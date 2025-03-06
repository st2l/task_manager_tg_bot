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
from datetime import datetime

task_management_router = Router()


@sync_to_async
def get_user_tasks(user, state: str = '*'):
    if state == '*':
        return list(TaskAssignment.objects.filter(
            user=user,
            status__in=['in_progress', 'assigned', 'overdue']
        ).select_related('task').order_by('-task__created_at'))
    elif state == 'my_tasks':
        return list(TaskAssignment.objects.filter(
            user=user,
            status__in=['in_progress', 'assigned', 'overdue']
        ).select_related('task').order_by('-task__created_at'))
    elif state == 'user_completed_tasks':
        return list(TaskAssignment.objects.filter(
            user=user,
            status='completed'
        ).select_related('task').order_by('-completed_at'))
    elif state == 'user_overdue_tasks':
        return list(TaskAssignment.objects.filter(
            user=user,
            status='overdue'
        ).select_related('task').order_by('task__deadline'))
    elif state == 'user_submitted_tasks':
        return list(TaskAssignment.objects.filter(
            user=user,
            status='submitted'
        ).select_related('task').order_by('-task__created_at'))
    elif state == 'user_revision_tasks':
        return list(TaskAssignment.objects.filter(
            user=user,
            status='revision'
        ).select_related('task').order_by('-task__created_at'))


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
    elif state == 'submitted_tasks':
        return list(Task.objects.filter(status='submitted').order_by('-created_at'))
    elif state == 'revision_tasks':
        return list(Task.objects.filter(status='revision').order_by('-created_at'))

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

