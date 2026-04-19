import logging, time, os, asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from telegram.constants import ChatAction
from config import TOKEN, ADMIN_ID, ADMIN_LINK, SERVERS
from database import DBManager
from xui_api import MultiXUI
import admin

# --- Logging Setup ---
logging.basicConfig(format='%(asctime)s - %(name)s - %(message)s', level=logging.INFO)
db = DBManager()

# --- Helper Functions ---
async def send_typing(context, chat_id):
    try:
        await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
        await asyncio.sleep(0.5)
    except: pass

async def backup_to_admin(context):
    try:
        await context.bot.send_document(chat_id=ADMIN_ID, document=open("nandabot.db", "rb"), 
                                       caption=f"🛡️ **NandaBot DB Backup**\nTime: {time.ctime()}")
    except: pass

# --- Core Bot Handlers ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg_obj = update.message or update.business_message
    if not msg_obj: return

    user = update.effective_user
    bal = db.get_balance(user.id)
    
    raw_msg = db.get_setting('welcome_msg')
    msg = raw_msg.format(name=user.first_name, balance=bal)
    
    kb = [[InlineKeyboardButton("🛍 ဝယ်ယူရန်", callback_data='user_buy')],
          [InlineKeyboardButton("💰 Credit ဖြည့်ရန်", callback_data='topup_menu')],
          [InlineKeyboardButton("👤 My Account / History", callback_data='my_acc')],
          [InlineKeyboardButton("👨‍💻 Admin နှင့် တိုက်ရိုက်", url=ADMIN_LINK)]]
    
    if user.id == ADMIN_ID:
        kb.append([InlineKeyboardButton("🛠 Admin Panel", callback_data='admin_panel')])
    
    await msg_obj.reply_text(msg, reply_markup=InlineKeyboardMarkup(kb), parse_mode='Markdown')

async def handle_msg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.business_message
    if not msg or not update.effective_user: return
    
    user_id = update.effective_user.id

    # Admin Text Update Logic
    if user_id == ADMIN_ID and 'editing_key' in context.user_data and update.message:
        key = context.user_data.pop('editing_key')
        db.update_setting(key, update.message.text)
        await update.message.reply_text(f"✅ `{key}` ကို အောင်မြင်စွာ ပြင်ဆင်ပြီးပါပြီ။")
        return

    # Skip Admin echo except business messages
    if user_id == ADMIN_ID and not update.business_message: return

    await send_typing(context, update.effective_chat.id)

    # Photo/Receipt Handler
    if msg.photo:
        await msg.reply_text("✅ ပြေစာရရှိပါသည်။ Admin အတည်ပြုရန် စောင့်ပေးပါ။ 🙏")
        await context.bot.send_photo(
            chat_id=ADMIN_ID, 
            photo=msg.photo[-1].file_id, 
            caption=f"💰 **Top-up Request**\nFrom: {update.effective_user.first_name}\nID: `{user_id}`",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ 5000 Ks", callback_data=f"ap_{user_id}_5000"),
                 InlineKeyboardButton("✅ 10000 Ks", callback_data=f"ap_{user_id}_10000")],
                [InlineKeyboardButton("📝 Custom", callback_data=f"ap_custom_{user_id}")]
            ])
        )
        return

    # Trigger Keywords
    text = msg.text.lower() if msg.text else ""
    if any(x in text for x in ['atom', 'ပိတ်', 'မရဘူး']):
        await msg.reply_text(db.get_setting('atom_msg'))
        return

    triggers = ['hi', 'hello', 'မင်္ဂလာပါ', 'စျေးနှုန်း', 'vpn', 'start', 'ဝယ်မယ်']
    if any(x in text for x in triggers) or msg.sticker:
        await start(update, context)

