from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from ..utils import identify_user
from ..models import Task, TaskCompletion, TelegramUser, TaskComment
from ..keyboards.task_list_keyboards import get_task_list_keyboard, get_task_detail_keyboard, get_task_list_open_keyboard, get_open_task_detail_keyboard, get_user_filter_keyboard
from asgiref.sync import sync_to_async
from ..states.task_states import TaskSubmission
from django.utils import timezone
from aiogram.utils.keyboard import InlineKeyboardBuilder
from django.db import models
from django.db.models import Q
from ..utils.message_utils import safe_edit_message, send_task_message
from ..utils.logger import logger
import logging
from aiogram.fsm.state import State, StatesGroup
from zoneinfo import ZoneInfo

task_management_router = Router()


@sync_to_async
def get_user_tasks(user, state: str = '*'):
    if state == '*':
        return list(Task.objects.filter(
            (models.Q(assignee=user) & ~models.Q(status__in=['open', 'completed'])) |
            (models.Q(is_group_task=True) & models.Q(status='in_progress'))
        ))
    elif state == 'my_tasks':
        logging.info(f"Getting user tasks for user {user.id} with state {state}")
        logging.info(f"length = {len(list(Task.objects.filter(
            (models.Q(assignee=user) | models.Q(is_group_task=True)),
            status__in=['in_progress', 'assigned', 'overdue']
        ).order_by('-created_at')))}")
        return list(Task.objects.filter(
            (models.Q(assignee=user) | models.Q(is_group_task=True)),
            status__in=['in_progress', 'assigned', 'overdue']
        ).order_by('-created_at'))
    elif state == 'user_completed_tasks':
        return list(Task.objects.filter(
            (models.Q(assignee=user) | models.Q(is_group_task=True)),
            status='completed'
        ).order_by('-completed_at'))
    elif state == 'user_overdue_tasks':
        return list(Task.objects.filter(
            (models.Q(assignee=user) | models.Q(is_group_task=True)),
            status='overdue'
        ).order_by('deadline'))

@sync_to_async
def get_open_tasks():
    return list(Task.objects.filter(status='open'))


@sync_to_async
def get_admin_task_list(state: str = '*'):
    if state == '*':
        return list(Task.objects.all().order_by('-created_at'))
    elif state == 'my_tasks':
        return list(Task.objects.filter(status__in=['in_progress', 'assigned', 'overdue']).order_by('-created_at'))
    elif state == 'user_completed_tasks':
        return list(Task.objects.filter(status='completed').order_by('-completed_at'))
    elif state == 'user_overdue_tasks':
        return list(Task.objects.filter(status='overdue').order_by('deadline'))

@sync_to_async
def get_completed_tasks():
    return list(Task.objects.filter(status='completed').order_by('-completed_at'))


@sync_to_async
def get_overdue_tasks():
    now = timezone.now().astimezone(ZoneInfo("Europe/Moscow"))
    return list(Task.objects.filter(
        models.Q(status__in=['open', 'in_progress', 'assigned', 'overdue']) &
        models.Q(deadline__lt=now)
    ).order_by('deadline'))


@sync_to_async
def get_task_with_completions(task_id):
    task = Task.objects.get(id=task_id)
    if task.is_group_task:
        completions_count = TaskCompletion.objects.filter(task=task).count()
        return task, completions_count
    return task, None


@sync_to_async
def assign_task_to_user(task_id, user):
    task = Task.objects.get(id=task_id)
    if not task.is_group_task:
        if task.assignee:
            return None
        task.assignee = user
    task.status = 'in_progress'
    task.save()
    return task


@sync_to_async
def complete_individual_task(task_id):
    task = Task.objects.get(id=task_id)
    task.status = 'completed'
    task.completed_at = timezone.now().astimezone(ZoneInfo("Europe/Moscow"))
    task.save()
    return task


