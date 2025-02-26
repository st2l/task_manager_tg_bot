from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from datetime import datetime, timezone
import os
from ..keyboards.task_creation_keyboards import (
    get_assignment_type_keyboard,
    get_users_keyboard,
    get_multi_users_keyboard,
    get_media_keyboard,
    get_confirm_keyboard
)
from ..keyboards.task_keyboards import get_task_action_keyboard, get_open_task_keyboard, get_group_task_keyboard, get_personal_task_keyboard
from ..states.task_states import TaskCreation
from ..models import Task, TelegramUser, TaskAssignment
from ..utils import identify_user
from ..utils.message_utils import safe_edit_message
from asgiref.sync import sync_to_async
from zoneinfo import ZoneInfo
import logging
task_creation_router = Router()


@task_creation_router.callback_query(F.data == "create_task")
async def start_task_creation(callback: CallbackQuery, state: FSMContext):
    user, _ = await identify_user(callback.from_user.id)
    
    if not user.is_admin:
        await callback.answer("У вас нет прав для создания задач!", show_alert=True)
        return

    await state.set_state(TaskCreation.waiting_for_title)
    await callback.message.edit_text("📝 Введите название задачи:")
    await callback.answer()


@task_creation_router.message(TaskCreation.waiting_for_title)
async def process_title(message: Message, state: FSMContext):
    await state.update_data(title=message.text)
    await state.set_state(TaskCreation.waiting_for_description)
    await message.answer("📄 Введите описание задачи:")


from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from datetime import timedelta

def seven_days_kb():
    now = datetime.now()
    kb = InlineKeyboardBuilder()
    for i in range(1, 7+1):
        next_day = now + timedelta(days=i)
        logging.info(f'next_day -> {next_day}')
        kb.button(text=f'{next_day.day}.{next_day.month}.{next_day.year} 23:59',
                  callback_data=f'choose_time_{next_day.day}.{next_day.month}.{next_day.year} 23:59')
    kb.adjust(2)
    return kb.as_markup()
    

@task_creation_router.message(TaskCreation.waiting_for_description)
async def process_description(message: Message, state: FSMContext):
    await state.update_data(description=message.text)
    await state.set_state(TaskCreation.waiting_for_deadline)
    await message.answer(
        "📅 Введите дедлайн в формате ДД.ММ.ГГГГ ЧЧ:ММ\nНапример: 31.12.2024 15:00\n\nИли выберите из списка внизу.",
        reply_markup=seven_days_kb(),
        )

@task_creation_router.callback_query(F.data.startswith('choose_time_'))
async def process_deadline_time(callback: CallbackQuery, state: FSMContext):
    try:
        
        deadline = datetime.strptime(callback.data.split('_')[-1], "%d.%m.%Y %H:%M")
        await state.update_data(deadline=deadline)
        
        await state.set_state(TaskCreation.waiting_for_assignment_type)
        keyboard = get_assignment_type_keyboard()
        await callback.message.edit_text("👥 Выберите тип назначения:", reply_markup=keyboard)
        
    except Exception as e:
        await callback.answer(f'Error: {e}')

@task_creation_router.message(TaskCreation.waiting_for_deadline)
async def process_deadline(message: Message, state: FSMContext):
    try:
        deadline = datetime.strptime(message.text, "%d.%m.%Y %H:%M")
        await state.update_data(deadline=deadline)
        
        await state.set_state(TaskCreation.waiting_for_assignment_type)
        keyboard = get_assignment_type_keyboard()
        await message.answer("👥 Выберите тип назначения:", reply_markup=keyboard)
    except ValueError:
        await message.answer("❌ Неверный формат даты. Попробуйте еще раз в формате ДД.М.ГГГ ЧЧ:ММ")


@task_creation_router.callback_query(F.data == "individual_task")
async def process_individual_task(callback: CallbackQuery, state: FSMContext):
    await state.update_data(is_group_task=False)
    keyboard = await get_users_keyboard()
    await state.set_state(TaskCreation.waiting_for_assignee)
    await callback.message.edit_text("👤 Выберите исполнителя:", reply_markup=keyboard)
    await callback.answer()


@task_creation_router.callback_query(F.data == "group_task")
async def process_group_task(callback: CallbackQuery, state: FSMContext):
    await state.update_data(is_group_task=True)
    keyboard = get_media_keyboard()
    await state.set_state(TaskCreation.waiting_for_media)
    await callback.message.edit_text("📎 Прикрепите медиафайл (фото/видео) или пропустите этот шаг:", reply_markup=keyboard)
    await callback.answer()


