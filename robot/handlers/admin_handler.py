from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from ..utils import identify_user
from asgiref.sync import sync_to_async
from ..models import Task, TelegramUser
from datetime import datetime, timedelta
from ..keyboards.admin_keyboards import (
    get_admin_settings_keyboard,
    get_admin_task_list_keyboard,
    get_admin_statistics_keyboard
)

admin_router = Router()

@admin_router.callback_query(F.data == "tasks")
async def handle_admin_tasks(callback: CallbackQuery):
    user, _ = await identify_user(callback.from_user.id)
    
    if not user.is_admin:
        await callback.answer("У вас нет прав администратора!", show_alert=True)
        return

    keyboard = get_admin_task_list_keyboard()
    await callback.message.edit_text("🗂 Управление задачами:", reply_markup=keyboard)
    await callback.answer()

@admin_router.callback_query(F.data == "statistics")
async def handle_admin_statistics(callback: CallbackQuery):
    user, _ = await identify_user(callback.from_user.id)
    
    if not user.is_admin:
        await callback.answer("У вас нет прав администратора!", show_alert=True)
        return

    @sync_to_async
    def get_statistics():
        now = datetime.now()
        return {
            'total_tasks': Task.objects.count(),
            'active_tasks': Task.objects.filter(status='in_progress').count(),
            'completed_tasks': Task.objects.filter(status='completed').count(),
            'overdue_tasks': Task.objects.filter(
                status__in=['open', 'in_progress'],
                deadline__lt=now
            ).count(),
            'users_count': TelegramUser.objects.filter(is_active=True).count()
        }

    stats = await get_statistics()
    
    stats_text = (
        "📊 Статистика:\n\n"
        f"📝 Всего задач: {stats['total_tasks']}\n"
        f"▫️ Активных: {stats['active_tasks']}\n"
        f"✅ Завершённых: {stats['completed_tasks']}\n"
        f"⚠️ Просроченных: {stats['overdue_tasks']}\n"
        f"👥 Активных пользователей: {stats['users_count']}"
    )
    
    keyboard = get_admin_statistics_keyboard()
    await callback.message.edit_text(stats_text, reply_markup=keyboard)
    await callback.answer()

@admin_router.callback_query(F.data == "settings")
async def handle_admin_settings(callback: CallbackQuery):
    user, _ = await identify_user(callback.from_user.id)
    
    if not user.is_admin:
        await callback.answer("У вас нет прав администратора!", show_alert=True)
        return

    settings_text = (
        "⚙️ Настройки администратора:\n\n"
        f"🔔 Уведомления: {'Включены' if user.notification_enabled else 'Выключены'}\n"
        "👥 Управление пользователями\n"
        "📝 Настройка шаблонов\n"
        "⏰ Настройка напоминаний"
    )
    
    keyboard = get_admin_settings_keyboard()
    await callback.message.edit_text(settings_text, reply_markup=keyboard)
    await callback.answer() 