@sync_to_async
def create_task_completion(task_id, user, comment=None):
    task = Task.objects.get(id=task_id)
    completion = TaskCompletion.objects.create(
        task=task,
        user=user,
        comment=comment
    )
    return task


@sync_to_async
def get_user_filtered_tasks(user_id, state: str = '*'):
    logging.info(f"Getting user filtered tasks for user {user_id} with state {state}")
    filtered_user = TelegramUser.objects.get(telegram_id=user_id)
    if state == '*':
        return list(Task.objects.filter(
            models.Q(assignee=filtered_user)
        ).order_by('-created_at'))
    elif state == 'my_tasks':
        return list(Task.objects.filter(
            models.Q(assignee=filtered_user),
            status__in=['in_progress', 'assigned', 'overdue']
        ).order_by('-created_at'))
    elif state == 'user_completed_tasks':
        return list(Task.objects.filter(
            models.Q(assignee=filtered_user),
            status='completed'
        ).order_by('-completed_at'))
    elif state == 'user_overdue_tasks':
        return list(Task.objects.filter(
            models.Q(assignee=filtered_user),
            status='overdue'
        ).order_by('deadline'))

@sync_to_async
def get_user_completed_tasks(user):
    return list(Task.objects.filter(
        assignee=user,
        status='completed'
    ).order_by('-completed_at'))


@sync_to_async
def get_user_overdue_tasks(user):
    now = timezone.now().astimezone(ZoneInfo("Europe/Moscow"))
    return list(Task.objects.filter(
        assignee=user,
        status__in=['in_progress', 'assigned', 'overdue'],
        deadline__lt=now
    ).order_by('deadline'))


@sync_to_async
def get_moscow_time():
    return timezone.now().astimezone(ZoneInfo("Europe/Moscow"))