@task_creation_router.callback_query(F.data == "multi_task")
async def process_multi_task(callback: CallbackQuery, state: FSMContext):
    await state.update_data(is_multi_task=True, is_group_task=False, selected_users=[])
    
    # Initialize the pagination state
    await state.update_data(page=0)
    
    # Get and set the multi-user selection keyboard
    keyboard = await get_multi_users_keyboard()
    await state.set_state(TaskCreation.selecting_assignees)
    await callback.message.edit_text("👥 Выберите исполнителей задачи:", reply_markup=keyboard)
    await callback.answer()


@task_creation_router.callback_query(F.data.startswith("multi_select:"))
async def handle_user_selection(callback: CallbackQuery, state: FSMContext):
    user_id = int(callback.data.split(":")[1])
    
    # Get current state data
    data = await state.get_data()
    selected_users = data.get('selected_users', [])
    current_page = data.get('page', 0)
    
    # Toggle user selection
    if user_id in selected_users:
        selected_users.remove(user_id)
    else:
        selected_users.append(user_id)
    
    # Update state with new selection
    await state.update_data(selected_users=selected_users)
    
    # Update the keyboard with new selection state
    keyboard = await get_multi_users_keyboard(selected_users, current_page)
    await callback.message.edit_text("👥 Выберите исполнителей задачи:", reply_markup=keyboard)
    await callback.answer()


@task_creation_router.callback_query(F.data.startswith("multi_page:"))
async def handle_pagination(callback: CallbackQuery, state: FSMContext):
    new_page = int(callback.data.split(":")[1])
    
    # Get current state data
    data = await state.get_data()
    selected_users = data.get('selected_users', [])
    
    # Update state with new page
    await state.update_data(page=new_page)
    
    # Update the keyboard with new page
    keyboard = await get_multi_users_keyboard(selected_users, new_page)
    await callback.message.edit_text("👥 Выберите исполнителей задачи:", reply_markup=keyboard)
    await callback.answer()


