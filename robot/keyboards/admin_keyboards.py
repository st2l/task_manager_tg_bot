from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

def get_admin_settings_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="👥 Управление пользователями", callback_data="manage_users")
    builder.button(text="🔔 Настройка уведомлений", callback_data="notification_settings")
    builder.button(text="📝 Шаблоны сообщений", callback_data="message_templates")
    builder.button(text="📊 Экспорт данных", callback_data="export_data")
    builder.button(text="◀️ Назад", callback_data="back_to_main")
    builder.adjust(2)
    return builder.as_markup()

def get_admin_task_list_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="📝 Создать задачу", callback_data="create_task")
    builder.button(text="📋 Все задачи", callback_data="all_tasks")
    builder.button(text="👤 Фильтр по пользователю", callback_data="filter_by_user")
    builder.button(text="⏰ Просроченные", callback_data="overdue_tasks")
    builder.button(text="✅ Выполненные", callback_data="completed_tasks")
    builder.button(text="◀️ Назад", callback_data="back_to_main")
    builder.adjust(2)
    return builder.as_markup()

def get_admin_statistics_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="📊 Подробный отчёт", callback_data="detailed_stats")
    builder.button(text="📅 За неделю", callback_data="weekly_stats")
    builder.button(text="📈 За месяц", callback_data="monthly_stats")
    builder.button(text="◀️ Назад", callback_data="back_to_main")
    builder.adjust(2)
    return builder.as_markup()

def get_users_list_keyboard(users, page=1, items_per_page=5) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    
    start_idx = (page - 1) * items_per_page
    end_idx = start_idx + items_per_page
    
    for user in users[start_idx:end_idx]:
        builder.button(
            text=f"👤 {user.first_name}",
            callback_data=f"user_stats:{user.telegram_id}"
        )
    
    # Navigation buttons
    nav_buttons = []
    if len(users) > items_per_page:
        if page > 1:
            nav_buttons.append(InlineKeyboardButton(text="⬅️", callback_data=f"users_page:{page-1}"))
        nav_buttons.append(InlineKeyboardButton(text=f"{page}/{(len(users) + items_per_page - 1) // items_per_page}", callback_data="current_page"))
        if end_idx < len(users):
            nav_buttons.append(InlineKeyboardButton(text="➡️", callback_data=f"users_page:{page+1}"))
    
    if nav_buttons:
        builder.row(*nav_buttons)
    
    builder.button(text="◀️ Назад", callback_data="back_to_main")
    builder.adjust(1)
    return builder.as_markup()

def get_user_stats_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="👥 К списку пользователей", callback_data="users")
    builder.button(text="◀️ В главное меню", callback_data="back_to_main")
    builder.adjust(1)
    return builder.as_markup()

def get_admin_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="📝 Управление задачами", callback_data="tasks")
    builder.button(text="👥 Пользователи", callback_data="users")
    builder.button(text="📊 Статистика", callback_data="statistics")
    builder.adjust(2)
    return builder.as_markup() 