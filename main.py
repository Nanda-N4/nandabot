import logging, time, os, asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from config import TOKEN, ADMIN_ID, ADMIN_LINK, SERVERS
from database import DBManager
from xui_api import MultiXUI
import admin

# --- Logging ---
logging.basicConfig(format='%(asctime)s - %(name)s - %(message)s', level=logging.INFO)
db = DBManager()

# --- Keyboards ---
def get_main_keyboard(uid):
    kb = [[InlineKeyboardButton("🛍 ဝယ်ယူရန်", callback_data='user_buy')],
          [InlineKeyboardButton("💰 Credits ဖြည့်ရန်", callback_data='topup_menu')],
          [InlineKeyboardButton("👤 My Account / History", callback_data='my_acc')],
          [InlineKeyboardButton("👨‍💻 Admin နှင့် တိုက်ရိုက်", url=ADMIN_LINK)]]
    if int(uid) == int(ADMIN_ID):
        kb.append([InlineKeyboardButton("🛠 Admin Panel", callback_data='admin_panel')])
    return InlineKeyboardMarkup(kb)

# --- Handlers ---
async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.business_message or update.message
    if not msg: return
    user = update.effective_user
    bal = db.get_balance(user.id)
    raw_msg = db.get_setting('welcome_msg')
    msg_text = raw_msg.format(name=user.first_name, balance=bal)
    bc_id = update.business_message.business_connection_id if update.business_message else None
    await context.bot.send_message(chat_id=msg.chat_id, text=msg_text, reply_markup=get_main_keyboard(user.id), business_connection_id=bc_id, parse_mode='Markdown')

