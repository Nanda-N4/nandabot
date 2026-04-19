import logging, time, os, asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from telegram.constants import ChatAction
from config import TOKEN, ADMIN_ID, ADMIN_LINK, SERVERS
from database import DBManager
from xui_api import MultiXUI
import admin

logging.basicConfig(format='%(asctime)s - %(name)s - %(message)s', level=logging.INFO)
db = DBManager()

async def backup_to_admin(context):
    try:
        await context.bot.send_document(chat_id=ADMIN_ID, document=open("nandabot.db", "rb"), 
                                       caption=f"🛡️ **NandaBot DB Backup**\nTime: {time.ctime()}")
    except: pass

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg_obj = update.message or update.business_message
    if not msg_obj: return
    user = update.effective_user
    bal = db.get_balance(user.id)
    raw_msg = db.get_setting('welcome_msg')
    msg = raw_msg.format(name=user.first_name, balance=bal)
    kb = [[InlineKeyboardButton("🛍 ဝယ်ယူရန်", callback_data='user_buy')],
          [InlineKeyboardButton("💰 Credits ဖြည့်ရန်", callback_data='topup_menu')],
          [InlineKeyboardButton("👤 My Account / History", callback_data='my_acc')],
          [InlineKeyboardButton("👨‍💻 Admin နှင့် တိုက်ရိုက်", url=ADMIN_LINK)]]
    if int(user.id) == int(ADMIN_ID):
        kb.append([InlineKeyboardButton("🛠 Admin Panel", callback_data='admin_panel')])
    await msg_obj.reply_text(msg, reply_markup=InlineKeyboardMarkup(kb), parse_mode='Markdown')

async def handle_msg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.business_message
    if not msg or not update.effective_user: return
    user_id = int(update.effective_user.id)

    if user_id == int(ADMIN_ID) and 'editing_key' in context.user_data:
        key = context.user_data.pop('editing_key')
        db.update_setting(key, msg.text)
        await msg.reply_text(f"✅ `{key}` ကို ပြင်ဆင်ပြီးပါပြီ။")
        return

    if user_id == int(ADMIN_ID) and not update.business_message: return

    if msg.photo:
        await msg.reply_text("✅ ပြေစာရရှိပါသည်။ Admin အတည်ပြုရန် စောင့်ပေးပါ။ 🙏")
        await context.bot.send_photo(
            chat_id=ADMIN_ID, photo=msg.photo[-1].file_id, 
            caption=f"💰 **Top-up Request**\nFrom: {update.effective_user.first_name}\nID: `{user_id}`",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ 5000 Ks", callback_data=f"ap_{user_id}_5000"),
                 InlineKeyboardButton("✅ 10000 Ks", callback_data=f"ap_{user_id}_10000")],
                [InlineKeyboardButton("📝 Custom", callback_data=f"ap_custom_{user_id}")]
            ])
        )
        return

    text = msg.text.lower() if msg.text else ""
    triggers = ['hi', 'hello', 'မင်္ဂလာပါ', 'စျေးနှုန်း', 'vpn', 'start', 'ဝယ်မယ်']
    if any(x in text for x in triggers) or msg.sticker:
        await start(update, context)

