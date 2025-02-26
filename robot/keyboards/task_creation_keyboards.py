from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from ..models import TelegramUser
from asgiref.sync import sync_to_async


def get_assignment_type_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="👤 Индивидуальная задача", callback_data="individual_task")
    builder.button(text="👥 Групповая задача (всем в группе)", callback_data="group_task")
    builder.button(text="👥 Групповая задача (выбрать определенных исполнителей)", callback_data="multi_task")
    builder.button(text="❌ Отмена", callback_data="cancel_creation")
    builder.adjust(1)
    return builder.as_markup()


@sync_to_async
def get_users_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    users = TelegramUser.objects.filter(
        is_active=True, 
        is_bot=False,
        is_admin=False
    )
    
    for user in users:
        builder.button(
            text=f"👤 {user.first_name}", 
            callback_data=f"assign_user:{user.telegram_id}"
        )
    
    builder.button(text="🔓 Оставить открытой", callback_data="leave_open")
    builder.button(text="❌ Отмена", callback_data="cancel_creation")
    builder.adjust(2)
    return builder.as_markup()


def get_media_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="➡️ Пропустить", callback_data="skip_media")
    builder.button(text="❌ Отмена", callback_data="cancel_creation")
    builder.adjust(1)
    return builder.as_markup()


def get_confirm_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Подтвердить", callback_data="confirm_task")
    builder.button(text="❌ Отменить", callback_data="cancel_creation")
    builder.adjust(2)
    return builder.as_markup() 