import logging, time, os, asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from config import TOKEN, ADMIN_ID, ADMIN_LINK, SERVERS
from database import DBManager
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
    # Business Chat ထဲမှာ စာပြန်ဖို့အတွက် business_message ကို ဦးစားပေးယူမယ်
    msg_obj = update.business_message or update.message
    if not msg_obj: return
    
    user = update.effective_user
    bal = db.get_balance(user.id)
    msg = db.get_setting('welcome_msg').format(name=user.first_name, balance=bal)
    
    # reply_text ကို သုံးရင် သူက ဘယ် Chat ထဲမှာ စာပို့ပို့ အဲ့ဒီ chat ထဲမှာပဲ ပြန်ဖြေမှာပါ
    await msg_obj.reply_text(msg, reply_markup=get_main_keyboard(user.id), parse_mode='Markdown')

async def handle_msg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.business_message or update.message
    if not msg or not update.effective_user: return
    user_id = int(update.effective_user.id)

    # Admin Editing Logic
    if user_id == int(ADMIN_ID) and 'editing_key' in context.user_data:
        key = context.user_data.pop('editing_key')
        db.update_setting(key, msg.text)
        await msg.reply_text(f"✅ `{key}` ကို ပြင်ဆင်ပြီးပါပြီ။")
        return

    # Admin ကိုယ်တိုင် စာရိုက်တာကို ignore လုပ်မယ် (Business message မဟုတ်ရင်)
    if user_id == int(ADMIN_ID) and not update.business_message: return

    if msg.photo:
        # User ရဲ့ Chat ထဲမှာပဲ "ပြေစာရရှိပါသည်" လို့ စာပြန်မယ်
        reply_msg = await msg.reply_text("✅ ပြေစာရရှိပါသည်။ Admin အတည်ပြုရန် စောင့်ပေးပါ။ 🙏")
        
        # Admin (နန္ဒ) ဆီကို Bot က သီးသန့် Noti လှမ်းပို့မယ်
        await context.bot.send_photo(
            chat_id=ADMIN_ID, 
            photo=msg.photo[-1].file_id, 
            caption=f"💰 **Top-up Request**\nFrom: {update.effective_user.first_name}\nID: `{user_id}`",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ 5000 Ks", callback_data=f"ap_{user_id}_5000_{reply_msg.message_id}"),
                 InlineKeyboardButton("✅ 10000 Ks", callback_data=f"ap_{user_id}_10000_{reply_msg.message_id}")]
            ])
        )
        return

    text = msg.text.lower() if msg.text else ""
    if any(x in text for x in ['hi', 'hello', 'မင်္ဂလာပါ', 'စျေးနှုန်း', 'vpn', 'start', 'ဝယ်မယ်']):
        await start(update, context)

async def handle_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    uid = int(query.from_user.id)
    data = query.data
    await query.answer()

    if data.startswith('ap_'):
        if int(uid) != int(ADMIN_ID): return
        parts = data.split('_')
        target_id, amt, user_msg_id = int(parts[1]), float(parts[2]), int(parts[3])

        if db.update_balance(target_id, amt, "TOPUP_APPROVE"):
            bal = db.get_balance(target_id)
            success_msg = f"✅ Credit **{amt} Ks** ဖြည့်သွင်းမှု အောင်မြင်ပါသည်။\n💰 လက်ရှိလက်ကျန်: **{bal} Ks**"
            
            # User ရဲ့ chat ထဲမှာ ရှိနေတဲ့ "ပြေစာရရှိပါသည်" ဆိုတဲ့စာကို Menu အဖြစ် ပြောင်းပေးလိုက်မယ်
            try:
                await context.bot.edit_message_text(
                    chat_id=target_id, 
                    message_id=user_msg_id, 
                    text=success_msg, 
                    reply_markup=get_main_keyboard(target_id), 
                    parse_mode='Markdown'
                )
            except:
                # Edit မရရင် (ဥပမာ User က chat list ထဲမှာ မဟုတ်ရင်) တိုက်ရိုက် message အသစ်ပို့မယ်
                await context.bot.send_message(target_id, success_msg, reply_markup=get_main_keyboard(target_id), parse_mode='Markdown')
            
            # Admin ဆီက Noti message ကို caption ပြင်မယ်
            await query.edit_message_caption(caption=f"{query.message.caption}\n\n✅ **Approved {amt} Ks!**")

    # (ကျန်တဲ့ Navigation Logic တွေက အရင်အတိုင်းပါပဲ...)
    elif data == 'back_to_main':
        bal = db.get_balance(uid)
        msg = db.get_setting('welcome_msg').format(name=query.from_user.first_name, balance=bal)
        await query.edit_message_text(msg, reply_markup=get_main_keyboard(uid), parse_mode='Markdown')

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_cb))
    # filters.ChatType.BUSINESS ကို သုံးပြီး Business Chat တွေကို ပိုဦးစားပေးမယ်
    app.add_handler(MessageHandler((filters.TEXT | filters.PHOTO) & ~filters.COMMAND, handle_msg))
    app.run_polling(drop_pending_updates=True)

if __name__ == '__main__': main()