async def handle_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    uid = int(query.from_user.id)
    data = query.data
    await query.answer()

    # --- Approval Logic ---
    if data.startswith('ap_'):
        if int(uid) != int(ADMIN_ID): return
        parts = data.split('_')
        if 'custom' in data:
            target_id = parts[2]
            await query.message.reply_text(f"👤 User `{target_id}` အတွက် Amount ရိုက်ထည့်ပါ-\n\n`/add {target_id} 5000`", parse_mode='Markdown')
            return
        target_id, amt = int(parts[1]), float(parts[2])
        if db.update_balance(target_id, amt, "TOPUP_APPROVE"):
            try:
                await context.bot.send_message(chat_id=target_id, 
                    text=f"✅ Credit **{amt} Ks** ဖြည့်သွင်းပြီးပါပြီ။\n💰 လက်ကျန်: **{db.get_balance(target_id)} Ks**", 
                    parse_mode='Markdown')
            except: pass
            await query.edit_message_caption(caption=f"{query.message.caption}\n\n✅ **Approved {amt} Ks!**")
        await backup_to_admin(context)

    # --- Navigation Logic ---
    elif data == 'topup_menu':
        kb = [[InlineKeyboardButton("💳 5,000 Ks", callback_data='pay_5000')],
              [InlineKeyboardButton("💳 10,000 Ks", callback_data='pay_10000')],
              [InlineKeyboardButton("📝 Custom Amount", callback_data='pay_custom')],
              [InlineKeyboardButton("🔙 Back", callback_data='back_to_main')]]
        await query.edit_message_text("ဖြည့်သွင်းလိုသော ပမာဏ ရွေးချယ်ပါ-", reply_markup=InlineKeyboardMarkup(kb))

    elif data == 'my_acc':
        bal = db.get_balance(uid)
        kb = [[InlineKeyboardButton("📜 History", callback_data='view_history')], [InlineKeyboardButton("🔙 Back", callback_data='back_to_main')]]
        await query.edit_message_text(f"👤 **Account Info**\n🆔 ID: `{uid}`\n💰 Balance: **{bal} Ks**", reply_markup=InlineKeyboardMarkup(kb), parse_mode='Markdown')

    elif data == 'back_to_main':
        bal = db.get_balance(uid)
        msg = db.get_setting('welcome_msg').format(name=query.from_user.first_name, balance=bal)
        kb = [[InlineKeyboardButton("🛍 ဝယ်ယူရန်", callback_data='user_buy')],
              [InlineKeyboardButton("💰 Credits ဖြည့်ရန်", callback_data='topup_menu')],
              [InlineKeyboardButton("👤 My Account / History", callback_data='my_acc')],
              [InlineKeyboardButton("👨‍💻 Admin နှင့် တိုက်ရိုက်", url=ADMIN_LINK)]]
        if int(uid) == int(ADMIN_ID): kb.append([InlineKeyboardButton("🛠 Admin Panel", callback_data='admin_panel')])
        await query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(kb), parse_mode='Markdown')

    elif data.startswith('pay_'):
        await query.edit_message_text(db.get_setting('payment_info'), parse_mode='Markdown')

    elif data == 'view_history':
        h = db.get_history(uid)
        txt = "📜 **မှတ်တမ်း (၅) ခု**\n\n"
        for amt, t, ts in h: txt += f"{'➕' if amt > 0 else '➖'} {abs(amt)} Ks ({t})\n"
        await query.edit_message_text(txt, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data='my_acc')]]), parse_mode='Markdown')

    elif data == 'user_buy':
        prods = db.get_products()
        kb = [[InlineKeyboardButton(f"{p['name']} - {p['price']} Ks", callback_data=f"confirm_buy_{p['id']}")] for p in prods]
        kb.append([InlineKeyboardButton("🔙 Back", callback_data='back_to_main')])
        await query.edit_message_text("🏷️ **Product ရွေးချယ်ပါ**", reply_markup=InlineKeyboardMarkup(kb), parse_mode='Markdown')

    elif data.startswith('confirm_buy_'):
        pid = int(data.split('_')[-1])
        p = next((x for x in db.get_products() if x['id'] == pid), None)
        if db.get_balance(uid) < p['price']:
            await query.message.reply_text(f"❌ Credit မလုံလောက်ပါ။\n\n{db.get_setting('payment_info')}", parse_mode='Markdown')
            return
        db.update_balance(uid, -p['price'], f"BUY_{p['name']}")
        if p['type'] == 'manual':
            await query.message.reply_text(f"✅ **{p['name']}** အောင်မြင်ပါသည်။ Admin မှ ပို့ပေးပါမည်။")
            await context.bot.send_message(ADMIN_ID, f"🔔 Order: @{query.from_user.username} bought {p['name']}")
        else:
            xui = MultiXUI(SERVERS[p['server_key']])
            res = xui.create_user(f"n4_{uid}_{int(time.time())}", p['p_type'], p['gb'], p['days'])
            if res: await query.message.reply_text(f"✅ **အောင်မြင်ပါသည်!**\n\n🌐 Sub: `{res['sub']}`\n🔑 Key: `{res['key']}`\n💰 လက်ကျန်: {db.get_balance(uid)} Ks")
            else:
                db.update_balance(uid, p['price'], "REFUND")
                await query.message.reply_text("❌ Server Error! Credit ပြန်ဖြည့်ပေးထားပါသည်။")
        await backup_to_admin(context)

async def admin_credit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if int(update.effective_user.id) != int(ADMIN_ID): return
    try:
        uid, amt = int(context.args[0]), float(context.args[1])
        if db.update_balance(uid, amt, "ADMIN_ADD"):
            await context.bot.send_message(chat_id=uid, text=f"✅ Admin မှ Credit **{amt} Ks** ဖြည့်သွင်းပေးလိုက်ပါသည်။", parse_mode='Markdown')
            await update.message.reply_text(f"✅ Success: {uid} +{amt} Ks")
    except: await update.message.reply_text("Usage: /add ID Amount")

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("add", admin_credit))
    app.add_handler(CallbackQueryHandler(handle_cb))
    app.add_handler(MessageHandler((filters.TEXT | filters.PHOTO) & ~filters.COMMAND, handle_msg))
    app.run_polling(drop_pending_updates=True)

if __name__ == '__main__': main()
