from telegram import InlineKeyboardButton, InlineKeyboardMarkup

async def get_admin_menu():
    keyboard = [
        [InlineKeyboardButton("📝 Edit စာသားများ", callback_data='admin_edit_text')],
        [InlineKeyboardButton("📦 Product စီမံရန်", callback_data='admin_manage_prod')],
        [InlineKeyboardButton("📂 DB Backup", callback_data='admin_backup')],
        [InlineKeyboardButton("🏠 Main Menu", callback_data='back_to_main')]
    ]
    return InlineKeyboardMarkup(keyboard)
