# main.py
import logging, time, os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from config import TOKEN, ADMIN_ID, ADMIN_LINK, SERVERS
from products import VPN_PRODUCTS
from database import DBManager
from xui_api import MultiXUI
import admin

logging.basicConfig(format='%(asctime)s - %(name)s - %(message)s', level=logging.INFO)
db = DBManager()

PAYMENT_INFO = "💳 **ငွေလွှဲရန် အချက်အလက်များ**\n\n📞 **09682115890** (Myo Nanda Kyaw)\n❤️ **Wave | Kpay | AYA Pay**\n\n📸 ပြေစာပို့ပေးပါ၊ Admin မှ Credit ဖြည့်ပေးပါမည်။"

async def backup_db(context):
    await context.bot.send_document(chat_id=ADMIN_ID, document=open("nandabot.db", "rb"), caption="🛡️ DB Auto Backup")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bal = db.get_balance(update.effective_user.id)
    keyboard = [[InlineKeyboardButton("🛍 VPN ဝယ်ယူရန်", callback_data='user_buy')],
                [InlineKeyboardButton("👤 My Account / Credit", callback_data='my_acc')]]
    if update.effective_user.id == ADMIN_ID:
        keyboard.append([InlineKeyboardButton("🛠 Admin Panel", callback_data='admin_panel')])
    await update.message.reply_text(f"👋 မင်္ဂလာပါ {update.effective_user.first_name}\n💰 လက်ရှိ Credit: **{bal} Ks**", 
                                   reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()

    if query.data == 'admin_panel':
        await query.edit_message_text("🛠 Admin Panel:", reply_markup=await admin.get_admin_menu())
    elif query.data == 'admin_backup':
        await backup_db(context)
        await query.message.reply_text("✅ Backup sent to your chat.")
    elif query.data == 'my_acc':
        bal = db.get_balance(user_id)
        await query.edit_message_text(f"👤 **သင့်အကောင့်အချက်အလက်**\n\n🆔 ID: `{user_id}`\n💰 Balance: **{bal} Ks**\n\n{PAYMENT_INFO}", 
                                     reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data='back_to_main')]]), parse_mode='Markdown')
    elif query.data == 'back_to_main':
        await start(update, context) # Simplified back
    elif query.data == 'user_buy':
        keyboard = [[InlineKeyboardButton(v['name'], callback_data=f"cat_{k}")] for k,v in VPN_PRODUCTS.items()]
        await query.edit_message_text("Product ရွေးချယ်ပါ-", reply_markup=InlineKeyboardMarkup(keyboard))
    elif query.data.startswith('cat_'):
        cat = query.data.split('_', 1)[1]
        prod = VPN_PRODUCTS[cat]
        keyboard = [[InlineKeyboardButton(p['label'], callback_data=f"buy_{cat}_{i}")] for i, p in enumerate(prod['plans'])]
        await query.edit_message_text(f"✨ {prod['name']}\nPlan ရွေးချယ်ပါ-", reply_markup=InlineKeyboardMarkup(keyboard))
    elif query.data.startswith('buy_'):
        _, cat, idx = query.data.split('_')
        prod = VPN_PRODUCTS[cat]
        plan = prod['plans'][int(idx)]
        bal = db.get_balance(user_id)

        if bal < plan['price']:
            await query.message.reply_text(f"❌ Credit မလုံလောက်ပါ။ {plan['price']} Ks လိုအပ်ပါသည်။\n\n{PAYMENT_INFO}", parse_mode='Markdown')
            return

        db.update_balance(user_id, -plan['price'], f"BUY_{cat}")
        await query.edit_message_text("⏳ Processing your request...")
        
        if prod['type'] == 'manual':
            await query.message.reply_text(f"✅ ဝယ်ယူမှုအောင်မြင်ပါပြီ။ Admin မှ {plan['label']} ကို ပို့ပေးပါမည်။")
            await context.bot.send_message(ADMIN_ID, f"🔔 **Order:** @{query.from_user.username} (ID: {user_id}) bought {plan['label']}")
        else:
            xui = MultiXUI(SERVERS[prod['server_key']])
            res = xui.create_user(f"n4_{user_id}_{int(time.time())}", prod['p_type'], plan['gb'], plan['days'])
            if res:
                await query.message.reply_text(f"✅ **Key Generated!**\n\n🌐 Sub: `{res['sub']}`\n🔑 Key: `{res['key']}`")
            else:
                db.update_balance(user_id, plan['price'], "REFUND_ERROR")
                await query.message.reply_text("❌ Server Error! Credit ပြန်ဖြည့်ပေးထားပါသည်။")
        await backup_db(context)

async def admin_add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    try:
        uid, amt = int(context.args[0]), float(context.args[1])
        db.update_balance(uid, amt, "DEPOSIT")
        await update.message.reply_text(f"✅ Added {amt} Ks to User {uid}")
        await backup_db(context)
    except: await update.message.reply_text("Usage: /add ID Amount")

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("add", admin_add))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.PHOTO, lambda u, c: c.bot.forward_message(ADMIN_ID, u.message.chat_id, u.message.message_id)))
    print("🚀 NandaBot V2 is Live!")
    app.run_polling(drop_pending_updates=True)

if __name__ == '__main__': main()
