from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

def get_user_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="📋 Мои задачи", callback_data="my_tasks")
    builder.button(text="📥 Новые задачи", callback_data="open_tasks")
    builder.adjust(1)
    return builder.as_markup() 