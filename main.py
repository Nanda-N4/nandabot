import logging, time, os, asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from config import TOKEN, ADMIN_ID, ADMIN_LINK, SERVERS
from database import DBManager
from xui_api import MultiXUI
import admin

logging.basicConfig(format='%(asctime)s - %(name)s - %(message)s', level=logging.INFO)
db = DBManager()

def get_main_keyboard(uid):
    kb = [[InlineKeyboardButton("🛍 ဝယ်ယူရန်", callback_data='user_buy')],
          [InlineKeyboardButton("💰 Credits ဖြည့်ရန်", callback_data='topup_menu')],
          [InlineKeyboardButton("👤 My Account / History", callback_data='my_acc')],
          [InlineKeyboardButton("👨‍💻 Admin နှင့် တိုက်ရိုက်", url=ADMIN_LINK)]]
    if int(uid) == int(ADMIN_ID):
        kb.append([InlineKeyboardButton("🛠 Admin Panel", callback_data='admin_panel')])
    return InlineKeyboardMarkup(kb)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg_obj = update.message or update.business_message
    if not msg_obj: return
    user = update.effective_user
    bal = db.get_balance(user.id)
    msg = db.get_setting('welcome_msg').format(name=user.first_name, balance=bal)
    await msg_obj.reply_text(msg, reply_markup=get_main_keyboard(user.id), parse_mode='Markdown')

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
        # User ဆီ ပို့မယ့် Message ကို ID မှတ်ထားမယ်
        reply_msg = await msg.reply_text("✅ ပြေစာရရှိပါသည်။ Admin အတည်ပြုရန် စောင့်ပေးပါ။ 🙏")
        
        # Admin ဆီကို ပို့တဲ့အခါ User ရဲ့ message_id ကိုပါ callback data မှာ ထည့်ပေးမယ်
        await context.bot.send_photo(
            chat_id=ADMIN_ID, photo=msg.photo[-1].file_id, 
            caption=f"💰 **Top-up Request**\nFrom: {update.effective_user.first_name}\nID: `{user_id}`",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ 5000 Ks", callback_data=f"ap_{user_id}_5000_{reply_msg.message_id}"),
                 InlineKeyboardButton("✅ 10000 Ks", callback_data=f"ap_{user_id}_10000_{reply_msg.message_id}")],
                [InlineKeyboardButton("📝 Custom", callback_data=f"ap_custom_{user_id}_{reply_msg.message_id}")]
            ])
        )
        return

    text = msg.text.lower() if msg.text else ""
    if any(x in text for x in ['hi', 'hello', 'မင်္ဂလာပါ', 'စျေးနှုန်း', 'vpn', 'start', 'ဝယ်မယ်']) or msg.sticker:
        await start(update, context)

async def handle_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    uid = int(query.from_user.id)
    data = query.data
    await query.answer()

    if data.startswith('ap_'):
        if int(uid) != int(ADMIN_ID): return
        parts = data.split('_')
        target_id = int(parts[1])
        
        if 'custom' in data:
            await query.message.reply_text(f"👤 User `{target_id}` အတွက် Amount ရိုက်ထည့်ပါ-\n\n`/add {target_id} 5000`", parse_mode='Markdown')
            return
            
        amt = float(parts[2])
        user_msg_id = int(parts[3]) # User ဆီက reply စာကို edit ဖို့ ID

        if db.update_balance(target_id, amt, "TOPUP_APPROVE"):
            # ၁။ User ဆီက "ပြေစာရရှိပါသည်" ဆိုတဲ့စာကို ဝယ်ယူရန် Menu အဖြစ် Edit လုပ်မယ်
            bal = db.get_balance(target_id)
            success_msg = f"✅ Credit **{amt} Ks** ဖြည့်သွင်းမှု အောင်မြင်ပါသည်။\n💰 လက်ရှိလက်ကျန်: **{bal} Ks**"
            try:
                await context.bot.edit_message_text(
                    chat_id=target_id,
                    message_id=user_msg_id,
                    text=success_msg,
                    reply_markup=get_main_keyboard(target_id),
                    parse_mode='Markdown'
                )
            except:
                # Edit မရရင် စာအသစ် ပို့မယ်
                await context.bot.send_message(target_id, success_msg, reply_markup=get_main_keyboard(target_id), parse_mode='Markdown')

            # ၂။ Admin ဆီက caption ကို edit လုပ်မယ်
            await query.edit_message_caption(caption=f"{query.message.caption}\n\n✅ **Approved {amt} Ks!**")

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
        await query.edit_message_text(msg, reply_markup=get_main_keyboard(uid), parse_mode='Markdown')

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
        kb.append([InlineKeyboardButton("🔙 Back", callback_data='back_to_main') | InlineKeyboardButton("🔙 Back", callback_data='back_to_main')]]
        await query.edit_message_text("🏷️ **Product ရွေးချယ်ပါ**", reply_markup=InlineKeyboardMarkup(kb), parse_mode='Markdown')

    elif data.startswith('confirm_buy_'):
        pid = int(data.split('_')[-1])
        p = next((x for x in db.get_products() if x['id'] == pid), None)
        if db.get_balance(uid) < p['price']:
            await query.message.reply_text(f"❌ Credit မလုံလောက်ပါ။\n\n{db.get_setting('payment_info')}", parse_mode='Markdown')
            return
        db.update_balance(uid, -p['price'], f"BUY_{p['name']}")
        await query.edit_message_text(f"✅ **{p['name']}** ဝယ်ယူမှု အောင်မြင်ပါသည်။")

async def admin_credit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if int(update.effective_user.id) != int(ADMIN_ID): return
    try:
        uid, amt = int(context.args[0]), float(context.args[1])
        if db.update_balance(uid, amt, "ADMIN_ADD"):
            await context.bot.send_message(chat_id=uid, text=f"✅ Admin မှ Credit **{amt} Ks** ဖြည့်သွင်းပေးလိုက်ပါသည်။", reply_markup=get_main_keyboard(uid), parse_mode='Markdown')
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
