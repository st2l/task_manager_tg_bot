from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

def get_report_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="📊 Dump to Google Sheets", callback_data="export_report")
    builder.button(text="◀️ Back", callback_data="back_to_main")
    builder.adjust(1)
    return builder.as_markup() 