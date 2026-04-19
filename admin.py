# admin.py
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

async def get_admin_menu():
    keyboard = [
        [InlineKeyboardButton("📊 Server Status", callback_data='admin_status')],
        [InlineKeyboardButton("📂 Manual Backup", callback_data='admin_backup')],
        [InlineKeyboardButton("🏠 Main Menu", callback_data='back_to_main')]
    ]
    return InlineKeyboardMarkup(keyboard)