from robot.models import TaskAssignment
@sync_to_async
def get_user_filtered_tasks(user_id, state: str = '*'):
    logging.info(f"Getting user filtered tasks for user {user_id} with state {state}")
    filtered_user = TelegramUser.objects.get(telegram_id=user_id)
    if state == '*':
        assignments = TaskAssignment.objects.filter(user=filtered_user)
        tasks = [el.task for el in assignments]
        return tasks + list(Task.objects.filter(
            models.Q(assignee=filtered_user) | models.Q(assignments__user=filtered_user)
        ).order_by('-created_at'))
    elif state == 'my_tasks':
        assignments = TaskAssignment.objects.filter(user=filtered_user)
        tasks = [el.task for el in assignments]
        return tasks + list(Task.objects.filter(
            (models.Q(assignee=filtered_user) | models.Q(assignments__user=filtered_user)),
            status__in=['in_progress', 'assigned', 'overdue', 'multi']
        ).order_by('-created_at'))
    elif state == 'user_completed_tasks':
        return list(Task.objects.filter(
            models.Q(assignee=filtered_user) | models.Q(assignments__user=filtered_user),
            status='completed'
        ).order_by('-completed_at'))
    elif state == 'user_overdue_tasks':
        return list(Task.objects.filter(
            models.Q(assignee=filtered_user) | models.Q(assignments__user=filtered_user),
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
                    # assignments = TaskAssignment.objects.filter(user=user)
                    # tasks = [el.task for el in assignments]
                    # return tasks + list(Task.objects.filter(
                    #     (Q(assignee=user) | Q(is_group_task=True)),
                    #     status__in=['in_progress', 'assigned', 'overdue']
                    # ).order_by('-created_at'))
                    
                    return list(TaskAssignment.objects.filter(
                        (Q(user=user)),
                        status__in=['in_progress', 'assigned', 'overdue']
                    ))
                    
                elif task_type == "user_completed_tasks":
                    
                    return list(TaskAssignment.objects.filter(
                        (Q(user=user)),
                        status='completed'
                    ))
                    
                else:  # user_overdue_tasks
                    return list(Task.objects.filter(
                        (Q(assignee=user) | Q(is_group_task=True)),
                        status='overdue'
                    ).order_by('deadline'))
        
        tasks = await get_tasks_by_type(callback.data, user.is_admin)
        logger.info(f"Retrieved {len(tasks)} tasks for user {user_id}")
        
        if callback.data == "my_tasks":
            text = "📋 All active tasks:" if user.is_admin else "📋 My tasks:"
        elif callback.data == "user_completed_tasks":
            text = "✅ All completed tasks:" if user.is_admin else "✅ My completed tasks:"
        else:  # user_overdue_tasks
            text = "⏰ All overdue tasks:" if user.is_admin else "⏰ My overdue tasks:"
        
        
        keyboard = await get_task_list_keyboard(tasks, state=callback.data)
        try:
            await callback.message.edit_text(text, reply_markup=keyboard)
        except Exception as e:
            await callback.message.answer(text, reply_markup=keyboard)
        await callback.answer()
        logger.info(f"Successfully displayed task list for user {user_id}")
        
    except Exception as e:
        logger.error(f"Error in handle_task_list_navigation for user {user_id}: {str(e)}", exc_info=True)
        await callback.answer("Error occured in displaying task list")


@sync_to_async
def get_text_with_details(task: Task):
    return (
        f"📝 Task: {task.title}\n\n"
        f"📄 Description: {task.description}\n"
        f"📅 Deadline: {task.deadline.strftime('%m/%d/%Y %I:%M %p')}\n"
        f"👤 Created by: {task.creator.first_name}\n"
        f"📊 Status: {task.get_status_display()}\n"
    )


@sync_to_async
def get_assignee_text(task: Task):
    if task.assignee:
        return f"👤 Assignee: {task.assignee.first_name}\n"
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
            task_text += f"✅ Completed: {completions_count} members\n"
        if task.status == 'completed':
            task_text += f"✅ Task completed\n"

            comment = await get_task_comment(task)
            if comment:
                task_text += f"💬 Commentary: {comment}\n"

    asignee = await get_assignee_text(task)
    if asignee:
        task_text += asignee

    keyboard = await get_task_detail_keyboard(task.id, user.is_admin, task.status, user)
    await send_task_message(callback.message, task, task_text, keyboard)
    await callback.answer()


@task_management_router.callback_query(F.data.startswith("take_task:"))
async def take_task(callback: CallbackQuery, state: FSMContext):
    task_id = int(callback.data.split(":")[1])
    user, _ = await identify_user(callback.from_user.id)

    task = await assign_task_to_user(task_id, user)
    if task:
        await callback.answer("✅ Task taken to work!")
        # await view_task_details(callback, state)
    else:
        await callback.answer("❌ Task has been already taken!")


@sync_to_async
def mark_task_submitted(task_id, user, comment):
    assignment = TaskAssignment.objects.get(task_id=task_id, user=user)
    assignment.mark_submitted()
    TaskComment.objects.create(
        task_id=task_id,
        user=user,
        text=comment
    )
    return assignment.task


class TaskStates(StatesGroup):
    waiting_for_comment = State()
    waiting_for_review_decision = State()
    waiting_for_new_deadline = State()


@task_management_router.callback_query(F.data.startswith("submit_task:"))
async def submit_task(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    logger.info(f"User {user_id} attempting to submit task")
    
    try:
        task_id = int(callback.data.split(":")[1])
        await state.update_data(task_id=task_id)
        
        # Ask for mandatory comment
        keyboard = InlineKeyboardBuilder()
        keyboard.button(text="❌ Cancel", callback_data="cancel_submission")
        try:
            await callback.message.edit_text(
                "💬 Please add commentary to work.\n"
                "It is neccessary.",
                reply_markup=keyboard.as_markup()
            )
        except Exception as e:
            await callback.message.answer(
                "💬 Please add commentary to work.\n"
                "It is neccessary.",
                reply_markup=keyboard.as_markup()
            )
        await state.set_state(TaskStates.waiting_for_comment)
        await callback.answer()
        logger.info(f"Waiting for comment from user {user_id} for task {task_id}")
        
    except Exception as e:
        logger.error(f"Error in submit_task for user {user_id}: {str(e)}", exc_info=True)
        await callback.answer("❌ Error in completion task")


@task_management_router.message(TaskStates.waiting_for_comment)
async def handle_task_comment(message: Message, state: FSMContext):
    user_id = message.from_user.id
    logger.info(f"Received comment from user {user_id}")
    
    try:
        data = await state.get_data()
        task_id = data['task_id']
        user, _ = await identify_user(user_id)
        
        # Mark task as submitted, not completed
        task = await mark_task_submitted(task_id, user, message.text)
        
        # Get the task creator for notification
        @sync_to_async
        def get_task_creator(task_id):
            task = Task.objects.get(id=task_id)
            return task.creator
        
        creator = await get_task_creator(task_id)
        
        # Send notification to task creator
        notification_text = (
            f"📨 Task was sent for approve!\n\n"
            f"Name: {task.title}\n"
            f"Assignee: {user.first_name}\n"
            f"Time sent: {timezone.now().astimezone(ZoneInfo('Europe/Moscow')).strftime('%m/%d/%Y %I:%M %p')}\n"
            f"💬 Commentary: {message.text}\n\n"
        )
        
        try:
            # Send notification with review keyboard
            review_keyboard = InlineKeyboardBuilder()
            review_keyboard.button(text="✅ Review task", callback_data=f"review_task:{task_id}:{user_id}")
            await message.bot.send_message(
                creator.telegram_id,
                notification_text,
                reply_markup=review_keyboard.as_markup()
            )
            logger.info(f"Sent submission notification to task creator {creator.telegram_id}")
        except Exception as e:
            logger.error(f"Failed to send notification to task creator {creator.telegram_id}: {e}")
        
        # Update task view for the user
        task_text = await get_text_with_details(task)
        await message.answer(
            f"✅ Task send for approve!\n"
            f"You will get the notification about the status of task later.\n\n{task_text}"
        )
        await state.clear()
        logger.info(f"Task {task_id} marked as submitted with comment by user {user_id}")
        
    except Exception as e:
        logger.error(f"Error in handle_task_comment for user {user_id}: {str(e)}", exc_info=True)
        await message.answer("❌ Error occured")
        await state.clear()


# Add review handlers for admins
@task_management_router.callback_query(F.data.startswith("review_task:"))
async def review_task(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    logger.info(f"Admin {user_id} reviewing task")
    
    try:
        task_id = int(callback.data.split(":")[1])
        user, _ = await identify_user(user_id)
        
        if not user.is_admin:
            await callback.answer("You do not have access!", show_alert=True)
            return
        
        # Get task details
        @sync_to_async
        def get_task_details(task_id):
            task = Task.objects.get(id=task_id)
            comments = TaskComment.objects.filter(task=task).order_by('-created_at')
            latest_comment = comments.first() if comments.exists() else None
            assignee = task.assignee
            multi_assignees = []
            
            # For multi-task, get all assignees
            if task.is_multi_task:
                multi_assignees = [a.user for a in TaskAssignment.objects.filter(task=task)]
            
            return task, latest_comment, assignee, multi_assignees
        
        task, latest_comment, assignee, multi_assignees = await get_task_details(task_id)
        
        # Display task details to admin
        task_info = (
            f"📋 Task name: {task.title}\n\n"
            f"📄 Description: {task.description}\n"
            f"📅 Deadline: {task.deadline.strftime('%m/%d/%Y %I:%M %p')}\n"
            f"👤 Assignee: "
        )
        
        if task.is_multi_task and multi_assignees:
            assignees_names = [user.first_name for user in multi_assignees]
            task_info += f"{', '.join(assignees_names)}\n"
        elif assignee:
            task_info += f"{assignee.first_name}\n"
        else:
            task_info += "Not assigned\n"
        
        if latest_comment:
            task_info += f"\n💬 Commentary from user:\n{latest_comment.text}\n"
        
        # Create review keyboard
        review_keyboard = InlineKeyboardBuilder()
        review_keyboard.button(text="✅ Confirm competion", callback_data=f"accept_completion:{task_id}")
        review_keyboard.button(text="🔄 Send for a rework", callback_data=f"request_revision:{task_id}")
        review_keyboard.button(text="❌ Cancel", callback_data=f"cancel_review:{task_id}")
        review_keyboard.adjust(1)
        
        try:
            await callback.message.edit_text(task_info, reply_markup=review_keyboard.as_markup())
        except Exception as e:
            await callback.message.answer(task_info, reply_markup=review_keyboard.as_markup())
        await callback.answer()
        await state.update_data(task_id=task_id)
        
    except Exception as e:
        logger.error(f"Error in review_task for admin {user_id}: {str(e)}", exc_info=True)
        await callback.answer("❌ Error occured in reviewing task")


@task_management_router.callback_query(F.data.startswith("accept_completion:"))
async def accept_task_completion(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    logger.info(f"Admin {user_id} accepting task completion")
    
    try:
        task_id = int(callback.data.split(":")[1])
        admin, _ = await identify_user(user_id)
        
        if not admin.is_admin:
            await callback.answer("You do not have access!", show_alert=True)
            return
        
        @sync_to_async
        def complete_task_and_notify(task_id):
            task = Task.objects.get(id=task_id)
            task.mark_completed()
            
            assignees = []
            # Get assignee(s) to notify
            if task.is_multi_task:
                assignments = TaskAssignment.objects.filter(task=task)
                assignees = [a.user for a in assignments]
            elif task.assignee:
                assignees = [task.assignee]
            
            return task, assignees
        
        task, assignees = await complete_task_and_notify(task_id)
        
        # Notify all assignees
        for assignee in assignees:
            notification_text = (
                f"✅ Your task was check and confirmed!\n\n"
                f"Name: {task.title}\n"
                f"Time of confirmation: {task.completed_at.strftime('%m/%d/%Y %I:%M %p')}"
            )
            
            try:
                await callback.bot.send_message(assignee.telegram_id, notification_text)
                logger.info(f"Sent acceptance notification to assignee {assignee.telegram_id}")
            except Exception as e:
                logger.error(f"Failed to send notification to assignee {assignee.telegram_id}: {e}")
        
        # Update UI for the admin
        try:
            await callback.message.edit_text(
                f"✅ Task '{task.title}' was confirmed!\n"
                f"Assignees was notificated about that."
            )
        except Exception as e:
            await callback.message.answer(
                f"✅ Task '{task.title}' was confirmed!\n"
                f"Assignees was notificated about that."
            )
        await callback.answer("Task confirmed!")
        logger.info(f"Admin {user_id} accepted task {task_id}")
        
    except Exception as e:
        logger.error(f"Error in accept_task_completion for admin {user_id}: {str(e)}", exc_info=True)
        await callback.answer("❌ Error in confirmation of task")

from datetime import timedelta
@task_management_router.callback_query(F.data.startswith("request_revision:"))
async def request_task_revision(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    logger.info(f"Admin {user_id} requesting task revision")
    
    try:
        task_id = int(callback.data.split(":")[1])
        await state.update_data(task_id=task_id)
        
        # Ask for a new deadline
        keyboard = InlineKeyboardBuilder()
        
        # Add some quick date options (today + 1-7 days)
        now = datetime.now()
        for days in [1, 2, 3, 5, 7]:
            new_date = now + timedelta(days=days)
            date_str = new_date.strftime("%m/%d/%Y")
            keyboard.button(
                text=f"{date_str}", 
                callback_data=f"revision_date:{date_str}"
            )
        
        keyboard.button(text="❌ Cancel", callback_data=f"cancel_review:{task_id}")
        keyboard.adjust(3, 2, 1)
        
        try:
            await callback.message.edit_text(
                "📅 Choose new deadline date in format MM/DD/YYYY HH:MM",
                reply_markup=keyboard.as_markup()
            )
        except Exception as e:
            await callback.message.answer(
                "📅 Choose new deadline date in format MM/DD/YYYY HH:MM",
                reply_markup=keyboard.as_markup()
            )
        await state.set_state(TaskStates.waiting_for_new_deadline)
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Error in request_task_revision for admin {user_id}: {str(e)}", exc_info=True)
        await callback.answer("❌ Error occured in sending for review")


@task_management_router.callback_query(F.data.startswith("revision_date:"))
async def set_revision_date_from_button(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    logger.info(f"Admin {user_id} selected revision date from buttons")
    
    try:
        date_str = callback.data.split(":")[1]
        date_obj = datetime.strptime(date_str, "%m/%d/%Y")
        date_obj = date_obj.replace(hour=23, minute=59)
        
        # Now proceed with the comment request
        await state.update_data(new_deadline=date_obj)
        
        keyboard = InlineKeyboardBuilder()
        keyboard.button(text="❌ Cancel", callback_data=f"cancel_review:{(await state.get_data())['task_id']}")
        
        try:
            await callback.message.edit_text(
                "💬 Commentary for task (what exactly needs to be reworked):",
                reply_markup=keyboard.as_markup()
            )
        except Exception as e:
            await callback.message.answer(
                "💬 Commentary for task (what exactly needs to be reworked):",
                reply_markup=keyboard.as_markup()
            )
        await state.set_state(TaskStates.waiting_for_review_decision)
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Error in set_revision_date_from_button for admin {user_id}: {str(e)}", exc_info=True)
        await callback.answer("❌ Error occured")


@task_management_router.message(TaskStates.waiting_for_new_deadline)
async def set_revision_date_manual(message: Message, state: FSMContext):
    user_id = message.from_user.id
    logger.info(f"Admin {user_id} entered manual revision date")
    
    try:
        # Parse the date
        date_obj = datetime.strptime(message.text, "%m/%d/%Y")
        date_obj = date_obj.replace(hour=23, minute=59)
        
        # Update state and request comment
        await state.update_data(new_deadline=date_obj)
        
        keyboard = InlineKeyboardBuilder()
        keyboard.button(text="❌ Cancel", callback_data=f"cancel_review:{(await state.get_data())['task_id']}")
        
        await message.answer(
            "💬 Commentary for task (what exactly needs to be reworked):",
            reply_markup=keyboard.as_markup()
        )
        await state.set_state(TaskStates.waiting_for_review_decision)
        
    except ValueError:
        await message.answer(
            "❌ Incorrect data fomat. use -> MM/DD/YYYY",
        )
    except Exception as e:
        logger.error(f"Error in set_revision_date_manual for admin {user_id}: {str(e)}", exc_info=True)
        await message.answer("❌ Error occured")


@task_management_router.message(TaskStates.waiting_for_review_decision)
async def send_task_to_revision(message: Message, state: FSMContext):
    user_id = message.from_user.id
    logger.info(f"Admin {user_id} sending task to revision with comment")
    
    try:
        data = await state.get_data()
        task_id = data['task_id']
        new_deadline = data['new_deadline']
        admin, _ = await identify_user(user_id)
        
        @sync_to_async
        def update_task_for_revision(task_id, new_deadline, admin, comment):
            task = Task.objects.get(id=task_id)
            task.mark_revision(new_deadline)
            
            # Add admin comment
            TaskComment.objects.create(
                task=task,
                user=admin,
                text=f"Task send for rework. {comment}"
            )
            
            assignees = []
            # Get assignee(s) to notify
            if task.is_multi_task:
                assignments = TaskAssignment.objects.filter(task=task)
                assignees = [a.user for a in assignments]
            elif task.assignee:
                assignees = [task.assignee]
                
            return task, assignees
        
        task, assignees = await update_task_for_revision(task_id, new_deadline, admin, message.text)
        
        # Notify all assignees
        for assignee in assignees:
            notification_text = (
                f"🔄 Your task needs to be reworked!\n\n"
                f"Name: {task.title}\n"
                f"New deadline: {new_deadline.strftime('%m/%d/%Y %I:%M %p')}\n"
                f"💬 Commentary from checker: {message.text}"
            )
            
            try:
                await message.bot.send_message(assignee.telegram_id, notification_text)
                logger.info(f"Sent revision notification to assignee {assignee.telegram_id}")
            except Exception as e:
                logger.error(f"Failed to send notification to assignee {assignee.telegram_id}: {e}")
        
        # Update UI for the admin
        await message.answer(
            f"🔄 Task '{task.title}' send for rework!\n"
            f"New deadline: {new_deadline.strftime('%m/%d/%Y %I:%M %p')}\n"
            f"Assignees was notificated."
        )
        await state.clear()
        logger.info(f"Admin {user_id} sent task {task_id} to revision")
        
    except Exception as e:
        logger.error(f"Error in send_task_to_revision for admin {user_id}: {str(e)}", exc_info=True)
        await message.answer("❌ Error in sending task to revision")
        await state.clear()


@task_management_router.callback_query(F.data == "cancel_submission")
async def cancel_submission(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    data = await state.get_data()
    task_id = data.get('task_id')

    if (task_id):
        await view_task_details(callback, state)
    else:
        await show_my_tasks(callback, state)


@task_management_router.callback_query(F.data == "back_to_task_list")
async def handle_back_to_task_list(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    user, _ = await identify_user(callback.from_user.id)

    if user.is_admin:
        tasks = await get_admin_task_list()
        text = "🗂 All tasks:"
    else:
        tasks = await get_user_tasks(user)
        text = "📋 My tasks:"

    keyboard = await get_task_list_keyboard(tasks)
    await safe_edit_message(callback.message, text, keyboard)
    await callback.answer()


@task_management_router.callback_query(F.data.in_(["open_tasks", "available_tasks"]))
async def show_open_tasks(callback: CallbackQuery, state: FSMContext):
    tasks = await get_open_tasks()
    keyboard = get_task_list_open_keyboard(tasks)
    try:
        await callback.message.edit_text("📥 New tasks:", reply_markup=keyboard)
    except Exception as e:
        await callback.message.answer("📥 New tasks:", reply_markup=keyboard)
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
        text = "📋 My tasks:"
    elif filtered_user_id:
        logger.info(f"Getting user filtered tasks for user {filtered_user_id} with state {state_}")
        tasks = await get_user_filtered_tasks(filtered_user_id, state_)
        filtered_user = await sync_to_async(TelegramUser.objects.get)(telegram_id=filtered_user_id)
        text = f"📋 User's tasks {filtered_user.first_name}:"
    else:
        tasks = await get_admin_task_list(state=state_)
        text = "📋 All tasks:"

    keyboard = await get_task_list_keyboard(tasks, page=page, state=state_)
    try:
        await callback.message.edit_text(text, reply_markup=keyboard)
    except Exception as e:
        await callback.message.answer(text, reply_markup=keyboard)
    await callback.answer()


@task_management_router.callback_query(F.data == "filter_by_user")
async def show_user_filter(callback: CallbackQuery, state: FSMContext):
    user, _ = await identify_user(callback.from_user.id)

    if not user.is_admin:
        await callback.answer("You do not have access!", show_alert=True)
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
    try:
        await callback.message.edit_text("👥 Choose user for filtration:", reply_markup=keyboard)
    except Exception as e:
        await callback.message.answer("👥 Choose user for filtration:", reply_markup=keyboard)
    await callback.answer()


@task_management_router.callback_query(F.data.startswith("filter_tasks_user:"))
async def show_filtered_tasks(callback: CallbackQuery, state: FSMContext):
    user_id = int(callback.data.split(":")[1])
    page = 1
    await state.update_data(filtered_user_id=user_id, page=page)

    tasks = await get_user_filtered_tasks(user_id)
    filtered_user = await sync_to_async(TelegramUser.objects.get)(telegram_id=user_id)

    keyboard = await get_task_list_keyboard(tasks, page=page)
    try:
        await callback.message.edit_text(
            f"📋 User's tasks {filtered_user.first_name}:",
            reply_markup=keyboard
        )
    except Exception as e:
        await callback.message.answer(
            f"📋 User's tasks {filtered_user.first_name}:",
            reply_markup=keyboard
        )
    await callback.answer()


@task_management_router.callback_query(F.data == "clear_filter")
async def clear_task_filter(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    tasks = await get_admin_task_list()
    keyboard = await get_task_list_keyboard(tasks)
    try:
        await callback.message.edit_text("📋 All tasks:", reply_markup=keyboard)
    except Exception as e:
        await callback.message.answer("📋 All tasks:", reply_markup=keyboard)
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
    try:
        await callback.message.edit_text("👥 Choose user for filtration:", reply_markup=keyboard)
    except Exception as e:
        await callback.message.answer("👥 Choose user for filtration:", reply_markup=keyboard)
    await callback.answer()


@task_management_router.callback_query(F.data == "completed_tasks")
async def show_completed_tasks(callback: CallbackQuery, state: FSMContext):
    user, _ = await identify_user(callback.from_user.id)

    if not user.is_admin:
        await callback.answer("You do not have access!", show_alert=True)
        return

    tasks = await get_completed_tasks()
    keyboard = await get_task_list_keyboard(tasks)
    try:
        await callback.message.edit_text("✅ Completed tasks:", reply_markup=keyboard)
    except Exception as e:
        await callback.message.answer("✅ Completed tasks:", reply_markup=keyboard)
    await callback.answer()


@task_management_router.callback_query(F.data == "overdue_tasks")
async def show_overdue_tasks(callback: CallbackQuery, state: FSMContext):
    user, _ = await identify_user(callback.from_user.id)

    if not user.is_admin:
        await callback.answer("You do not have access!", show_alert=True)
        return

    tasks = await get_overdue_tasks()
    keyboard = await get_task_list_keyboard(tasks)
    try:
        await callback.message.edit_text("⏰ Overdue tasks:", reply_markup=keyboard)
    except Exception as e:
        await callback.message.answer("⏰ Overdue tasks:", reply_markup=keyboard)
    await callback.answer()


@task_management_router.callback_query(F.data == "user_completed_tasks")
async def show_user_completed_tasks(callback: CallbackQuery, state: FSMContext):
    user, _ = await identify_user(callback.from_user.id)
    tasks = await get_user_completed_tasks(user)
    keyboard = await get_task_list_keyboard(tasks)
    try:
        await callback.message.edit_text("✅ My completed tasks:", reply_markup=keyboard)
    except Exception as e:
        await callback.message.answer("✅ My completed tasks:", reply_markup=keyboard)
    await callback.answer()


@task_management_router.callback_query(F.data == "user_overdue_tasks")
async def show_user_overdue_tasks(callback: CallbackQuery, state: FSMContext):
    user, _ = await identify_user(callback.from_user.id)
    tasks = await get_user_overdue_tasks(user)
    keyboard = await get_task_list_keyboard(tasks)
    try:
        await callback.message.edit_text("⏰ My overdue tasks:", reply_markup=keyboard)
    except Exception as e:
        await callback.message.answer("⏰ My overdue tasks:", reply_markup=keyboard)
    await callback.answer()


@task_management_router.callback_query(F.data == "my_tasks")
async def show_my_tasks(callback: CallbackQuery, state: FSMContext):
    user, _ = await identify_user(callback.from_user.id)
    tasks = await get_user_tasks(user)
    keyboard = await get_task_list_keyboard(tasks)
    try:
        await callback.message.edit_text("📋 My tasks:", reply_markup=keyboard)
    except Exception as e:
        await callback.message.answer("📋 My tasks:", reply_markup=keyboard)
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
            await callback.answer("You do not have access!", show_alert=True)
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
        keyboard = await get_task_list_keyboard(tasks)
        try:
            await callback.message.edit_text(
                f"✅ Task «{task_title}» deleted\n\n"
                "📋 All tasks:",
                reply_markup=keyboard
            )
        except Exception as e:
            await callback.message.answer(
                f"✅ Task «{task_title}» deleted\n\n"
                "📋 All tasks:",
                reply_markup=keyboard
            )   
        await callback.answer("Task successfully deleted")
        
    except Exception as e:
        logger.error(f"Error in handle_delete_task for user {user_id}: {str(e)}", exc_info=True)
        await callback.answer("❌ Error in deleting task")

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
                f"✅ User confirm task!\n\n"
                f"Task: {task.title}\n"
                f"Assignee: {user.first_name}\n"
                f"Time of comfirmation: {timezone.now().astimezone(ZoneInfo('Europe/Moscow')).strftime('%m/%d/%Y %I:%M %p')}"
            )
            
            try:
                await callback.bot.send_message(creator_id, admin_notification)
                logger.info(f"Sent acceptance notification to admin {creator_id}")
            except Exception as e:
                logger.error(f"Failed to send notification to admin {creator_id}: {e}")
            
            # Update UI for the user
            try:
                await callback.message.edit_text(
                    f"✅ You confirmed task!\n\n"
                    f"Task: {task.title}\n"
                    f"Deadline: {task.deadline.strftime('%m/%d/%Y %I:%M %p')}"
                )
            except Exception as e:
                logger.warning(f"Failed to update UI for user {user_id}: {e}")
                await callback.message.answer(
                    f"✅ You confirmed task!\n\n"
                    f"Task: {task.title}\n"
                    f"Deadline: {task.deadline.strftime('%m/%d/%Y %I:%M %p')}"
                )
                
            await callback.answer("✅ Task successfully became in progress!")
            logger.info(f"User {user_id} accepted task {task_id}")
        elif task:
            await callback.answer("You have been confirmed this task.")
            logger.info(f"User {user_id} attempted to accept already accepted task {task_id}")
        else:
            await callback.answer("❌ Error occured in accepting task")
            logger.warning(f"Failed to accept task {task_id} for user {user_id}")
    
    except Exception as e:
        logger.error(f"Error in accept_task for user {user_id}: {str(e)}", exc_info=True)
        await callback.answer("❌ Error occured in accepting task")

@task_management_router.callback_query(F.data.startswith("cancel_review:"))
async def cancel_review(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    try:
        await callback.message.edit_text("❌ Check canceled")
    except Exception as e:
        await callback.message.answer("❌ Check canceled")
    await callback.answer()


@task_management_router.callback_query(F.data == "submitted_tasks")
async def show_submitted_tasks(callback: CallbackQuery, state: FSMContext):
    user, _ = await identify_user(callback.from_user.id)

    if user.is_admin:
        tasks = await get_admin_task_list("submitted_tasks")
        text = "📤 Tasks on check:"
    else:
        tasks = await get_user_tasks(user, "user_submitted_tasks")
        text = "📤 My tasks on check:"

    keyboard = await get_task_list_keyboard(tasks, state="submitted_tasks")
    try:
        await callback.message.edit_text(text, reply_markup=keyboard)
    except Exception as e:
        await callback.message.answer(text, reply_markup=keyboard)
    await callback.answer()


@task_management_router.callback_query(F.data == "revision_tasks")
async def show_revision_tasks(callback: CallbackQuery, state: FSMContext):
    user, _ = await identify_user(callback.from_user.id)

    if user.is_admin:
        tasks = await get_admin_task_list("revision_tasks")
        text = "🔄 Tasks on rework:"
    else:
        tasks = await get_user_tasks(user, "user_revision_tasks")
        text = "🔄 My tasks on rework:"

    keyboard = await get_task_list_keyboard(tasks, state="revision_tasks")
    try:
        await callback.message.edit_text(text, reply_markup=keyboard)
    except Exception as e:
        await callback.message.answer(text, reply_markup=keyboard)
    await callback.answer()
