# main.py
import logging, time, asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from config import TOKEN, ADMIN_ID, ADMIN_LINK, SERVERS
from products import VPN_PRODUCTS
from database import DBManager
from xui_api import MultiXUI

logging.basicConfig(format='%(asctime)s - %(name)s - %(message)s', level=logging.INFO)
db = DBManager()

PAYMENT_INFO = f"💳 **ငွေလွှဲရန် အချက်အလက်များ**\n\n📞 **09682115890** (Myo Nanda Kyaw)\n❤️ **Wave | Kpay | Mytel Pay**\n\n📸 လွှဲပြီးပါက ပြေစာပို့ပေးပါ။ Admin မှ အမြန်ဆုံး အတည်ပြုပေးပါမည်။"

async def backup_db(context):
    await context.bot.send_document(chat_id=ADMIN_ID, document=open("nandabot.db", "rb"), caption="🛡️ Database Backup")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    bal = db.get_balance(user.id)
    kb = [[InlineKeyboardButton("🛍 ဝယ်ယူရန်", callback_data='user_buy')],
          [InlineKeyboardButton("💰 Credits ဖြည့်ရန်", callback_data='topup_menu')],
          [InlineKeyboardButton("👤 My Account", callback_data='my_acc')],
          [InlineKeyboardButton("👨‍💻 Admin နှင့် တိုက်ရိုက်", url=ADMIN_LINK)]]
    await update.message.reply_text(f"👋 မင်္ဂလာပါ {user.first_name}\n✨ **Nanda VPN Service** မှ ကြိုဆိုပါတယ်။\n💰 လက်ရှိ Credit: **{bal} Ks**", reply_markup=InlineKeyboardMarkup(kb), parse_mode='Markdown')

async def handle_msg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    if not msg: return
    if msg.photo:
        await msg.reply_text("✅ ပြေစာရရှိပါသည်။ Admin အတည်ပြုရန် စောင့်ပေးပါ။ 🙏")
        await context.bot.send_photo(chat_id=ADMIN_ID, photo=msg.photo[-1].file_id, 
                                     caption=f"💰 **Top-up Request**\nFrom: {update.effective_user.first_name}\nID: `{update.effective_user.id}`",
                                     reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("✅ 5000 Ks", callback_data=f"ap_{update.effective_user.id}_5000"),
                                                                         InlineKeyboardButton("✅ 10000 Ks", callback_data=f"ap_{update.effective_user.id}_10000")],
                                                                        [InlineKeyboardButton("📝 Custom", callback_data=f"ap_custom_{update.effective_user.id}")]]))
        return
    text = msg.text.lower() if msg.text else ""
    if any(x in text for x in ['hi', 'hello', 'မင်္ဂလာပါ']) or msg.sticker:
        await start(update, context)