async def handle_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    uid, data = query.from_user.id, query.data
    await query.answer()

    if data == 'admin_panel':
        await query.edit_message_text("🛠 Admin Control Panel:", reply_markup=await admin.get_admin_menu())
    
    elif data == 'admin_edit_text':
        kb = [[InlineKeyboardButton("Welcome Message", callback_data='set_txt_welcome_msg')],
              [InlineKeyboardButton("Payment Info", callback_data='set_txt_payment_info')],
              [InlineKeyboardButton("Atom Msg", callback_data='set_txt_atom_msg')],
              [InlineKeyboardButton("🔙 Back", callback_data='admin_panel')]]
        await query.edit_message_text("ပြင်လိုသော စာသားကို ရွေးချယ်ပါ-", reply_markup=InlineKeyboardMarkup(kb))

    elif data.startswith('set_txt_'):
        key = data.replace('set_txt_', '')
        context.user_data['editing_key'] = key
        await query.message.reply_text(f"📝 `{key}` အတွက် စာသားအသစ် ပို့ပေးပါ။")

    elif data == 'user_buy':
        prods = db.get_products()
        if not prods:
            await query.edit_message_text("❌ လက်ရှိတွင် ရောင်းရန် Product မရှိသေးပါ။")
            return
        kb = [[InlineKeyboardButton(f"{p['name']} - {p['price']} Ks", callback_data=f"confirm_buy_{p['id']}")] for p in prods]
        kb.append([InlineKeyboardButton("🔙 Back", callback_data='back_to_main')])
        await query.edit_message_text("🏷️ **Product အမျိုးအစား ရွေးချယ်ပါ**", reply_markup=InlineKeyboardMarkup(kb), parse_mode='Markdown')

    elif data.startswith('confirm_buy_'):
        pid = int(data.split('_')[-1])
        p = next((x for x in db.get_products() if x['id'] == pid), None)
        bal = db.get_balance(uid)
        
        if bal < p['price']:
            await query.message.reply_text(f"❌ Credit မလုံလောက်ပါ။\n\n{db.get_setting('payment_info')}", parse_mode='Markdown')
            return

        db.update_balance(uid, -p['price'], f"BUY_{p['name']}")
        await query.edit_message_text(f"⏳ **{p['name']}** အတွက် လုပ်ဆောင်နေပါပြီ...")
        
        if p['type'] == 'manual':
            await query.message.reply_text(f"✅ **{p['name']}** အောင်မြင်ပါသည်။ Admin မှ ပို့ပေးပါမည်။")
            await context.bot.send_message(ADMIN_ID, f"🔔 Order: @{query.from_user.username} bought {p['name']}")
        else:
            xui = MultiXUI(SERVERS[p['server_key']])
            res = xui.create_user(f"n4_{uid}_{int(time.time())}", p['p_type'], p['gb'], p['days'])
            if res:
                await query.message.reply_text(f"✅ **ဝယ်ယူမှု အောင်မြင်ပါသည်!**\n\n🌐 Sub: `{res['sub']}`\n🔑 Key: `{res['key']}`\n💰 လက်ကျန်: {db.get_balance(uid)} Ks")
            else:
                db.update_balance(uid, p['price'], "REFUND")
                await query.message.reply_text("❌ Server Error! Credit ပြန်ဖြည့်ပေးထားပါသည်။")
        await backup_to_admin(context)

    elif data == 'topup_menu':
        kb = [[InlineKeyboardButton("💳 5,000 Ks", callback_data='pay_5000')],
              [InlineKeyboardButton("💳 10,000 Ks", callback_data='pay_10000')],
              [InlineKeyboardButton("📝 Custom Amount", callback_data='pay_custom')],
              [InlineKeyboardButton("🔙 Back", callback_data='back_to_main')]]
        await query.edit_message_text("ဖြည့်သွင်းလိုသော ပမာဏ ရွေးချယ်ပါ-", reply_markup=InlineKeyboardMarkup(kb))

    elif data.startswith('pay_'):
        await query.edit_message_text(db.get_setting('payment_info'), parse_mode='Markdown')

    elif data.startswith('ap_'):
        if uid != ADMIN_ID: return
        parts = data.split('_')
        target_id = int(parts[1]) if parts[1] != 'custom' else int(parts[2])
        
        if 'custom' in data:
            await query.message.reply_text(f"👤 User `{target_id}` အတွက် Amount ရိုက်ထည့်ပါ-\n\n`/add {target_id} 5000`", parse_mode='Markdown')
            return
            
        amt = float(parts[2])
        db.update_balance(target_id, amt, "TOPUP_APPROVE")
        try:
            await context.bot.send_message(target_id, f"✅ Credit **{amt} Ks** ဖြည့်သွင်းပြီးပါပြီ။\nလက်ရှိလက်ကျန်: **{db.get_balance(target_id)} Ks**", parse_mode='Markdown')
        except: pass
        await query.edit_message_caption(caption=f"{query.message.caption}\n\n✅ **Approved {amt} Ks!**")
        await backup_to_admin(context)

    elif data == 'my_acc':
        bal = db.get_balance(uid)
        kb = [[InlineKeyboardButton("📜 ငွေဝင်ထွက်မှတ်တမ်း", callback_data='view_history')],
              [InlineKeyboardButton("🔙 Back", callback_data='back_to_main')]]
        await query.edit_message_text(f"👤 **Account Info**\n🆔 ID: `{uid}`\n💰 Balance: **{bal} Ks**", reply_markup=InlineKeyboardMarkup(kb), parse_mode='Markdown')

    elif data == 'view_history':
        h = db.get_history(uid)
        txt = "📜 **နောက်ဆုံးမှတ်တမ်း (၅) ခု**\n\n"
        if not h: txt += "မှတ်တမ်းမရှိပါ။"
        else:
            for amt, t, ts in h:
                icon = "➕" if amt > 0 else "➖"
                txt += f"{icon} {abs(amt)} Ks ({t})\n📅 {ts}\n\n"
        await query.edit_message_text(txt, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data='my_acc')]]), parse_mode='Markdown')

    elif data == 'back_to_main':
        await start(update, context)