@task_management_router.callback_query(F.data.in_(["my_tasks", "user_completed_tasks", "user_overdue_tasks"]))
async def handle_task_list_navigation(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    logger.info(f"User {user_id} accessing task list with type: {callback.data}")
    
    try:
        await state.update_data(last_view=callback.data)
        user, _ = await identify_user(user_id)
        
        @sync_to_async
        def get_tasks_by_type(task_type: str, is_admin: bool):
            if is_admin:
                if task_type == "my_tasks":
                    return list(Task.objects.filter(
                        status__in=['in_progress', 'assigned', 'overdue']
                    ).order_by('-created_at'))
                elif task_type == "user_completed_tasks":
                    return list(Task.objects.filter(
                        status='completed'
                    ).order_by('-completed_at'))
                else:  # user_overdue_tasks
                    return list(Task.objects.filter(
                        status='overdue'
                    ).order_by('deadline'))
            else:
                if task_type == "my_tasks":
                    return list(Task.objects.filter(
                        (Q(assignee=user) | Q(is_group_task=True)),
                        status__in=['in_progress', 'assigned', 'overdue']
                    ).order_by('-created_at'))
                elif task_type == "user_completed_tasks":
                    return list(Task.objects.filter(
                        (Q(assignee=user) | Q(is_group_task=True)),
                        status='completed'
                    ).order_by('-completed_at'))
                else:  # user_overdue_tasks
                    return list(Task.objects.filter(
                        (Q(assignee=user) | Q(is_group_task=True)),
                        status='overdue'
                    ).order_by('deadline'))
        
        tasks = await get_tasks_by_type(callback.data, user.is_admin)
        logger.info(f"Retrieved {len(tasks)} tasks for user {user_id}")
        
        if callback.data == "my_tasks":
            text = "📋 Все активные задачи:" if user.is_admin else "📋 Мои задачи:"
        elif callback.data == "user_completed_tasks":
            text = "✅ Все выполненные задачи:" if user.is_admin else "✅ Мои выполненные задачи:"
        else:  # user_overdue_tasks
            text = "⏰ Все просроченные задачи:" if user.is_admin else "⏰ Мои просроченные задачи:"
        
        
        keyboard = get_task_list_keyboard(tasks, state=callback.data)
        await callback.message.edit_text(text, reply_markup=keyboard)
        await callback.answer()
        logger.info(f"Successfully displayed task list for user {user_id}")
        
    except Exception as e:
        logger.error(f"Error in handle_task_list_navigation for user {user_id}: {str(e)}", exc_info=True)
        await callback.answer("Произошла ошибка при загрузке списка задач")


@sync_to_async
def get_text_with_details(task: Task):
    return (
        f"📝 Задача: {task.title}\n\n"
        f"📄 Описание: {task.description}\n"
        f"📅 Дедлайн: {task.deadline.strftime('%d.%m.%Y %H:%M')}\n"
        f"👤 Создал: {task.creator.first_name}\n"
        f"📊 Статус: {task.get_status_display()}\n"
    )


@sync_to_async
def get_assignee_text(task: Task):
    if task.assignee:
        return f"👤 Исполнитель: {task.assignee.first_name}\n"
    else:
        return ""

@sync_to_async
def get_task_comment(task: Task):
    if task.comments.count() > 0:
        return TaskComment.objects.filter(task=task).order_by('-created_at').first().text
    else:
        return ""

@sync_to_async
def get_task_assignee(task: Task):
    if task.assignee:
        return task.assignee.first_name
    else:
        return ""

@task_management_router.callback_query(F.data.startswith("view_task:"))
async def view_task_details(callback: CallbackQuery, state: FSMContext):
    task_id = int(callback.data.split(":")[1])
    user, _ = await identify_user(callback.from_user.id)

    task, completions_count = await get_task_with_completions(task_id)

    task_text = await get_text_with_details(task)

    if user.is_admin:
        if task.is_group_task and completions_count is not None:
            task_text += f"✅ Выполнили: {completions_count} человек\n"
        if task.status == 'completed':
            task_text += f"✅ Задание выполнено\n"

            comment = await get_task_comment(task)
            if comment:
                task_text += f"💬 Комментарий: {comment}\n"

    asignee = await get_assignee_text(task)
    if asignee:
        task_text += asignee

    keyboard = get_task_detail_keyboard(task.id, user.is_admin, task.status)
    await send_task_message(callback.message, task, task_text, keyboard)
    await callback.answer()


@task_management_router.callback_query(F.data.startswith("take_task:"))
async def take_task(callback: CallbackQuery, state: FSMContext):
    task_id = int(callback.data.split(":")[1])
    user, _ = await identify_user(callback.from_user.id)

    task = await assign_task_to_user(task_id, user)
    if task:
        await callback.answer("✅ Задача взята в работу!")
        # await view_task_details(callback, state)
    else:
        await callback.answer("❌ Задача уже взята в работу другим пользователем!")


class TaskStates(StatesGroup):
    waiting_for_comment = State()


@task_management_router.callback_query(F.data.startswith("submit_task:"))
async def submit_task(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    logger.info(f"User {user_id} attempting to submit task")
    
    try:
        task_id = int(callback.data.split(":")[1])
        await state.update_data(task_id=task_id)
        
        # Ask for comment
        keyboard = InlineKeyboardBuilder()
        keyboard.button(text="⏩ Пропустить", callback_data="skip_comment")
        await callback.message.edit_text(
            "💬 Пожалуйста, напишите комментарий к выполненному заданию\n"
            "или нажмите «Пропустить», если комментарий не требуется.",
            reply_markup=keyboard.as_markup()
        )
        await state.set_state(TaskStates.waiting_for_comment)
        await callback.answer()
        logger.info(f"Waiting for comment from user {user_id} for task {task_id}")
        
    except Exception as e:
        logger.error(f"Error in submit_task for user {user_id}: {str(e)}", exc_info=True)
        await callback.answer("❌ Произошла ошибка при выполнении задачи")


@task_management_router.message(TaskStates.waiting_for_comment)
async def handle_task_comment(message: Message, state: FSMContext):
    user_id = message.from_user.id
    logger.info(f"Received comment from user {user_id}")
    
    try:
        data = await state.get_data()
        task_id = data['task_id']
        user, _ = await identify_user(user_id)
        
        @sync_to_async
        def complete_task_with_comment(comment):
            task = Task.objects.get(id=task_id)
            task.mark_completed()
            TaskComment.objects.create(
                task=task,
                user=user,
                text=comment
            )
            return task
            
        @sync_to_async
        def get_admins():
            return list(TelegramUser.objects.filter(is_admin=True, notification_enabled=True))
        
        task = await complete_task_with_comment(message.text)
        admins = await get_admins()
        
        # Send notifications to admins
        notification_text = (
            f"✅ Задача выполнена!\n"
            f"Название: {task.title}\n"
            f"Исполнитель: {user.first_name}\n"
            f"Время выполнения: {task.completed_at.astimezone(ZoneInfo('Europe/Moscow')).strftime('%d.%m.%Y %H:%M')}\n"
            f"💬 Комментарий: {message.text}"
        )
        
        for admin in admins:
            try:
                await message.bot.send_message(admin.telegram_id, notification_text)
                logger.info(f"Sent completion notification to admin {admin.telegram_id}")
            except Exception as e:
                logger.error(f"Failed to send notification to admin {admin.telegram_id}: {e}")
        
        # Update task view
        task_text = await get_text_with_details(task)
        keyboard = get_task_detail_keyboard(task_id, user.is_admin, 'completed')
        await message.answer(
            f"✅ Задача отмечена как выполненная!\n{task_text}",
            reply_markup=keyboard
        )
        await state.clear()
        logger.info(f"Task {task_id} marked as completed with comment by user {user_id}")
        
    except Exception as e:
        logger.error(f"Error in handle_task_comment for user {user_id}: {str(e)}", exc_info=True)
        await message.answer("❌ Произошла ошибка при сохранении комментария")
        await state.clear()


@task_management_router.callback_query(F.data == "skip_comment")
async def skip_task_comment(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    logger.info(f"User {user_id} skipped comment")
    
    try:
        data = await state.get_data()
        task_id = data['task_id']
        user, _ = await identify_user(user_id)
        
        @sync_to_async
        def complete_task():
            task = Task.objects.get(id=task_id)
            task.mark_completed()
            return task
            
        @sync_to_async
        def get_admins():
            return list(TelegramUser.objects.filter(is_admin=True, notification_enabled=True))
        
        task = await complete_task()
        admins = await get_admins()
        
        # Send notifications to admins
        notification_text = (
            f"✅ Задача выполнена!\n"
            f"Название: {task.title}\n"
            f"Исполнитель: {user.first_name}\n"
            f"Время выполнения: {task.completed_at.astimezone(ZoneInfo('Europe/Moscow')).strftime('%d.%m.%Y %H:%M')}"
        )
        
        for admin in admins:
            try:
                await callback.bot.send_message(admin.telegram_id, notification_text)
                logger.info(f"Sent completion notification to admin {admin.telegram_id}")
            except Exception as e:
                logger.error(f"Failed to send notification to admin {admin.telegram_id}: {e}")
        
        # Update task view
        task_text = await get_text_with_details(task)
        keyboard = get_task_detail_keyboard(task_id, user.is_admin, 'completed')
        await callback.message.edit_text(
            f"✅ Задача отмечена как выполненная!\n{task_text}",
            reply_markup=keyboard
        )
        await state.clear()
        await callback.answer()
        logger.info(f"Task {task_id} marked as completed without comment by user {user_id}")
        
    except Exception as e:
        logger.error(f"Error in skip_task_comment for user {user_id}: {str(e)}", exc_info=True)
        await callback.answer("❌ Произошла ошибка при выполнении задачи")
        await state.clear()


@task_management_router.callback_query(F.data == "cancel_submission")
async def cancel_submission(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    data = await state.get_data()
    task_id = data.get('task_id')

    if task_id:
        await view_task_details(callback, state)
    else:
        await show_my_tasks(callback, state)


@task_management_router.callback_query(F.data == "back_to_task_list")
async def handle_back_to_task_list(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    user, _ = await identify_user(callback.from_user.id)

    if user.is_admin:
        tasks = await get_admin_task_list()
        text = "🗂 Все задачи:"
    else:
        tasks = await get_user_tasks(user)
        text = "📋 Мои задачи:"

    keyboard = get_task_list_keyboard(tasks)
    await safe_edit_message(callback.message, text, keyboard)
    await callback.answer()


@task_management_router.callback_query(F.data.in_(["open_tasks", "available_tasks"]))
async def show_open_tasks(callback: CallbackQuery, state: FSMContext):
    tasks = await get_open_tasks()
    keyboard = get_task_list_open_keyboard(tasks)
    try:
        await callback.message.edit_text("📥 Новые задачи:", reply_markup=keyboard)
    except Exception as e:
        await callback.message.answer("📥 Новые задачи:", reply_markup=keyboard)
    await callback.answer()


@task_management_router.callback_query(F.data.startswith("task_page:"))
async def handle_task_pagination(callback: CallbackQuery, state: FSMContext):
    page = int(callback.data.split(":")[1])
    state_ = callback.data.split(":")[2]
    data = await state.get_data()
    filtered_user_id = data.get('filtered_user_id')
    logging.info(f'FILTERED_USER_ID = {filtered_user_id}')

    user, _ = await identify_user(callback.from_user.id)

    if not user.is_admin:
        tasks = await get_user_tasks(user, state_)
        text = "📋 Мои задачи:"
    elif filtered_user_id:
        logger.info(f"Getting user filtered tasks for user {filtered_user_id} with state {state_}")
        tasks = await get_user_filtered_tasks(filtered_user_id, state_)
        filtered_user = await sync_to_async(TelegramUser.objects.get)(telegram_id=filtered_user_id)
        text = f"📋 Задачи пользователя {filtered_user.first_name}:"
    else:
        tasks = await get_admin_task_list(state=state_)
        text = "📋 Все задачи:"

    keyboard = get_task_list_keyboard(tasks, page=page, state=state_)
    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()


@task_management_router.callback_query(F.data == "filter_by_user")
async def show_user_filter(callback: CallbackQuery, state: FSMContext):
    user, _ = await identify_user(callback.from_user.id)

    if not user.is_admin:
        await callback.answer("У вас нет прав администратора!", show_alert=True)
        return

    @sync_to_async
    def get_active_users():
        return list(TelegramUser.objects.filter(
            is_active=True, 
            is_bot=False,
            is_admin=False
        ))

    users = await get_active_users()
    keyboard = get_user_filter_keyboard(users)
    await callback.message.edit_text("👥 Выберите пользователя для фильтрации:", reply_markup=keyboard)
    await callback.answer()


@task_management_router.callback_query(F.data.startswith("filter_tasks_user:"))
async def show_filtered_tasks(callback: CallbackQuery, state: FSMContext):
    user_id = int(callback.data.split(":")[1])
    page = 1
    await state.update_data(filtered_user_id=user_id, page=page)

    tasks = await get_user_filtered_tasks(user_id)
    filtered_user = await sync_to_async(TelegramUser.objects.get)(telegram_id=user_id)

    keyboard = get_task_list_keyboard(tasks, page=page)
    await callback.message.edit_text(
        f"📋 Задачи пользователя {filtered_user.first_name}:",
        reply_markup=keyboard
    )
    await callback.answer()


@task_management_router.callback_query(F.data == "clear_filter")
async def clear_task_filter(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    tasks = await get_admin_task_list()
    keyboard = get_task_list_keyboard(tasks)
    await callback.message.edit_text("📋 Все задачи:", reply_markup=keyboard)
    await callback.answer()


@task_management_router.callback_query(F.data.startswith("user_filter_page:"))
async def handle_user_filter_pagination(callback: CallbackQuery, state: FSMContext):
    page = int(callback.data.split(":")[1])

    @sync_to_async
    def get_active_users():
        return list(TelegramUser.objects.filter(
            is_active=True, 
            is_bot=False,
            is_admin=False
        ))

    users = await get_active_users()
    keyboard = get_user_filter_keyboard(users, page=page)
    await callback.message.edit_text("👥 Выберите пользователя для фильтрации:", reply_markup=keyboard)
    await callback.answer()


@task_management_router.callback_query(F.data == "completed_tasks")
async def show_completed_tasks(callback: CallbackQuery, state: FSMContext):
    user, _ = await identify_user(callback.from_user.id)

    if not user.is_admin:
        await callback.answer("У вас нет прав администратора!", show_alert=True)
        return

    tasks = await get_completed_tasks()
    keyboard = get_task_list_keyboard(tasks)
    await callback.message.edit_text("✅ Выполненные задачи:", reply_markup=keyboard)
    await callback.answer()


@task_management_router.callback_query(F.data == "overdue_tasks")
async def show_overdue_tasks(callback: CallbackQuery, state: FSMContext):
    user, _ = await identify_user(callback.from_user.id)

    if not user.is_admin:
        await callback.answer("У вас нет прав администратора!", show_alert=True)
        return

    tasks = await get_overdue_tasks()
    keyboard = get_task_list_keyboard(tasks)
    await callback.message.edit_text("⏰ Просроченные задачи:", reply_markup=keyboard)
    await callback.answer()


@task_management_router.callback_query(F.data == "user_completed_tasks")
async def show_user_completed_tasks(callback: CallbackQuery, state: FSMContext):
    user, _ = await identify_user(callback.from_user.id)
    tasks = await get_user_completed_tasks(user)
    keyboard = get_task_list_keyboard(tasks)
    await callback.message.edit_text("✅ Мои выполненные задачи:", reply_markup=keyboard)
    await callback.answer()


@task_management_router.callback_query(F.data == "user_overdue_tasks")
async def show_user_overdue_tasks(callback: CallbackQuery, state: FSMContext):
    user, _ = await identify_user(callback.from_user.id)
    tasks = await get_user_overdue_tasks(user)
    keyboard = get_task_list_keyboard(tasks)
    await callback.message.edit_text("⏰ Мои просроченные задачи:", reply_markup=keyboard)
    await callback.answer()


@task_management_router.callback_query(F.data == "my_tasks")
async def show_my_tasks(callback: CallbackQuery, state: FSMContext):
    user, _ = await identify_user(callback.from_user.id)
    tasks = await get_user_tasks(user)
    keyboard = get_task_list_keyboard(tasks)
    await callback.message.edit_text("📋 Мои задачи:", reply_markup=keyboard)
    await callback.answer()


@task_management_router.callback_query(F.data.startswith("delete_task:"))
async def handle_delete_task(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    logger.info(f"Admin {user_id} attempting to delete task")
    
    try:
        task_id = int(callback.data.split(":")[1])
        user, _ = await identify_user(user_id)
        
        if not user.is_admin:
            logger.warning(f"Unauthorized delete attempt by user {user_id}")
            await callback.answer("У вас нет прав администратора!", show_alert=True)
            return
            
        @sync_to_async
        def delete_task():
            task = Task.objects.get(id=task_id)
            task_title = task.title
            task.delete()
            return task_title
            
        task_title = await delete_task()
        logger.info(f"Task {task_id} ({task_title}) deleted by admin {user_id}")
        
        # Return to task list
        tasks = await get_admin_task_list()
        keyboard = get_task_list_keyboard(tasks)
        await callback.message.edit_text(
            f"✅ Задача «{task_title}» удалена\n\n"
            "📋 Все задачи:",
            reply_markup=keyboard
        )
        await callback.answer("Задача успешно удалена")
        
    except Exception as e:
        logger.error(f"Error in handle_delete_task for user {user_id}: {str(e)}", exc_info=True)
        await callback.answer("❌ Произошла ошибка при удалении задачи")

from robot.models import TaskAssignment
@sync_to_async
def mark_task_accepted(task_id, user):
    task = Task.objects.get(id=task_id)
    
    # For regular individual task
    if task.assignee == user and not task.is_group_task and not task.is_multi_task:
        # Create a TaskAssignment record if it doesn't exist
        assignment, created = TaskAssignment.objects.get_or_create(
            task=task,
            user=user,
            defaults={'accepted': True, 'accepted_at': timezone.now().astimezone(ZoneInfo("Europe/Moscow"))}
        )
        if not created and not assignment.accepted:
            assignment.mark_accepted()
        return task, True
    
    # For multi-task
    if task.is_multi_task:
        try:
            assignment = TaskAssignment.objects.get(task=task, user=user)
            if not assignment.accepted:
                assignment.mark_accepted()
                return task, True
            return task, False  # Already accepted
        except TaskAssignment.DoesNotExist:
            return task, False  # Not assigned to this user
    
    # For group task, create assignment if needed
    if task.is_group_task:
        assignment, created = TaskAssignment.objects.get_or_create(
            task=task,
            user=user,
            defaults={'accepted': True, 'accepted_at': timezone.now().astimezone(ZoneInfo("Europe/Moscow"))}
        )
        if not created and not assignment.accepted:
            assignment.mark_accepted()
        return task, True
    
    return None, False


@task_management_router.callback_query(F.data.startswith("accept_task:"))
async def accept_task(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    logger.info(f"User {user_id} accepting task")
    
    try:
        task_id = int(callback.data.split(":")[1])
        user, _ = await identify_user(user_id)
        
        task, accepted = await mark_task_accepted(task_id, user)
        
        if accepted and task:
            # Send notification to admin (task creator)
            @sync_to_async
            def get_creator(task: Task):
                return task.creator.telegram_id
            
            creator_id = await get_creator(task)
            admin_notification = (
                f"✅ Пользователь принял задание!\n\n"
                f"Задание: {task.title}\n"
                f"Исполнитель: {user.first_name}\n"
                f"Время принятия: {timezone.now().astimezone(ZoneInfo('Europe/Moscow')).strftime('%d.%m.%Y %H:%M')}"
            )
            
            try:
                await callback.bot.send_message(creator_id, admin_notification)
                logger.info(f"Sent acceptance notification to admin {creator_id}")
            except Exception as e:
                logger.error(f"Failed to send notification to admin {creator_id}: {e}")
            
            # Update UI for the user
            await callback.message.edit_text(
                f"✅ Вы приняли задание!\n\n"
                f"Задание: {task.title}\n"
                f"Срок выполнения: {task.deadline.strftime('%d.%m.%Y %H:%M')}"
            )
            await callback.answer("✅ Задание успешно принято!")
            logger.info(f"User {user_id} accepted task {task_id}")
        elif task:
            await callback.answer("Это задание уже принято вами ранее.")
            logger.info(f"User {user_id} attempted to accept already accepted task {task_id}")
        else:
            await callback.answer("❌ Произошла ошибка при принятии задания")
            logger.warning(f"Failed to accept task {task_id} for user {user_id}")
    
    except Exception as e:
        logger.error(f"Error in accept_task for user {user_id}: {str(e)}", exc_info=True)
        await callback.answer("❌ Произошла ошибка при принятии задания")
