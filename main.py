import logging, time, os, asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from config import TOKEN, ADMIN_ID, ADMIN_LINK, SERVERS
from database import DBManager
import admin

# --- Logging Setup ---
logging.basicConfig(format='%(asctime)s - %(name)s - %(message)s', level=logging.INFO)
db = DBManager()

# --- ပင်မ Keyboard ---
def get_main_keyboard(uid):
    kb = [[InlineKeyboardButton("🛍 ဝယ်ယူရန်", callback_data='user_buy')],
          [InlineKeyboardButton("💰 Credits ဖြည့်ရန်", callback_data='topup_menu')],
          [InlineKeyboardButton("👤 My Account / History", callback_data='my_acc')],
          [InlineKeyboardButton("👨‍💻 Admin နှင့် တိုက်ရိုက်", url=ADMIN_LINK)]]
    if int(uid) == int(ADMIN_ID):
        kb.append([InlineKeyboardButton("🛠 Admin Panel", callback_data='admin_panel')])
    return InlineKeyboardMarkup(kb)

# --- Start Handler ---
async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.business_message or update.message
    if not msg: return
    user = update.effective_user
    bal = db.get_balance(user.id)
    raw_msg = db.get_setting('welcome_msg')
    msg_text = raw_msg.format(name=user.first_name, balance=bal)
    
    bc_id = update.business_message.business_connection_id if update.business_message else None
    await context.bot.send_message(
        chat_id=msg.chat_id,
        text=msg_text,
        reply_markup=get_main_keyboard(user.id),
        business_connection_id=bc_id,
        parse_mode='Markdown'
    )

# --- Message & Photo Handler ---
async def handle_all_updates(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.business_message or update.message
    if not msg or not update.effective_user: return
    user_id = int(update.effective_user.id)
    bc_id = update.business_message.business_connection_id if update.business_message else None

    # Admin Settings Edit
    if user_id == int(ADMIN_ID) and 'editing_key' in context.user_data:
        key = context.user_data.pop('editing_key')
        db.update_setting(key, msg.text)
        await msg.reply_text(f"✅ `{key}` ကို ပြင်ဆင်ပြီးပါပြီ။")
        return

    # Photo Handling
    if msg.photo:
        reply_msg = await msg.reply_text("✅ ပြေစာရရှိပါသည်။ Admin အတည်ပြုရန် စောင့်ပေးပါ။ 🙏")
        await context.bot.send_photo(
            chat_id=ADMIN_ID, 
            photo=msg.photo[-1].file_id, 
            caption=f"💰 **Top-up Request**\nFrom: {update.effective_user.first_name}\nID: `{user_id}`",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ 5000 Ks", callback_data=f"ap_{user_id}_5000_{bc_id}_{reply_msg.message_id}"),
                 InlineKeyboardButton("✅ 10000 Ks", callback_data=f"ap_{user_id}_10000_{bc_id}_{reply_msg.message_id}")],
                [InlineKeyboardButton("❌ Reject / Cancel", callback_data=f"rj_{user_id}_{bc_id}_{reply_msg.message_id}")]
            ])
        )
        return

    text = msg.text.lower() if msg.text else ""
    triggers = ['hi', 'hello', 'မင်္ဂလာပါ', 'start', 'ဝယ်မယ်', 'စျေးနှုန်း']
    if any(x in text for x in triggers) or msg.sticker:
        await start_handler(update, context)