@task_creation_router.callback_query(F.data == "multi_confirm")
async def confirm_multi_selection(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    selected_users = data.get('selected_users', [])
    
    if not selected_users:
        await callback.answer("❌ Выберите хотя бы одного исполнителя!", show_alert=True)
        return
    
    keyboard = get_media_keyboard()
    await state.set_state(TaskCreation.waiting_for_media)
    await callback.message.edit_text("📎 Прикрепите медиафайл (фото/видео) или пропустите этот шаг:", reply_markup=keyboard)
    await callback.answer()


@task_creation_router.callback_query(F.data == "ignore")
async def ignore_callback(callback: CallbackQuery):
    await callback.answer()


@task_creation_router.callback_query(F.data.startswith("assign_user:"))
async def process_assignee(callback: CallbackQuery, state: FSMContext):
    user_id = int(callback.data.split(":")[1])
    await state.update_data(assignee_id=user_id, is_open_task=False)
    keyboard = get_media_keyboard()
    await state.set_state(TaskCreation.waiting_for_media)
    await callback.message.edit_text("📎 Прикрепите медиафайл (фото/видео) или пропустите этот шаг:", reply_markup=keyboard)
    await callback.answer()


@task_creation_router.callback_query(F.data == "leave_open")
async def process_open_task(callback: CallbackQuery, state: FSMContext):
    await state.update_data(assignee_id=None, is_open_task=True)
    keyboard = get_media_keyboard()
    await state.set_state(TaskCreation.waiting_for_media)
    await callback.message.edit_text("📎 Прикрепите медиафайл (фото/видео) или пропустите этот шаг:", reply_markup=keyboard)
    await callback.answer()


@task_creation_router.message(TaskCreation.waiting_for_media)
async def process_media(message: Message, state: FSMContext):
    if message.photo:
        file_id = message.photo[-1].file_id
        media_type = 'photo'
    elif message.video:
        file_id = message.video.file_id
        media_type = 'video'
    else:
        await message.answer("❌ Пожалуйста, отправьте фото или видео, либо пропустите этот шаг.")
        return
    
    await state.update_data(media_file_id=file_id, media_type=media_type)
    
    # Показываем превью задачи
    data = await state.get_data()
    preview_text = await get_task_preview(data)
    
    keyboard = get_confirm_keyboard()
    await message.answer(preview_text, reply_markup=keyboard)
    await state.set_state(TaskCreation.confirm_creation)


@task_creation_router.callback_query(F.data == "skip_media")
async def skip_media(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    preview_text = await get_task_preview(data)
    
    keyboard = get_confirm_keyboard()
    await safe_edit_message(callback.message, preview_text, keyboard)
    await state.set_state(TaskCreation.confirm_creation)
    await callback.answer()


async def show_confirmation(message: Message, state: FSMContext):
    data = await state.get_data()
    
    confirmation_text = (
        "📋 Подтвердите создание задачи:\n\n"
        f"📝 Название: {data['title']}\n"
        f"📄 Описание: {data['description']}\n"
        f"📅 Дедлайн: {data['deadline'].strftime('%d.%m.%Y %H:%M')}\n"
        f"👥 Тип: {'Групповая' if data.get('is_group_task') else 'Индивидуальная'}\n"
    )
    
    keyboard = get_confirm_keyboard()
    await state.set_state(TaskCreation.confirm_creation)
    await message.answer(confirmation_text, reply_markup=keyboard)


async def send_task_notification(bot: Bot, task: Task, data: dict):
    group_id = os.getenv("TELEGRAM_GROUP_ID")
    bot_username = os.getenv("TELEGRAM_BOT_USERNAME")
    
    # Формируем базовый текст задачи
    task_text = (
        f"📋 Новая задача: {task.title}\n\n"
        f"📝 Описание: {task.description}\n"
        f"📅 Дедлайн: {task.deadline.strftime('%d.%m.%Y %H:%M')}\n"
        f"👤 Создал: {task.creator.first_name}"
    )

    # For multi-task (multiple assignees)
    if task.is_multi_task:
        task_type = "👥 Задача для выбранных пользователей"
        
        # Get assignees from database
        @sync_to_async
        def get_task_assignments(task):
            return list(task.assignments.all())

        @sync_to_async
        def get_user_first_name(assignment):
            return assignment.user.username

        @sync_to_async
        def get_user_telegram_id(assignment):
            return assignment.user.telegram_id

        # Get assignments from database
        assignments = await get_task_assignments(task)
        assignees_names = []
        for assignment in assignments:
            name = await get_user_first_name(assignment)
            assignees_names.append(name)
        assignees_names = [assignment.user.first_name for assignment in assignments]
        assignees_text = ", ".join(assignees_names)
        
        group_text = f"{task_type}\n\n{task_text}\n\nИсполнители: {assignees_text}"
        
        # Send to group chat
        if task.media_file_id:
            if task.media_type == 'photo':
                await bot.send_photo(group_id, task.media_file_id, caption=group_text)
            else:
                await bot.send_video(group_id, task.media_file_id, caption=group_text)
        else:
            await bot.send_message(group_id, group_text)
        
        # Send to individual assignees
        personal_text = (
            f"👤 Вам назначена новая задача!\n\n{task_text}\n\n"
            "Пожалуйста, ознакомьтесь и примите задание к выполнению."
        )
        
        for assignment in assignments:
            user_id = assignment.user.telegram_id
            keyboard = get_personal_task_keyboard(task.id)
            if task.media_file_id:
                if task.media_type == 'photo':
                    await bot.send_photo(user_id, task.media_file_id, caption=personal_text, reply_markup=keyboard)
                else:
                    await bot.send_video(user_id, task.media_file_id, caption=personal_text, reply_markup=keyboard)
            else:
                await bot.send_message(user_id, personal_text, reply_markup=keyboard)
    
    # Для открытой задачи
    elif data.get('is_open_task'):
        task_type = "🔓 Открытая задача"
        group_text = f"{task_type}\n\n{task_text}"
        keyboard = get_open_task_keyboard(task.id)
        if task.media_file_id:
            if task.media_type == 'photo':
                message = await bot.send_photo(group_id, task.media_file_id, caption=group_text, reply_markup=keyboard)
            else:
                message = await bot.send_video(group_id, task.media_file_id, caption=group_text, reply_markup=keyboard)
        else:
            message = await bot.send_message(group_id, group_text, reply_markup=keyboard)
    
    # Для групповой задачи
    elif task.is_group_task:
        task_type = "👥 Групповая задача"
        group_text = f"{task_type}\n\n{task_text}"
        keyboard = await get_group_task_keyboard(bot)
        if task.media_file_id:
            if task.media_type == 'photo':
                message = await bot.send_photo(group_id, task.media_file_id, caption=group_text, reply_markup=keyboard)
            else:
                message = await bot.send_video(group_id, task.media_file_id, caption=group_text, reply_markup=keyboard)
        else:
            message = await bot.send_message(group_id, group_text, reply_markup=keyboard)
    
    # Для индивидуальной задачи с назначенным исполнителем
    elif task.assignee:
        personal_text = (
            f"👤 Вам назначена новая задача!\n\n{task_text}\n\n"
            "Пожалуйста, ознакомьтесь и примите задание к выполнению."
        )
        keyboard = get_personal_task_keyboard(task.id)
        if task.media_file_id:
            if task.media_type == 'photo':
                message = await bot.send_photo(task.assignee.telegram_id, task.media_file_id, caption=personal_text, reply_markup=keyboard)
            else:
                message = await bot.send_video(task.assignee.telegram_id, task.media_file_id, caption=personal_text, reply_markup=keyboard)
        else:
            message = await bot.send_message(task.assignee.telegram_id, personal_text, reply_markup=keyboard)


@sync_to_async
def create_new_task(data, creator):
    logging.info(f"Creating new task with data: {data}")
    
    # Handle regular assignee for individual tasks
    if not data.get('is_group_task') and not data.get('is_multi_task'):
        try:
            assignee = TelegramUser.objects.get(telegram_id=data['assignee_id']) if 'assignee_id' in data else None
        except Exception as e:
            assignee = None
    else:
        assignee = None
    
    task_status = 'open'
    if not data.get('is_group_task') and not data.get('is_open_task'):
        task_status = 'assigned'
    
    # Create the task
    task = Task.objects.create(
        title=data['title'],
        description=data['description'],
        creator=creator,
        deadline=data['deadline'],
        is_group_task=data.get('is_group_task', False),
        is_multi_task=data.get('is_multi_task', False),
        assignee=assignee,
        media_file_id=data.get('media_file_id', None),
        media_type=data.get('media_type', None),
        status=task_status,
    )
    
    # Handle multiple assignees for multi-tasks
    if data.get('is_multi_task') and 'selected_users' in data:
        for user_id in data['selected_users']:
            try:
                user = TelegramUser.objects.get(telegram_id=user_id)
                TaskAssignment.objects.create(task=task, user=user)
            except Exception as e:
                logging.error(f"Error creating task assignment: {e}")
    
    return task


@sync_to_async
def get_task_preview(data):
    preview_text = (
        f"📝 Название: {data['title']}\n"
        f"📄 Описание: {data['description']}\n"
        f"📅 Дедлайн: {data['deadline'].strftime('%d.%m.%Y %H:%M')}\n"
    )
    
    if data.get('is_group_task'):
        preview_text += "👥 Тип: Групповая (для всех участников группы)"
    elif data.get('is_multi_task'):
        preview_text += "👥 Тип: Мультизадача (для выбранных пользователей)"
        
        # Add selected users info
        if 'selected_users' in data and data['selected_users']:
            selected_users = []
            for user_id in data['selected_users']:
                try:
                    user = TelegramUser.objects.get(telegram_id=user_id)
                    selected_users.append(user.first_name)
                except Exception:
                    pass
            
            if selected_users:
                preview_text += f"\n👤 Исполнители: {', '.join(selected_users)}"
    else:
        preview_text += "👤 Тип: Индивидуальная"
        if data.get('is_open_task'):
            preview_text += "\n🔓 Открытая для выполнения"
        elif data.get('assignee_id'):
            assignee = TelegramUser.objects.get(telegram_id=data['assignee_id'])
            preview_text += f"\n👤 Исполнитель: {assignee.first_name}"
    
    if data.get('media_file_id'):
        media_type = "📷 Фото" if data.get('media_type') == 'photo' else "🎥 Видео"
        preview_text += f"\n{media_type}: Прикреплено"
    
    return preview_text


@task_creation_router.callback_query(F.data == "confirm_task")
async def create_task(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    creator, _ = await identify_user(callback.from_user.id)
    
    task = await create_new_task(data, creator)
    
    # Отправляем уведомления
    bot = callback.bot
    await send_task_notification(bot, task, data)
    
    # Формируем текст подтверждения для создателя
    task_type = "групповая" if task.is_group_task else "индивидуальная"
    if not task.is_group_task and data.get('is_open_task'):
        task_type += " (открыта для выполнения)"
    
    confirmation_text = (
        f"✅ Задача '{task.title}' успешно создана!\n"
        f"Тип: {task_type}\n"
        f"Дедлайн: {task.deadline.strftime('%d.%m.%Y %H:%M')}"
    )
    
    await state.clear()
    await safe_edit_message(callback.message, confirmation_text)
    await callback.answer()


@task_creation_router.callback_query(F.data == "cancel_creation")
async def cancel_creation(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("❌ Создание задачи отменено")
    await callback.answer()