# --- Admin Commands ---
async def admin_credit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    try:
        if not context.args or len(context.args) < 2:
            await update.message.reply_text("💡 Usage: `/add UserID Amount`")
            return
        uid, amt = int(context.args[0]), float(context.args[1])
        db.update_balance(uid, amt, "ADMIN_ADD")
        try:
            await context.bot.send_message(uid, f"✅ Admin မှ Credit **{amt} Ks** ဖြည့်သွင်းပေးလိုက်ပါသည်။\n💰 လက်ကျန်: **{db.get_balance(uid)} Ks**", parse_mode='Markdown')
        except: pass
        await update.message.reply_text(f"✅ User `{uid}` ထံ `{amt} Ks` သွင်းပြီးပါပြီ။")
        await backup_to_admin(context)
    except: await update.message.reply_text("❌ Format: `/add UserID Amount` (ဂဏန်းသီးသန့်ရိုက်ပါ)")

async def admin_add_p(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    try:
        a = [x.strip() for x in " ".join(context.args).split(',')]
        db.add_product(a[0], a[1], float(a[2]), a[3], a[4], int(a[5]), int(a[6]))
        await update.message.reply_text(f"✅ Product '{a[0]}' ထည့်ပြီးပါပြီ။")
    except: await update.message.reply_text("Format: `/add_prod Name, type, price, S1, vless, 100, 30`")

# --- Main App ---
def main():
    app = Application.builder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("add", admin_credit))
    app.add_handler(CommandHandler("add_prod", admin_add_p))
    app.add_handler(CallbackQueryHandler(handle_cb))
    app.add_handler(MessageHandler((filters.TEXT | filters.PHOTO | filters.Sticker.ALL) & ~filters.COMMAND, handle_msg))
    
    print("🚀 NandaBot V2.5 is running...")
    app.run_polling(drop_pending_updates=True)

if __name__ == '__main__': main()