async def handle_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    uid = query.from_user.id
    data = query.data
    await query.answer()

    if data == 'topup_menu':
        kb = [[InlineKeyboardButton("💳 5,000 Ks", callback_data='conf_top_5000')],
              [InlineKeyboardButton("💳 10,000 Ks", callback_data='conf_top_10000')],
              [InlineKeyboardButton("📝 Custom Amount", callback_data='conf_top_custom')],
              [InlineKeyboardButton("🔙 Back", callback_data='back_to_main')]]
        await query.edit_message_text("ဖြည့်သွင်းလိုသော Credit ပမာဏ ရွေးချယ်ပါ-", reply_markup=InlineKeyboardMarkup(kb))
    
    elif data.startswith('conf_top_'):
        amt = data.split('_')[-1]
        txt = f"❓ Credit {amt} Ks ဖြည့်ရန် သေချာပါသလား?" if amt != 'custom' else "❓ Custom Credit ဖြည့်ရန် သေချာပါသလား?"
        kb = [[InlineKeyboardButton("✅ ဟုတ်ကဲ့၊ သေချာပါတယ်", callback_data=f"pay_{amt}")],
              [InlineKeyboardButton("❌ မဟုတ်သေးပါ", callback_data='topup_menu')]]
        await query.edit_message_text(txt, reply_markup=InlineKeyboardMarkup(kb))

    elif data.startswith('pay_'):
        await query.edit_message_text(PAYMENT_INFO, parse_mode='Markdown')

    elif data.startswith('ap_'): # Admin Approval
        parts = data.split('_')
        target_id = int(parts[1]) if parts[1] != 'custom' else int(parts[2])
        if 'custom' in data:
            await query.message.reply_text(f"User {target_id} အတွက် Amount ရိုက်ထည့်ပါ (ဥပမာ- /add {target_id} 15000)")
            return
        amt = float(parts[2])
        db.update_balance(target_id, amt, "TOPUP")
        new_bal = db.get_balance(target_id)
        await context.bot.send_message(target_id, f"✅ Credit ဖြည့်ပြီးပါပြီ။\n➕ ဖြည့်သွင်းငွေ: {amt} Ks\n💰 စုစုပေါင်းလက်ကျန်: {new_bal} Ks")
        await query.message.reply_text(f"✅ User {target_id} ထံ {amt} Ks ဖြည့်သွင်းပြီးပါပြီ။")
        await backup_db(context)

    elif data == 'user_buy':
        kb = [[InlineKeyboardButton(v['name'], callback_data=f"cat_{k}")] for k,v in VPN_PRODUCTS.items()]
        kb.append([InlineKeyboardButton("🔙 Back", callback_data='back_to_main')])
        await query.edit_message_text("🏷️ Products Menu:", reply_markup=InlineKeyboardMarkup(kb))

    elif data.startswith('cat_'):
        cat = data.split('_', 1)[1]
        prod = VPN_PRODUCTS[cat]
        txt = f"✨ **{prod['name']}**\n💰 ဈေးနှုန်း: {prod['price']} Credits\n\nဝယ်ယူရန် သေချာပါသလား?"
        kb = [[InlineKeyboardButton("✅ ဟုတ်ကဲ့၊ ဝယ်ယူမည်", callback_data=f"confirm_buy_{cat}")],
              [InlineKeyboardButton("❌ မဝယ်သေးပါ", callback_data='user_buy')]]
        await query.edit_message_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode='Markdown')

    elif data.startswith('confirm_buy_'):
        cat = data.split('_')[-1]
        prod = VPN_PRODUCTS[cat]
        bal = db.get_balance(uid)
        if bal < prod['price']:
            await query.message.reply_text(f"❌ Credit မလုံလောက်ပါ။\nလိုအပ်ချက်: {prod['price']} Ks\nလက်ကျန်: {bal} Ks\n\n{PAYMENT_INFO}", parse_mode='Markdown')
            return
        
        db.update_balance(uid, -prod['price'], f"BUY_{cat}")
        await query.edit_message_text("⏳ Processing...")

        if prod['type'] == 'manual':
            await query.message.reply_text(f"✅ **{prod['name']}** ဝယ်ယူမှု အောင်မြင်ပါသည်။\nAdmin မှ အမြန်ဆုံး ဆက်သွယ် ပို့ဆောင်ပေးပါမည်။")
            await context.bot.send_message(ADMIN_ID, f"🔔 **Manual Order:** @{query.from_user.username} bought {prod['name']}")
        else:
            xui = MultiXUI(SERVERS[prod['server_key']])
            res = xui.create_user(f"n4_{uid}_{int(time.time())}", prod['p_type'], prod['gb'], prod['days'])
            if res:
                await query.message.reply_text(f"✅ **ဝယ်ယူမှု အောင်မြင်ပါသည်!**\n\n🌐 Sub URL: `{res['sub']}`\n🔑 Key: `{res['key']}`\n\n💰 လက်ကျန် Credit: {db.get_balance(uid)} Ks", parse_mode='Markdown')
            else:
                db.update_balance(uid, prod['price'], "REFUND_ERROR")
                await query.message.reply_text("❌ Server Error! Credit ပြန်ဖြည့်ပေးထားပါသည်။")
        await backup_db(context)

    elif data == 'back_to_main':
        await query.delete_message()
        # Resend start keyboard logic here...

async def admin_add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    try:
        uid, amt = int(context.args[0]), float(context.args[1])
        db.update_balance(uid, amt, "ADMIN_ADD")
        await update.message.reply_text(f"✅ User {uid} ထံ {amt} Ks ဖြည့်သွင်းပြီးပါပြီ။")
        await context.bot.send_message(uid, f"✅ Admin မှ Credit {amt} Ks ဖြည့်သွင်းပေးလိုက်ပါသည်။")
        await backup_db(context)
    except: await update.message.reply_text("Usage: /add ID Amount")

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("add", admin_add))
    app.add_handler(CallbackQueryHandler(handle_cb))
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle_msg))
    print("🚀 NandaBot V2 is running...")
    app.run_polling(drop_pending_updates=True)

if __name__ == '__main__': main()
