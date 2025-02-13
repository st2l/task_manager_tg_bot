from aiogram.types import InlineKeyboardMarkup
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