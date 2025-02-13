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
    builder.button(text="⚙️ Настройки", callback_data="settings")
    builder.adjust(2)
    return builder.as_markup()


def get_user_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="📋 Мои задачи", callback_data="my_tasks")
    builder.button(text="📝 Новые задачи", callback_data="available_tasks")
    builder.button(text="⚙️ Настройки", callback_data="settings")
    builder.adjust(2)
    return builder.as_markup()


@start_router.message(Command("start"))
async def start(message: Message):
    user, is_new = await identify_user(telegram_id=message.from_user.id)

    # Обновляем информацию о пользователе
    from_user = message.from_user
    user.first_name = from_user.first_name
    user.username = from_user.username
    await sync_to_async(user.save)()

    if is_new:
        welcome_text = await get_text_by_name(
            "start_new_user",
            "👋 Добро пожаловать в систему управления задачами!\n\n"
            "Здесь вы можете просматривать свои задачи, брать новые и отмечать их выполнение."
        )
    else:
        welcome_text = await get_text_by_name(
            "start_old_user",
            "🔄 С возвращением!\n\n"
            "Выберите нужное действие в меню ниже:"
        )

    # Показываем соответствующую клавиатуру в зависимости от прав пользователя
    keyboard = get_admin_keyboard() if user.is_admin else get_user_keyboard()
    await message.answer(welcome_text, reply_markup=keyboard)
