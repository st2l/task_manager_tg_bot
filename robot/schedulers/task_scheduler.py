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
        'deadline': task.deadline.strftime('%m/%d/%Y %I:%M %p')
    }


async def send_deadline_notifications(bot, hours: int):
    tasks = await get_tasks_with_deadline_approaching(hours)
    logging.info(f"Found {len(tasks)} tasks with deadline approaching in {hours} hours")
    admins = await get_admin_users()
    
    time_text = {
        48: "2 days",
        24: "24 hours",
        1: "1 hour"
    }.get(hours, f"{hours} hours")
    
    for task in tasks:
        assignee = await get_task_assignee(task)
        # Notify assignee
        if assignee:
            await bot.send_message(
                assignee.telegram_id,
                f"⚠️ Reminder!\n"
                f"The deadline for the task «{task.title}» is in {time_text}!\n"
                f"Deadline: {task.deadline.strftime('%m/%d/%Y %I:%M %p')}"
            )
        
        # Notify admins about critical tasks
        if hours <= 24:
            for admin in admins:
                await bot.send_message(
                    admin.telegram_id,
                    f"🚨 Attention, Admin!\n"
                    f"The task «{task.title}» is in a critical status!\n"
                    f"Time left: {time_text}\n"
                    f"Assignee: {assignee.first_name if assignee else 'Not assigned'}\n"
                    f"Deadline: {task.deadline.strftime('%m/%d/%Y %I:%M %p')}"
                )


@sync_to_async
def get_overdue_tasks():
    now = timezone.now()
    return list(Task.objects.filter(
        status__in=['open', 'in_progress', 'assigned'],
        deadline__lt=now
    ))

@sync_to_async
def get_task_assignee(task):
    return task.assignee

async def check_overdue_tasks(bot):
    tasks = await get_overdue_tasks()
    admins = await get_admin_users()
    
    for task in tasks:
        if task.status != 'overdue':
            task.status = 'overdue'
            await sync_to_async(task.save)()
            assignee = await get_task_assignee(task)
            # Notify assignee
            if assignee:
                await bot.send_message(
                    assignee.telegram_id,
                    f"🚨 Attention!\n"
                    f"The task «{task.title}» is overdue!\n"
                    f"Deadline was: {task.deadline.strftime('%m/%d/%Y %I:%M %p')}"
                )
            
            # Notify admins
            for admin in admins:
                if admin.notification_enabled:
                    await bot.send_message(
                        admin.telegram_id,
                        f"🚨 Attention, Admin!\n"
                        f"The task «{task.title}» is overdue!\n"
                        f"Assignee: {assignee.first_name if assignee else 'Not assigned'}\n"
                        f"Deadline was: {task.deadline.strftime('%m/%d/%Y %I:%M %p')}"
                    )

async def check_overdue_tasks_1(bot):
    now = timezone.now()
    one_hour_ago = now - timedelta(hours=1)

    tasks = await sync_to_async(list)(Task.objects.filter(
        status__in=['overdue'],
        deadline__lte=one_hour_ago,
        deadline__gt=now - timedelta(hours=2),
        is_notified_one_hour=False
    ))
    admins = await get_admin_users()
    
    for task in tasks:
        assignee = await get_task_assignee(task)
        # Notify assignee
        if assignee:
            await bot.send_message(
                assignee.telegram_id,
                f"🚨 Attention!\n"
                f"The task «{task.title}» is overdue for 1 hour!\n"
                f"Deadline was: {task.deadline.strftime('%m/%d/%Y %I:%M %p')}"
            )
        
        # Notify admins
        for admin in admins:
            if admin.notification_enabled:
                await bot.send_message(
                    admin.telegram_id,
                    f"🚨 Attention, Admin!\n"
                    f"The task «{task.title}» is overdue for 1 hour!\n"
                    f"Assignee: {assignee.first_name if assignee else 'Not assigned'}\n"
                    f"Deadline was: {task.deadline.strftime('%m/%d/%Y %I:%M %p')}"
                )
        task.is_notified_one_hour = True
        await sync_to_async(task.save)()

async def check_overdue_tasks_4_hours(bot):
    now = timezone.now()
    four_hours_ago = now - timedelta(hours=4)

    tasks = await sync_to_async(list)(Task.objects.filter(
        status__in=['overdue'],
        deadline__lte=four_hours_ago,
        deadline__gt=now - timedelta(hours=5),
        is_notified_4_hours=False
    ))
    admins = await get_admin_users()
    
    for task in tasks:
        assignee = await get_task_assignee(task)
        # Notify assignee
        if assignee:
            await bot.send_message(
                assignee.telegram_id,
                f"🚨 Attention!\n"
                f"The task «{task.title}» is overdue for 4 hours!\n"
                f"Deadline was: {task.deadline.strftime('%m/%d/%Y %I:%M %p')}"
            )
        
        # Notify admins
        for admin in admins:
            if admin.notification_enabled:
                await bot.send_message(
                    admin.telegram_id,
                    f"🚨 Attention, Admin!\n"
                    f"The task «{task.title}» is overdue for 4 hours!\n"
                    f"Assignee: {assignee.first_name if assignee else 'Not assigned'}\n"
                    f"Deadline was: {task.deadline.strftime('%m/%d/%Y %I:%M %p')}"
                )
        task.is_notified_4_hours = True
        await sync_to_async(task.save)()

def setup_task_schedulers(bot):
    # Check deadlines 48 hours in advance
    scheduler.add_job(
        send_deadline_notifications,
        'interval',
        hours=24,
        args=[bot, 48]
    )
    
    # Check deadlines 24 hours in advance
    scheduler.add_job(
        send_deadline_notifications,
        'interval',
        hours=24,
        args=[bot, 24]
    )
    
    # Check deadlines 1 hour in advance
    scheduler.add_job(
        send_deadline_notifications,
        'interval',
        hours=1,
        args=[bot, 1]
    )
    
    # Check overdue tasks
    scheduler.add_job(
        check_overdue_tasks,
        'interval',
        minutes=10,
        args=[bot]
    )
    
    # Check overdue tasks FOR 1 HOUR
    scheduler.add_job(
        check_overdue_tasks_1,
        'interval',
        hours=1,
        args=[bot]
    )
    
    # Check overdue tasks FOR 4 HOUR
    scheduler.add_job(
        check_overdue_tasks_4_hours,
        'interval',
        hours=1,
        args=[bot]
    )