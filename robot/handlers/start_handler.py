from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from robot.utils import get_text_by_name, identify_user
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from django.db.models.query import sync_to_async

start_router = Router()


def get_admin_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="📝 Управление задачами", callback_data="tasks")
    builder.button(text="📊 Статистика", callback_data="statistics")
    builder.button(text="👤 Пользователи", callback_data="users")
    builder.adjust(2)
    return builder.as_markup()


def get_user_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="📋 Мои задачи", callback_data="my_tasks")
    builder.button(text="📝 Новые задачи", callback_data="available_tasks")
    builder.adjust(2)
    return builder.as_markup()


@start_router.message(Command("start"))
async def handle_start(message: Message):
    user, is_new = await identify_user(message.from_user.id)
    
    if user.is_admin:
        keyboard = get_admin_keyboard()  # Теперь включает кнопку "Пользователи"
        await message.answer("Добро пожаловать в панель администратора!", reply_markup=keyboard)
    else:
        keyboard = get_user_keyboard()
        await message.answer("Добро пожаловать!", reply_markup=keyboard)