# --- Callback Handler ---
async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    uid, data = int(query.from_user.id), query.data
    bc_id = query.message.business_connection_id if query.message else None
    await query.answer()

    # --- Approval & Rejection Logic ---
    if data.startswith('ap_') or data.startswith('rj_'):
        if int(uid) != int(ADMIN_ID): return
        p = data.split('_')
        target_id, user_bc_id, msg_id = int(p[1]), (p[3] if p[3]!='None' else None), int(p[4])
        
        if data.startswith('ap_'):
            amt = float(p[2])
            db.update_balance(target_id, amt, "TOPUP")
            txt = f"✅ Credit **{amt} Ks** ဖြည့်သွင်းမှု အောင်မြင်ပါသည်။\n💰 လက်ကျန်: **{db.get_balance(target_id)} Ks**"
            await context.bot.send_message(chat_id=target_id, text=txt, reply_markup=get_main_keyboard(target_id), business_connection_id=user_bc_id, parse_mode='Markdown')
            await query.edit_message_caption(caption=f"{query.message.caption}\n\n✅ **Approved {amt} Ks!**")
        else:
            txt = "❌ သင်ပေးပို့သော ပြေစာမှာ မှားယွင်းနေပါသဖြင့် ငြင်းပယ်လိုက်ပါသည်။"
            await context.bot.send_message(chat_id=target_id, text=txt, business_connection_id=user_bc_id)
            await query.edit_message_caption(caption=f"{query.message.caption}\n\n❌ **Rejected!**")

    # --- Navigation Logic ---
    elif data == 'back_to_main':
        bal = db.get_balance(uid)
        msg = db.get_setting('welcome_msg').format(name=query.from_user.first_name, balance=bal)
        await context.bot.send_message(chat_id=uid, text=msg, reply_markup=get_main_keyboard(uid), business_connection_id=bc_id, parse_mode='Markdown')

    elif data == 'topup_menu':
        kb = [[InlineKeyboardButton("💳 5,000 Ks", callback_data='pay_5000')], [InlineKeyboardButton("💳 10,000 Ks", callback_data='pay_10000')], [InlineKeyboardButton("🔙 Back", callback_data='back_to_main')]]
        await context.bot.send_message(chat_id=uid, text="ဖြည့်သွင်းလိုသော ပမာဏ ရွေးချယ်ပါ-", reply_markup=InlineKeyboardMarkup(kb), business_connection_id=bc_id)

    elif data == 'my_acc':
        bal = db.get_balance(uid)
        kb = [[InlineKeyboardButton("📜 History", callback_data='view_history')], [InlineKeyboardButton("🔙 Back", callback_data='back_to_main')]]
        await context.bot.send_message(chat_id=uid, text=f"👤 Account\n🆔 ID: `{uid}`\n💰 Balance: **{bal} Ks**", reply_markup=InlineKeyboardMarkup(kb), business_connection_id=bc_id, parse_mode='Markdown')

    elif data == 'user_buy':
        kb = [[InlineKeyboardButton("💎 N4 VIP PRO စျေးနှုန်းများ", callback_data='n4_vip')],
              [InlineKeyboardButton("🔑 V2ray & Outline Key စျေးများ", callback_data='v2ray_menu')],
              [InlineKeyboardButton("📡 Starlink VIP ဝန်ဆောင်မှုများ", callback_data='starlink_menu')],
              [InlineKeyboardButton("🔙 Back", callback_data='back_to_main')]]
        await context.bot.send_message(chat_id=uid, text="🛍 **ဝယ်ယူလိုသော အမျိုးအစားကို ရွေးပါ**", reply_markup=InlineKeyboardMarkup(kb), business_connection_id=bc_id)

    # --- N4 VIP ---
    elif data == 'n4_vip':
        kb = [[InlineKeyboardButton("💎 ၁ လစာ - 8,000 Ks", callback_data='conf_N4VIP_8000')],
              [InlineKeyboardButton("💎 ၃ လစာ - 22,000 Ks", callback_data='conf_N4VIP_22000')],
              [InlineKeyboardButton("💎 ၆ လစာ - 40,000 Ks", callback_data='conf_N4VIP_40000')],
              [InlineKeyboardButton("💎 ၁ နှစ်စာ - 75,000 Ks", callback_data='conf_N4VIP_75000')],
              [InlineKeyboardButton("🔙 Back", callback_data='user_buy')]]
        await context.bot.send_message(chat_id=uid, text="🔥 **N4 VIP PRO စျေးနှုန်းများ**", reply_markup=InlineKeyboardMarkup(kb), business_connection_id=bc_id)

    # --- V2ray Menu ---
    elif data == 'v2ray_menu':
        kb = [[InlineKeyboardButton("♾ GB Limit (သက်တမ်းမရှိ)", callback_data='v2ray_gb')],
              [InlineKeyboardButton("🗓 သက်တမ်းပါသော Key များ", callback_data='v2ray_exp')],
              [InlineKeyboardButton("🇯🇵 Japan Region Key စျေး", callback_data='v2ray_jp')],
              [InlineKeyboardButton("🔙 Back", callback_data='user_buy')]]
        await context.bot.send_message(chat_id=uid, text="🔑 **V2ray & Outline Key စျေးများ**", reply_markup=InlineKeyboardMarkup(kb), business_connection_id=bc_id)

    elif data == 'v2ray_gb':
        kb = [[InlineKeyboardButton("🔸 50 GB - 5,000 Ks", callback_data='conf_V2GB_5000')],
              [InlineKeyboardButton("🔸 100 GB - 8,000 Ks", callback_data='conf_V2GB_8000')],
              [InlineKeyboardButton("🔸 200 GB - 15,000 Ks", callback_data='conf_V2GB_15000')],
              [InlineKeyboardButton("🔙 Back", callback_data='v2ray_menu')]]
        await context.bot.send_message(chat_id=uid, text="♾ **GB Limit (No Expiry)**", reply_markup=InlineKeyboardMarkup(kb), business_connection_id=bc_id)

    # --- Starlink ---
    elif data == 'starlink_menu':
        kb = [[InlineKeyboardButton("👤 တစ်ယောက်သုံးဖိုင်စျေး", callback_data='conf_SLFile_8000')],
              [InlineKeyboardButton("🖥 V2ray Key စျေးများ", callback_data='conf_SLV2_10000')],
              [InlineKeyboardButton("🔙 Back", callback_data='user_buy')]]
        await context.bot.send_message(chat_id=uid, text="📡 **Starlink VIP ဝန်ဆောင်မှုများ**", reply_markup=InlineKeyboardMarkup(kb), business_connection_id=bc_id)

    # --- Buying Conf ---
    elif data.startswith('conf_'):
        p = data.split('_')
        item, price = p[1], float(p[2])
        if db.get_balance(uid) < price:
            await context.bot.send_message(chat_id=uid, text=f"❌ Credit မလုံလောက်ပါ။\n{db.get_setting('payment_info')}", business_connection_id=bc_id, parse_mode='Markdown')
            return
        db.update_balance(uid, -price, f"BUY_{item}")
        await context.bot.send_message(chat_id=uid, text=f"✅ **{item}** ဝယ်ယူမှု အောင်မြင်ပါသည်။", business_connection_id=bc_id)
        await context.bot.send_message(ADMIN_ID, f"🔔 Order: {uid} bought {item}")

    elif data.startswith('pay_'):
        await context.bot.send_message(chat_id=uid, text=db.get_setting('payment_info'), business_connection_id=bc_id, parse_mode='Markdown')
    
    elif data == 'admin_panel':
        await query.edit_message_text("🛠 Admin Panel:", reply_markup=await admin.get_admin_menu())

# --- Admin Command ---
async def admin_credit_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if int(update.effective_user.id) != int(ADMIN_ID): return
    try:
        uid, amt = int(context.args[0]), float(context.args[1])
        db.update_balance(uid, amt, "ADMIN_ADD")
        await context.bot.send_message(chat_id=uid, text=f"✅ Admin မှ Credit {amt} Ks သွင်းပေးလိုက်ပါသည်။", reply_markup=get_main_keyboard(uid))
        await update.message.reply_text(f"✅ Success: {uid} +{amt}")
    except: await update.message.reply_text("Usage: /add ID Amount")

# --- Main ---
def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start_handler))
    app.add_handler(CommandHandler("add", admin_credit_cmd))
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle_all_updates))
    app.run_polling(drop_pending_updates=True)

if __name__ == '__main__': main()
