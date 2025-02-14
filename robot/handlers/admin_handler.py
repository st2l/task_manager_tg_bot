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
    get_admin_statistics_keyboard,
    get_users_list_keyboard,
    get_user_stats_keyboard
)
from django.utils import timezone
from ..utils.logger import logger

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
    user_id = callback.from_user.id
    logger.info(f"Admin {user_id} accessing statistics")
    
    try:
        user, _ = await identify_user(user_id)
        
        if not user.is_admin:
            logger.warning(f"Unauthorized statistics access attempt by user {user_id}")
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
        logger.info(f"Retrieved statistics: {stats}")
        
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
        logger.info(f"Successfully displayed statistics for admin {user_id}")
        
    except Exception as e:
        logger.error(f"Error in handle_admin_statistics for user {user_id}: {str(e)}", exc_info=True)
        await callback.answer("Произошла ошибка при загрузке статистики")

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

@sync_to_async
def get_user_statistics(user: TelegramUser):
    return {
        'completed_tasks': Task.objects.filter(assignee=user, status='completed').count(),
        'overdue_tasks': Task.objects.filter(
            assignee=user,
            status='overdue'
        ).count(),
        'in_progress_tasks': Task.objects.filter(
            assignee=user,
            status__in=['in_progress', 'assigned']
        ).count(),
        'total_assigned': Task.objects.filter(assignee=user).count()
    }

@admin_router.callback_query(F.data == "users")
async def show_users_menu(callback: CallbackQuery, state: FSMContext):
    user, _ = await identify_user(callback.from_user.id)
    
    if not user.is_admin:
        await callback.answer("У вас нет прав администратора!", show_alert=True)
        return
    
    @sync_to_async
    def get_regular_users():
        return list(TelegramUser.objects.filter(
            is_active=True,
            is_bot=False,
            is_admin=False
        ).order_by('first_name'))
    
    users = await get_regular_users()
    keyboard = get_users_list_keyboard(users)
    try:
        await callback.message.edit_text("👥 Список пользователей:", reply_markup=keyboard)
    except Exception as e:
        logging.error(f"Error in show_users_menu: {e}")
        await callback.message.answer("👥 Список пользователей:", reply_markup=keyboard)
    await callback.answer()

@admin_router.callback_query(F.data.startswith("user_stats:"))
async def show_user_stats(callback: CallbackQuery, state: FSMContext):
    admin, _ = await identify_user(callback.from_user.id)
    
    if not admin.is_admin:
        await callback.answer("У вас нет прав администратора!", show_alert=True)
        return
    
    user_id = int(callback.data.split(":")[1])
    
    @sync_to_async
    def get_user_with_stats():
        user = TelegramUser.objects.get(telegram_id=user_id)
        stats = {
            'completed_tasks': Task.objects.filter(assignee=user, status='completed').count(),
            'overdue_tasks': Task.objects.filter(
                assignee=user,
                status='overdue'
            ).count(),
            'in_progress_tasks': Task.objects.filter(
                assignee=user,
                status__in=['in_progress', 'assigned']
            ).count(),
            'total_assigned': Task.objects.filter(assignee=user).count()
        }
        return user, stats
    
    user, stats = await get_user_with_stats()
    
    stats_text = (
        f"📊 Статистика пользователя {user.first_name}:\n\n"
        f"✅ Выполнено задач: {stats['completed_tasks']}\n"
        f"⏰ Просрочено: {stats['overdue_tasks']}\n"
        f"📝 В работе: {stats['in_progress_tasks']}\n"
        f"📋 Всего назначено: {stats['total_assigned']}"
    )
    
    keyboard = get_user_stats_keyboard()
    await callback.message.edit_text(stats_text, reply_markup=keyboard)
    await callback.answer()

@admin_router.callback_query(F.data.startswith("users_page:"))
async def handle_users_pagination(callback: CallbackQuery, state: FSMContext):
    page = int(callback.data.split(":")[1])
    
    @sync_to_async
    def get_regular_users():
        return list(TelegramUser.objects.filter(
            is_active=True,
            is_bot=False,
            is_admin=False
        ).order_by('first_name'))
    
    users = await get_regular_users()
    keyboard = get_users_list_keyboard(users, page=page)
    await callback.message.edit_text("👥 Список пользователей:", reply_markup=keyboard)
    await callback.answer() 