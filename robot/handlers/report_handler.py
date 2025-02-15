from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from ..utils import identify_user
from ..models import Task, TelegramUser
from ..keyboards.report_keyboards import get_report_keyboard
from asgiref.sync import sync_to_async
from django.utils import timezone
from datetime import datetime, timedelta
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os
from ..utils.logger import logger
from zoneinfo import ZoneInfo

report_router = Router()

@sync_to_async
def get_weekly_stats():
    now = timezone.now().astimezone(ZoneInfo("Europe/Moscow"))
    week_ago = now - timedelta(days=7)
    
    return {
        'active_tasks': Task.objects.filter(
            status__in=['in_progress', 'assigned'],
            created_at__gte=week_ago
        ).count(),
        'completed_tasks': Task.objects.filter(
            status='completed',
            completed_at__gte=week_ago
        ).count(),
        'overdue_tasks': Task.objects.filter(
            status='overdue',
            deadline__gte=week_ago
        ).count(),
        'new_tasks': Task.objects.filter(
            created_at__gte=week_ago
        ).count(),
    }

async def export_to_sheets():
    scope = ['https://spreadsheets.google.com/feeds',
             'https://www.googleapis.com/auth/drive']
    
    credentials_file = os.getenv('GOOGLE_SHEETS_CREDENTIALS_FILE', 'credentials.json')
    spreadsheet_id = os.getenv('GOOGLE_SHEETS_SPREADSHEET_ID')
    
    creds = ServiceAccountCredentials.from_json_keyfile_name(
        credentials_file, scope)
    client = gspread.authorize(creds)
    
    sheet = client.open_by_key(spreadsheet_id).sheet1
    
    @sync_to_async
    def get_detailed_stats():
        now = timezone.now()
        week_ago = now - timedelta(days=7)
        tasks = Task.objects.filter(created_at__gte=week_ago).select_related('assignee')
        
        data = [['Название', 'Статус', 'Исполнитель', 'Создано', 'Дедлайн', 'Выполнено']]
        for task in tasks:
            data.append([
                task.title,
                task.status,
                task.assignee.first_name if task.assignee else 'Не назначен',
                task.created_at.strftime("%Y-%m-%d %H:%M"),
                task.deadline.strftime("%Y-%m-%d %H:%M"),
                task.completed_at.strftime("%Y-%m-%d %H:%M") if task.completed_at else '-'
            ])
        return data
    
    data = await get_detailed_stats()
    sheet.clear()
    sheet.update('A1', data)

@report_router.callback_query(F.data == "reports")
async def show_reports_menu(callback: CallbackQuery):
    user, _ = await identify_user(callback.from_user.id)
    
    if not user.is_admin:
        await callback.answer("У вас нет прав администратора!", show_alert=True)
        return
    
    stats = await get_weekly_stats()
    
    report_text = (
        "📊 Еженедельный отчет:\n\n"
        f"📝 Новых задач: {stats['new_tasks']}\n"
        f"▫️ Активных задач: {stats['active_tasks']}\n"
        f"✅ Выполнено за неделю: {stats['completed_tasks']}\n"
        f"⚠️ Просрочено за неделю: {stats['overdue_tasks']}\n\n"
        "📎 Для выгрузки детального отчета в Google Sheets\n"
        "нажмите соответствующую кнопку ниже"
    )
    
    keyboard = get_report_keyboard()
    await callback.message.edit_text(report_text, reply_markup=keyboard)
    await callback.answer()

@report_router.callback_query(F.data == "export_report")
async def handle_export_report(callback: CallbackQuery):
    user_id = callback.from_user.id
    logger.info(f"Admin {user_id} attempting to export report")
    
    try:
        user, _ = await identify_user(user_id)
        
        if not user.is_admin:
            logger.warning(f"Unauthorized report export attempt by user {user_id}")
            await callback.answer("У вас нет прав администратора!", show_alert=True)
            return
        
        await callback.answer("⏳ Подождите, идет формирование отчета...")
        logger.info(f"Starting report export for admin {user_id}")
        
        await export_to_sheets()
        logger.info(f"Successfully exported report to sheets for admin {user_id}")
        await callback.message.answer("✅ Отчет успешно выгружен в Google Sheets!")
        
    except Exception as e:
        logger.error(f"Error in handle_export_report for user {user_id}: {str(e)}", exc_info=True)
        await callback.message.answer("❌ Ошибка при выгрузке отчета. Попробуйте позже.") 