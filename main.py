import logging, time, os, asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from config import TOKEN, ADMIN_ID, ADMIN_LINK, SERVERS
from database import DBManager
from xui_api import MultiXUI
import admin

# --- Logging Setup ---
logging.basicConfig(format='%(asctime)s - %(name)s - %(message)s', level=logging.INFO)
db = DBManager()

# --- Helper Functions ---
def get_main_keyboard(uid):
    kb = [[InlineKeyboardButton("🛍 ဝယ်ယူရန်", callback_data='user_buy')],
          [InlineKeyboardButton("💰 Credits ဖြည့်ရန်", callback_data='topup_menu')],
          [InlineKeyboardButton("👤 My Account / History", callback_data='my_acc')],
          [InlineKeyboardButton("👨‍💻 Admin နှင့် တိုက်ရိုက်", url=ADMIN_LINK)]]
    if int(uid) == int(ADMIN_ID):
        kb.append([InlineKeyboardButton("🛠 Admin Panel", callback_data='admin_panel')])
    return InlineKeyboardMarkup(kb)

async def backup_to_admin(context):
    try:
        await context.bot.send_document(chat_id=ADMIN_ID, document=open("nandabot.db", "rb"), 
                                       caption=f"🛡️ **NandaBot DB Backup**\nTime: {time.ctime()}")
    except: pass

# --- Core Bot Handlers ---
async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.business_message or update.message
    if not msg: return
    user = update.effective_user
    bal = db.get_balance(user.id)
    welcome_text = db.get_setting('welcome_msg').format(name=user.first_name, balance=bal)
    
    bc_id = update.business_message.business_connection_id if update.business_message else None
    await context.bot.send_message(
        chat_id=msg.chat_id,
        text=welcome_text,
        reply_markup=get_main_keyboard(user.id),
        business_connection_id=bc_id,
        parse_mode='Markdown'
    )