async def handle_all_updates(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.business_message or update.message
    if not msg or not update.effective_user: return
    user_id = int(update.effective_user.id)
    bc_id = update.business_message.business_connection_id if update.business_message else None

    if msg.photo:
        reply_msg = await msg.reply_text("✅ ပြေစာရရှိပါသည်။ Admin အတည်ပြုရန် စောင့်ပေးပါ။ 🙏")
        await context.bot.send_photo(
            chat_id=ADMIN_ID, photo=msg.photo[-1].file_id, 
            caption=f"💰 **Top-up Request**\nFrom: {update.effective_user.first_name}\nID: `{user_id}`",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ 5000", callback_data=f"ap_{user_id}_5000_{bc_id}_{reply_msg.message_id}"),
                 InlineKeyboardButton("✅ 10000", callback_data=f"ap_{user_id}_10000_{bc_id}_{reply_msg.message_id}")],
                [InlineKeyboardButton("❌ Reject", callback_data=f"rj_{user_id}_{bc_id}_{reply_msg.message_id}")]
            ])
        )
        return

    text = msg.text.lower() if msg.text else ""
    if any(x in text for x in ['hi', 'hello', 'မင်္ဂလာပါ', 'start', 'ဝယ်မယ်', 'vpn', 'စျေးနှုန်း']):
        await start_handler(update, context)

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    uid, data = int(query.from_user.id), query.data
    bc_id = query.message.business_connection_id if query.message else None
    await query.answer()

    # --- Buying Logic (Format: conf_Name_Price_GB_Days_Proto_InboundID) ---
    if data.startswith('conf_'):
        p = data.split('_')
        item, price, gb, days, proto, inbound_id = p[1], float(p[2]), int(p[3]), int(p[4]), p[5], int(p[6])

        if db.get_balance(uid) < price:
            await context.bot.send_message(chat_id=uid, text=f"❌ Credit မလုံလောက်ပါ။\n{db.get_setting('payment_info')}", business_connection_id=bc_id, parse_mode='Markdown')
            return

        db.update_balance(uid, -price, f"BUY_{item}")
        await context.bot.send_message(chat_id=uid, text=f"⏳ **{item}** အတွက် Key ထုတ်ပေးနေပါပြီ...", business_connection_id=bc_id)

        try:
            xui = MultiXUI(SERVERS['S1']) 
            remark = f"Nanda_{uid}_{int(time.time())}"
            res = xui.create_user(remark, proto, gb, days, inbound_id=inbound_id)

            if res:
                msg = (f"✅ **ဝယ်ယူမှု အောင်မြင်ပါသည်!**\n\n"
                       f"📂 Product: `{item}`\n"
                       f"🌐 Sub Link: `{res['sub']}`\n\n"
                       f"🔑 Key:\n`{res['key']}`")
                await context.bot.send_message(chat_id=uid, text=msg, business_connection_id=bc_id, parse_mode='Markdown')
                await context.bot.send_message(ADMIN_ID, f"🔔 Order Success: {uid} bought {item}")
            else:
                db.update_balance(uid, price, "REFUND")
                await context.bot.send_message(chat_id=uid, text="❌ Server Error! ငွေပြန်အမ်းပေးထားပါသည်။", business_connection_id=bc_id)
        except:
            db.update_balance(uid, price, "REFUND")
            await context.bot.send_message(chat_id=uid, text="❌ ချိတ်ဆက်မှု မအောင်မြင်ပါ။", business_connection_id=bc_id)

    # --- Main Navigation ---
    elif data == 'user_buy':
        kb = [[InlineKeyboardButton("🔥 N4 VIP PRO စျေးနှုန်းများ", callback_data='n4_vip')],
              [InlineKeyboardButton("🔑 Outline & V2ray Key စျေးများ", callback_data='v2ray_menu')],
              [InlineKeyboardButton("📡 Starlink VIP ဝန်ဆောင်မှုများ", callback_data='starlink_menu')],
              [InlineKeyboardButton("🔙 Back", callback_data='back_to_main')]]
        await context.bot.send_message(chat_id=uid, text="🛍 **ဝယ်ယူလိုသော အမျိုးအစားကို ရွေးပါ**", reply_markup=InlineKeyboardMarkup(kb), business_connection_id=bc_id)

    # --- N4 VIP PRO ---
    elif data == 'n4_vip':
        kb = [[InlineKeyboardButton("💎 ၁ လစာ - 8,000 Ks", callback_data='conf_N4VIP-1M_8000_100_30_vless_1')],
              [InlineKeyboardButton("💎 ၃ လစာ - 22,000 Ks", callback_data='conf_N4VIP-3M_22000_300_90_vless_1')],
              [InlineKeyboardButton("💎 ၆ လစာ - 40,000 Ks", callback_data='conf_N4VIP-6M_40000_600_180_vless_1')],
              [InlineKeyboardButton("💎 ၁ နှစ်စာ - 75,000 Ks", callback_data='conf_N4VIP-1Y_75000_1200_365_vless_1')],
              [InlineKeyboardButton("🔙 နောက်သို့", callback_data='user_buy')]]
        await context.bot.send_message(chat_id=uid, text="🔥 **N4 VIP PRO စျေးနှုန်းများ**", reply_markup=InlineKeyboardMarkup(kb), business_connection_id=bc_id)

    # --- V2ray & Outline Menu ---
    elif data == 'v2ray_menu':
        kb = [[InlineKeyboardButton("♾ GB Limit (သက်တမ်းမရှိ)", callback_data='v2ray_gb')],
              [InlineKeyboardButton("🗓 သက်တမ်းပါသော Key များ", callback_data='v2ray_exp')],
              [InlineKeyboardButton("🇯🇵 Japan Region Key စျေး", callback_data='v2ray_jp')],
              [InlineKeyboardButton("🔙 နောက်သို့", callback_data='user_buy')]]
        await context.bot.send_message(chat_id=uid, text="🔑 **Outline & V2ray Key စျေးနှုန်းများ**", reply_markup=InlineKeyboardMarkup(kb), business_connection_id=bc_id)

    elif data == 'v2ray_gb':
        kb = [[InlineKeyboardButton("🔸 50 GB - 5,000 Ks", callback_data='conf_V2GB-50_5000_50_365_vless_1')],
              [InlineKeyboardButton("🔸 100 GB - 8,000 Ks", callback_data='conf_V2GB-100_8000_100_365_vless_1')],
              [InlineKeyboardButton("🔸 200 GB - 15,000 Ks", callback_data='conf_V2GB-200_15000_200_365_vless_1')],
              [InlineKeyboardButton("🔸 300 GB - 20,000 Ks", callback_data='conf_V2GB-300_20000_300_365_vless_1')],
              [InlineKeyboardButton("🔸 500 GB - 27,000 Ks", callback_data='conf_V2GB-500_27000_500_365_vless_1')],
              [InlineKeyboardButton("🔙 နောက်သို့", callback_data='v2ray_menu')]]
        await context.bot.send_message(chat_id=uid, text="♾ **GB Limit (No Expiry)**", reply_markup=InlineKeyboardMarkup(kb), business_connection_id=bc_id)

    elif data == 'v2ray_exp':
        kb = [[InlineKeyboardButton("🔸 100GB (1 Month) - 5,000 Ks", callback_data='conf_V2Exp-1M_5000_100_30_vless_1')],
              [InlineKeyboardButton("🔸 100GB (3 Month) - 13,000 Ks", callback_data='conf_V2Exp-3M_13000_100_90_vless_1')],
              [InlineKeyboardButton("🔸 100GB (12 Month) - 48,000 Ks", callback_data='conf_V2Exp-1Y_48000_100_365_vless_1')],
              [InlineKeyboardButton("🔙 နောက်သို့", callback_data='v2ray_menu')]]
        await context.bot.send_message(chat_id=uid, text="🗓 **သက်တမ်းပါသော Singapore Key များ**", reply_markup=InlineKeyboardMarkup(kb), business_connection_id=bc_id)

    elif data == 'v2ray_jp':
        kb = [[InlineKeyboardButton("🔸 50 GB (1 Month) - 5,000 Ks", callback_data='conf_V2JP-50_5000_50_30_vless_1')],
              [InlineKeyboardButton("🔸 100 GB (1 Month) - 8,000 Ks", callback_data='conf_V2JP-100_8000_100_30_vless_1')],
              [InlineKeyboardButton("🔙 နောက်သို့", callback_data='v2ray_menu')]]
        await context.bot.send_message(chat_id=uid, text="🇯🇵 **Japan Region (Tiktok Lite)**", reply_markup=InlineKeyboardMarkup(kb), business_connection_id=bc_id)

    # --- Starlink ---
    elif data == 'starlink_menu':
        kb = [[InlineKeyboardButton("👤 တစ်ယောက်သုံးဖိုင်စျေး", callback_data='sl_file')],
              [InlineKeyboardButton("🖥 V2ray Key စျေးများ", callback_data='sl_v2ray')],
              [InlineKeyboardButton("🔙 နောက်သို့", callback_data='user_buy')]]
        await context.bot.send_message(chat_id=uid, text="📡 **Starlink VIP ဝန်ဆောင်မှုများ**", reply_markup=InlineKeyboardMarkup(kb), business_connection_id=bc_id)

    elif data == 'sl_file':
        kb = [[InlineKeyboardButton("🔸 တလစာ - 8,000 Ks", callback_data='conf_SLFile-1M_8000_100_30_vless_1')],
              [InlineKeyboardButton("🔸 သုံးလစာ - 20,000 Ks", callback_data='conf_SLFile-3M_20000_300_90_vless_1')],
              [InlineKeyboardButton("🔙 နောက်သို့", callback_data='starlink_menu')]]
        await context.bot.send_message(chat_id=uid, text="📡 **StarLink VIP (တစ်ယောက်သုံးဖိုင်)**", reply_markup=InlineKeyboardMarkup(kb), business_connection_id=bc_id)

    # --- Other Navigation ---
    elif data == 'topup_menu' or data == 'my_acc' or data == 'back_to_main':
        bal = db.get_balance(uid)
        if data == 'topup_menu':
            txt, kb = "ဖြည့်သွင်းလိုသော ပမာဏ ရွေးချယ်ပါ-", [[InlineKeyboardButton("💳 5,000 Ks", callback_data='pay_5000')], [InlineKeyboardButton("💳 10,000 Ks", callback_data='pay_10000')], [InlineKeyboardButton("🔙 Back", callback_data='back_to_main')]]
        elif data == 'my_acc':
            txt, kb = f"👤 **Account Info**\n🆔 ID: `{uid}`\n💰 Balance: **{bal} Ks**", [[InlineKeyboardButton("📜 History", callback_data='view_history')], [InlineKeyboardButton("🔙 Back", callback_data='back_to_main')]]
        else: # back_to_main
            txt, kb = db.get_setting('welcome_msg').format(name=query.from_user.first_name, balance=bal), get_main_keyboard(uid).inline_keyboard
        await context.bot.send_message(chat_id=uid, text=txt, reply_markup=InlineKeyboardMarkup(kb), business_connection_id=bc_id, parse_mode='Markdown')

    elif data == 'view_history':
        h = db.get_history(uid)
        txt = "📜 **မှတ်တမ်း (၅) ခု**\n\n"
        for amt, t, ts in h: txt += f"{'➕' if amt > 0 else '➖'} {abs(amt)} Ks ({t})\n📅 {ts}\n\n"
        await context.bot.send_message(chat_id=uid, text=txt, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data='my_acc')]]), business_connection_id=bc_id, parse_mode='Markdown')

    elif data.startswith('pay_'):
        await context.bot.send_message(chat_id=uid, text=db.get_setting('payment_info'), business_connection_id=bc_id, parse_mode='Markdown')

    # --- Approval / Rejection ---
    elif data.startswith('ap_') or data.startswith('rj_'):
        if uid != int(ADMIN_ID): return
        p = data.split('_')
        target_id, user_bc_id = int(p[1]), (p[3] if p[3]!='None' else None)
        if data.startswith('ap_'):
            amt = float(p[2])
            db.update_balance(target_id, amt, "TOPUP")
            await context.bot.send_message(chat_id=target_id, text=f"✅ Credit **{amt} Ks** ဖြည့်သွင်းပြီးပါပြီ။", reply_markup=get_main_keyboard(target_id), business_connection_id=user_bc_id)
            await query.edit_message_caption(caption=f"{query.message.caption}\n\n✅ **Approved!**")
        else:
            await context.bot.send_message(chat_id=target_id, text="❌ သင်ပေးပို့သော ပြေစာမှာ မှားယွင်းနေပါသည်။", business_connection_id=user_bc_id)
            await query.edit_message_caption(caption=f"{query.message.caption}\n\n❌ **Rejected!**")

async def admin_add_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if int(update.effective_user.id) != int(ADMIN_ID): return
    try:
        uid, amt = int(context.args[0]), float(context.args[1])
        db.update_balance(uid, amt, "ADMIN_ADD")
        await context.bot.send_message(chat_id=uid, text=f"✅ Admin မှ Credit **{amt} Ks** သွင်းပေးလိုက်ပါသည်။", reply_markup=get_main_keyboard(uid))
        await update.message.reply_text(f"✅ Success: {uid} +{amt}")
    except: await update.message.reply_text("Usage: /add ID Amount")

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start_handler))
    app.add_handler(CommandHandler("add", admin_add_cmd))
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle_all_updates))
    app.run_polling(drop_pending_updates=True)

if __name__ == '__main__': main()
