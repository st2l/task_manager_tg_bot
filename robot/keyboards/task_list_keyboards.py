from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

def get_task_list_open_keyboard(tasks, page=1, items_per_page=5) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    
    start_idx = (page - 1) * items_per_page
    end_idx = start_idx + items_per_page
    
    for task in tasks[start_idx:end_idx]:
        status_emoji = "✅" if task.status == 'completed' else "📝"
        builder.button(
            text=f"{status_emoji} {task.title[:30]}...",
            callback_data=f"view_task:{task.id}"
        )
    
    # Навигационные кнопки
    if len(tasks) > items_per_page:
        if page > 1:
            builder.button(text="⬅️", callback_data=f"task_page:{page-1}")
        if end_idx < len(tasks):
            builder.button(text="➡️", callback_data=f"task_page:{page+1}")
    
    builder.button(text="◀️ Назад", callback_data="back_to_main")
    builder.adjust(1)
    return builder.as_markup()


def get_task_list_keyboard(tasks, page=1, items_per_page=5, is_open_tasks=False) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    
    start_idx = (page - 1) * items_per_page
    end_idx = start_idx + items_per_page
    
    for task in tasks[start_idx:end_idx]:
        status_emoji = "✅" if task.status == 'completed' else "📝"
        if task.status == 'overdue':
            status_emoji = "⏰"
        builder.button(
            text=f"{status_emoji} {task.title}",
            callback_data=f"view_task:{task.id}"
        )
    
    # Navigation row
    nav_buttons = []
    if len(tasks) > items_per_page:
        if page > 1:
            nav_buttons.append(InlineKeyboardButton(text="⬅️", callback_data=f"task_page:{page-1}"))
        nav_buttons.append(InlineKeyboardButton(text=f"{page}/{(len(tasks) + items_per_page - 1) // items_per_page}", callback_data="current_page"))
        if end_idx < len(tasks):
            nav_buttons.append(InlineKeyboardButton(text="➡️", callback_data=f"task_page:{page+1}"))
    
    if nav_buttons:
        builder.row(*nav_buttons)
    
    # Add filter buttons based on context
    if is_open_tasks:
        builder.button(text="◀️ Назад", callback_data="back_to_main")
    else:
        builder.button(text="📋 Текущие задачи", callback_data="my_tasks")
        builder.button(text="✅ Выполненные", callback_data="user_completed_tasks")
        builder.button(text="⏰ Просроченные", callback_data="user_overdue_tasks")
        builder.button(text="◀️ Назад", callback_data="back_to_main")
    
    builder.adjust(1)
    return builder.as_markup()

def get_task_detail_keyboard(task_id: int, user_is_admin: bool = False, task_status: str = 'open') -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    
    if task_status == 'open' and not user_is_admin:
        builder.button(text="✅ Взять в работу", callback_data=f"take_task:{task_id}")
    elif (task_status == 'in_progress' or task_status == 'assigned') and not user_is_admin:
        builder.button(text="📤 Сдать задание", callback_data=f"submit_task:{task_id}")
    
    if user_is_admin:
        builder.button(text="❌ Удалить", callback_data=f"delete_task:{task_id}")
        builder.button(text="📝 Редактировать", callback_data=f"edit_task:{task_id}")
    
    builder.button(text="◀️ Назад к списку", callback_data="back_to_task_list")
    builder.adjust(1)
    return builder.as_markup()


def get_open_task_detail_keyboard(task_id: int, user_is_admin: bool = False, task_status: str = 'open') -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    
    if task_status == 'open':
        builder.button(text="✅ Взять в работу", callback_data=f"take_task:{task_id}")
    elif task_status == 'in_progress' or task_status == 'assigned':
        builder.button(text="📤 Сдать задание", callback_data=f"submit_task:{task_id}")
    
    if user_is_admin:
        builder.button(text="❌ Удалить", callback_data=f"delete_task:{task_id}")
        builder.button(text="📝 Редактировать", callback_data=f"edit_task:{task_id}")
    
    builder.button(text="◀️ Назад к списку", callback_data="available_tasks")
    builder.adjust(1)
    return builder.as_markup()

def get_user_filter_keyboard(users, page=1, items_per_page=5) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    
    start_idx = (page - 1) * items_per_page
    end_idx = start_idx + items_per_page
    
    for user in users[start_idx:end_idx]:
        builder.button(
            text=f"👤 {user.first_name}",
            callback_data=f"filter_tasks_user:{user.telegram_id}"
        )
    
    # Navigation buttons
    if len(users) > items_per_page:
        if page > 1:
            builder.button(text="⬅️", callback_data=f"user_filter_page:{page-1}")
        if end_idx < len(users):
            builder.button(text="➡️", callback_data=f"user_filter_page:{page+1}")
    
    builder.button(text="❌ Сбросить фильтр", callback_data="clear_filter")
    builder.button(text="◀️ Назад", callback_data="tasks")
    builder.adjust(1)
    return builder.as_markup() 