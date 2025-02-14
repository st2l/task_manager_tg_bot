from .base_scheduler import scheduler
from ..models import Task, TelegramUser
from django.utils import timezone
from asgiref.sync import sync_to_async
from datetime import datetime, timedelta
import logging

@sync_to_async
def get_tasks_with_deadline_approaching(hours: int):
    deadline_threshold = timezone.now() + timedelta(hours=hours)
    return list(Task.objects.filter(
        status__in=['open', 'in_progress', 'assigned'],
        deadline__lte=deadline_threshold,
        deadline__gt=timezone.now()
    ).select_related('assignee', 'creator'))


@sync_to_async
def get_admin_users():
    return list(TelegramUser.objects.filter(is_admin=True))


@sync_to_async
def get_task_assignee_notification_status(task):
    return task.assignee and task.assignee.notification_enabled


@sync_to_async
def get_task_notification_details(task):
    return {
        'telegram_id': task.assignee.telegram_id,
        'title': task.title,
        'deadline': task.deadline.strftime('%d.%m.%Y %H:%M')
    }


async def send_deadline_notifications(bot, hours: int):
    tasks = await get_tasks_with_deadline_approaching(hours)
    logging.info(f"Found {len(tasks)} tasks with deadline approaching in {hours} hours")
    admins = await get_admin_users()
    
    time_text = {
        48: "2 дня",
        24: "24 часа",
        1: "1 час"
    }.get(hours, f"{hours} часов")
    
    for task in tasks:
        # Уведомление исполнителю
        if task.assignee and task.assignee.notification_enabled:
            await bot.send_message(
                task.assignee.telegram_id,
                f"⚠️ Напоминание!\n"
                f"До дедлайна задачи «{task.title}» осталось {time_text}!\n"
                f"Дедлайн: {task.deadline.strftime('%d.%m.%Y %H:%M')}"
            )
        
        # Уведомление администраторам о критических задачах
        if hours <= 24:
            for admin in admins:
                if admin.notification_enabled:
                    await bot.send_message(
                        admin.telegram_id,
                        f"🚨 Внимание администратору!\n"
                        f"Задача «{task.title}» в критическом статусе!\n"
                        f"До дедлайна осталось {time_text}\n"
                        f"Исполнитель: {task.assignee.first_name if task.assignee else 'Не назначен'}\n"
                        f"Дедлайн: {task.deadline.strftime('%d.%m.%Y %H:%M')}"
                    )


@sync_to_async
def get_overdue_tasks():
    now = timezone.now()
    return list(Task.objects.filter(
        status__in=['open', 'in_progress', 'assigned'],
        deadline__lt=now
    ))


async def check_overdue_tasks(bot):
    tasks = await get_overdue_tasks()
    admins = await get_admin_users()
    
    for task in tasks:
        if task.status != 'overdue':
            task.status = 'overdue'
            await sync_to_async(task.save)()
            
            # Уведомление исполнителю
            if task.assignee and task.assignee.notification_enabled:
                await bot.send_message(
                    task.assignee.telegram_id,
                    f"🚨 Внимание!\n"
                    f"Задача «{task.title}» просрочена!\n"
                    f"Дедлайн был: {task.deadline.strftime('%d.%m.%Y %H:%M')}"
                )
            
            # Уведомление администраторам
            for admin in admins:
                if admin.notification_enabled:
                    await bot.send_message(
                        admin.telegram_id,
                        f"🚨 Внимание администратору!\n"
                        f"Задача «{task.title}» просрочена!\n"
                        f"Исполнитель: {task.assignee.first_name if task.assignee else 'Не назначен'}\n"
                        f"Дедлайн был: {task.deadline.strftime('%d.%m.%Y %H:%M')}"
                    )


def setup_task_schedulers(bot):
    # Проверка дедлайнов за 48 часов
    scheduler.add_job(
        send_deadline_notifications,
        'interval',
        hours=1,
        args=[bot, 48]
    )
    
    # Проверка дедлайнов за 24 часа
    scheduler.add_job(
        send_deadline_notifications,
        'interval',
        hours=1,
        args=[bot, 24]
    )
    
    # Проверка дедлайнов за 1 час
    scheduler.add_job(
        send_deadline_notifications,
        'interval',
        minutes=15,
        args=[bot, 1]
    )
    
    # Проверка просроченных задач
    scheduler.add_job(
        check_overdue_tasks,
        'interval',
        minutes=10,
        args=[bot]
    )
