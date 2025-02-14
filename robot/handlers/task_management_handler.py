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
from ..utils.message_utils import safe_edit_message, send_task_message
from ..utils.logger import logger
import logging

task_management_router = Router()


@sync_to_async
def get_user_tasks(user):
    return list(Task.objects.filter(
        (models.Q(assignee=user) & ~models.Q(status__in=['open', 'completed'])) |
        (models.Q(is_group_task=True) & models.Q(status='in_progress'))
    ))


@sync_to_async
def get_open_tasks():
    return list(Task.objects.filter(status='open'))


@sync_to_async
def get_admin_task_list():
    return list(Task.objects.all().order_by('-created_at'))


@sync_to_async
def get_completed_tasks():
    return list(Task.objects.filter(status='completed').order_by('-completed_at'))


@sync_to_async
def get_overdue_tasks():
    now = timezone.now()
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
    task.completed_at = timezone.now()
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
def get_user_filtered_tasks(user_id):
    filtered_user = TelegramUser.objects.get(telegram_id=user_id)
    return list(Task.objects.filter(
        models.Q(assignee=filtered_user)
    ).order_by('-created_at'))


@sync_to_async
def get_user_completed_tasks(user):
    return list(Task.objects.filter(
        assignee=user,
        status='completed'
    ).order_by('-completed_at'))


@sync_to_async
def get_user_overdue_tasks(user):
    now = timezone.now()
    return list(Task.objects.filter(
        assignee=user,
        status__in=['in_progress', 'assigned', 'overdue'],
        deadline__lt=now
    ).order_by('deadline'))


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
                        assignee=user,
                        status__in=['in_progress', 'assigned', 'overdue']
                    ).order_by('-created_at'))
                elif task_type == "user_completed_tasks":
                    return list(Task.objects.filter(
                        assignee=user,
                        status='completed'
                    ).order_by('-completed_at'))
                else:  # user_overdue_tasks
                    return list(Task.objects.filter(
                        assignee=user,
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
        
        keyboard = get_task_list_keyboard(tasks)
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


@task_management_router.callback_query(F.data.startswith("submit_task:"))
async def start_task_submission(callback: CallbackQuery, state: FSMContext):
    task_id = int(callback.data.split(":")[1])
    await state.update_data(task_id=task_id)
    await state.set_state(TaskSubmission.waiting_for_comment)

    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="⏩ Пропустить", callback_data="skip_comment")
    keyboard.button(text="❌ Отмена", callback_data="cancel_submission")

    await callback.message.edit_text(
        "💬 Хотите добавить комментарий к выполненному заданию?\n"
        "Напишите комментарий или нажмите «Пропустить»",
        reply_markup=keyboard.as_markup()
    )
    await callback.answer()

@sync_to_async
def create_task_comment(task_id, user, comment):
    task = Task.objects.get(id=task_id)
    TaskComment.objects.create(task=task, user=user, text=comment)
    return task

@task_management_router.message(TaskSubmission.waiting_for_comment)
async def process_submission_comment(message: Message, state: FSMContext):
    data = await state.get_data()
    task_id = data['task_id']
    user, _ = await identify_user(message.from_user.id)

    task, _ = await get_task_with_completions(task_id)
    if task.is_group_task:
        task = await create_task_completion(task_id, user, message.text)
    else:
        task = await complete_individual_task(task_id)

    await create_task_comment(task_id, user, message.text)

    await message.answer("✅ Задание успешно сдано!")
    await state.clear()


@task_management_router.callback_query(F.data == "skip_comment")
async def skip_submission_comment(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    task_id = data['task_id']
    user, _ = await identify_user(callback.from_user.id)

    task, _ = await get_task_with_completions(task_id)
    if task.is_group_task:
        task = await create_task_completion(task_id, user)
    else:
        task = await complete_individual_task(task_id)

    await callback.message.edit_text("✅ Задание успешно сдано!")
    await state.clear()
    await callback.answer()


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
    data = await state.get_data()
    filtered_user_id = data.get('filtered_user_id')

    if filtered_user_id:
        tasks = await get_user_filtered_tasks(filtered_user_id)
        filtered_user = await sync_to_async(TelegramUser.objects.get)(telegram_id=filtered_user_id)
        text = f"📋 Задачи пользователя {filtered_user.first_name}:"
    else:
        tasks = await get_admin_task_list()
        text = "📋 Все задачи:"

    keyboard = get_task_list_keyboard(tasks, page=page)
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
