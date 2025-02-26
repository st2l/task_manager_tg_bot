from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from ..models import TelegramUser
from asgiref.sync import sync_to_async


def get_assignment_type_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="👤 Individual Task", callback_data="individual_task")
    builder.button(text="👥 Group Task (to everyone in the group)", callback_data="group_task")
    builder.button(text="👥 Group Task (select specific executors)", callback_data="multi_task")
    builder.button(text="❌ Cancel", callback_data="cancel_creation")
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
    
    builder.button(text="🔓 Leave Open", callback_data="leave_open")
    builder.button(text="❌ Cancel", callback_data="cancel_creation")
    builder.adjust(2)
    return builder.as_markup()


@sync_to_async
def get_multi_users_keyboard(selected_users=None, page=0, page_size=8) -> InlineKeyboardMarkup:
    if selected_users is None:
        selected_users = []
    
    builder = InlineKeyboardBuilder()
    
    users = list(TelegramUser.objects.filter(
        is_active=True, 
        is_bot=False,
        is_admin=False
    ))
    
    total_pages = (len(users) + page_size - 1) // page_size
    start_index = page * page_size
    end_index = min((page + 1) * page_size, len(users))
    
    visible_users = users[start_index:end_index]
    
    for user in visible_users:
        is_selected = user.telegram_id in selected_users
        prefix = "✅ " if is_selected else "👤 "
        builder.button(
            text=f"{prefix}{user.first_name}", 
            callback_data=f"multi_select:{user.telegram_id}"
        )
    
    # Navigation row
    if total_pages > 1:
        if page > 0:
            builder.button(text="◀️ Back", callback_data=f"multi_page:{page-1}")
        
        builder.button(text=f"📄 {page+1}/{total_pages}", callback_data="ignore")
        
        if page < total_pages - 1:
            builder.button(text="▶️ Next", callback_data=f"multi_page:{page+1}")
    
    # Control row
    builder.button(text="✅ Finish Selection", callback_data="multi_confirm")
    builder.button(text="❌ Cancel", callback_data="cancel_creation")
    
    # Adjust the layout
    builder.adjust(2)
    return builder.as_markup()


def get_media_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="➡️ Skip", callback_data="skip_media")
    builder.button(text="❌ Cancel", callback_data="cancel_creation")
    builder.adjust(1)
    return builder.as_markup()


def get_confirm_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Confirm", callback_data="confirm_task")
    builder.button(text="❌ Cancel", callback_data="cancel_creation")
    builder.adjust(2)
    return builder.as_markup()