async def handle_all_updates(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.business_message or update.message
    if not msg or not update.effective_user: return
    user_id = int(update.effective_user.id)
    bc_id = update.business_message.business_connection_id if update.business_message else None

    # Admin Settings Editing
    if user_id == int(ADMIN_ID) and 'editing_key' in context.user_data:
        key = context.user_data.pop('editing_key')
        db.update_setting(key, msg.text)
        await msg.reply_text(f"✅ `{key}` ပြင်ဆင်ပြီးပါပြီ။")
        return

    # Photo/Receipts
    if msg.photo:
        reply_msg = await msg.reply_text("✅ ပြေစာရရှိပါသည်။ Admin အတည်ပြုရန် စောင့်ပေးပါ။ 🙏")
        await context.bot.send_photo(
            chat_id=ADMIN_ID, 
            photo=msg.photo[-1].file_id, 
            caption=f"💰 **Top-up Request**\nFrom: {update.effective_user.first_name}\nID: `{user_id}`\nBC_ID: `{bc_id}`",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ 5000 Ks", callback_data=f"ap_{user_id}_5000_{bc_id}_{reply_msg.message_id}"),
                 InlineKeyboardButton("✅ 10000 Ks", callback_data=f"ap_{user_id}_10000_{bc_id}_{reply_msg.message_id}")]
            ])
        )
        return

    # Trigger Keywords
    text = msg.text.lower() if msg.text else ""
    if any(x in text for x in ['hi', 'hello', 'မင်္ဂလာပါ', 'start', 'ဝယ်မယ်']):
        await start_handler(update, context)

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    uid = int(query.from_user.id)
    data = query.data
    bc_id = query.message.business_connection_id if query.message else None
    await query.answer()

    if data.startswith('ap_'):
        if uid != int(ADMIN_ID): return
        p = data.split('_')
        # Format: ap_targetid_amount_bcid_msgid
        target_id, amt = int(p[1]), float(p[2])
        user_bc_id = p[3] if p[3]!='None' else None
        
        if db.update_balance(target_id, amt, "TOPUP_APPROVE"):
            msg_text = f"✅ Credit **{amt} Ks** ဖြည့်သွင်းမှု အောင်မြင်ပါသည်။\n💰 လက်ကျန်: **{db.get_balance(target_id)} Ks**"
            await context.bot.send_message(chat_id=target_id, text=msg_text, reply_markup=get_main_keyboard(target_id), business_connection_id=user_bc_id, parse_mode='Markdown')
            await query.edit_message_caption(caption=f"{query.message.caption}\n\n✅ **Approved {amt} Ks!**")
            await backup_to_admin(context)

    elif data == 'topup_menu':
        kb = [[InlineKeyboardButton("💳 5,000 Ks", callback_data='pay_5000')], [InlineKeyboardButton("💳 10,000 Ks", callback_data='pay_10000')], [InlineKeyboardButton("🔙 Back", callback_data='back_to_main')]]
        await context.bot.send_message(chat_id=uid, text="ဖြည့်သွင်းလိုသော ပမာဏ ရွေးချယ်ပါ-", reply_markup=InlineKeyboardMarkup(kb), business_connection_id=bc_id)

    elif data == 'my_acc':
        bal = db.get_balance(uid)
        kb = [[InlineKeyboardButton("📜 History", callback_data='view_history')], [InlineKeyboardButton("🔙 Back", callback_data='back_to_main')]]
        await context.bot.send_message(chat_id=uid, text=f"👤 **Account Info**\n🆔 ID: `{uid}`\n💰 Balance: **{bal} Ks**", reply_markup=InlineKeyboardMarkup(kb), business_connection_id=bc_id, parse_mode='Markdown')

    elif data == 'back_to_main':
        bal = db.get_balance(uid)
        msg = db.get_setting('welcome_msg').format(name=query.from_user.first_name, balance=bal)
        await context.bot.send_message(chat_id=uid, text=msg, reply_markup=get_main_keyboard(uid), business_connection_id=bc_id, parse_mode='Markdown')

    elif data == 'user_buy':
        prods = db.get_products()
        kb = [[InlineKeyboardButton(f"{p['name']} - {p['price']} Ks", callback_data=f"confirm_buy_{p['id']}")] for p in prods]
        kb.append([InlineKeyboardButton("🔙 Back", callback_data='back_to_main')])
        await context.bot.send_message(chat_id=uid, text="🏷️ **Product ရွေးချယ်ပါ**", reply_markup=InlineKeyboardMarkup(kb), business_connection_id=bc_id, parse_mode='Markdown')

    elif data.startswith('confirm_buy_'):
        pid = int(data.split('_')[-1])
        p = next((x for x in db.get_products() if x['id'] == pid), None)
        if db.get_balance(uid) < p['price']:
            await context.bot.send_message(chat_id=uid, text="❌ Credit မလုံလောက်ပါ။", business_connection_id=bc_id)
            return
        db.update_balance(uid, -p['price'], f"BUY_{p['name']}")
        await context.bot.send_message(chat_id=uid, text=f"✅ **{p['name']}** ဝယ်ယူမှု အောင်မြင်ပါသည်။", business_connection_id=bc_id)

    elif data == 'admin_panel':
        await query.edit_message_text("🛠 Admin Panel:", reply_markup=await admin.get_admin_menu())

    elif data.startswith('pay_'):
        await context.bot.send_message(chat_id=uid, text=db.get_setting('payment_info'), business_connection_id=bc_id, parse_mode='Markdown')

# --- Admin Commands ---
async def admin_credit_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if int(update.effective_user.id) != int(ADMIN_ID): return
    try:
        uid, amt = int(context.args[0]), float(context.args[1])
        if db.update_balance(uid, amt, "ADMIN_ADD"):
            await context.bot.send_message(chat_id=uid, text=f"✅ Admin မှ Credit **{amt} Ks** ဖြည့်သွင်းပေးလိုက်ပါသည်။", reply_markup=get_main_keyboard(uid), parse_mode='Markdown')
            await update.message.reply_text(f"✅ Success: {uid} +{amt} Ks")
    except: await update.message.reply_text("Usage: /add ID Amount")

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start_handler))
    app.add_handler(CommandHandler("add", admin_credit_command))
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle_all_updates))
    print("🚀 NandaBot is starting...")
    app.run_polling(drop_pending_updates=True)

if __name__ == '__main__': main()
