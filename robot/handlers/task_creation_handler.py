from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from datetime import datetime
from ..keyboards.task_creation_keyboards import (
    get_assignment_type_keyboard,
    get_users_keyboard,
    get_media_keyboard,
    get_confirm_keyboard
)
from ..states.task_states import TaskCreation
from ..models import Task, TelegramUser
from ..utils import identify_user
from asgiref.sync import sync_to_async

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


@task_creation_router.message(TaskCreation.waiting_for_description)
async def process_description(message: Message, state: FSMContext):
    await state.update_data(description=message.text)
    await state.set_state(TaskCreation.waiting_for_deadline)
    await message.answer("📅 Введите дедлайн в формате ДД.ММ.ГГГГ ЧЧ:ММ\nНапример: 31.12.2024 15:00")


@task_creation_router.message(TaskCreation.waiting_for_deadline)
async def process_deadline(message: Message, state: FSMContext):
    try:
        deadline = datetime.strptime(message.text, "%d.%m.%Y %H:%M")
        await state.update_data(deadline=deadline)
        
        await state.set_state(TaskCreation.waiting_for_assignment_type)
        keyboard = get_assignment_type_keyboard()
        await message.answer("👥 Выберите тип назначения:", reply_markup=keyboard)
    except ValueError:
        await message.answer("❌ Неверный формат даты. Попробуйте еще раз в формате ДД.ММ.ГГГГ ЧЧ:ММ")


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
        await state.update_data(media_file_id=file_id, media_type='photo')
    elif message.video:
        file_id = message.video.file_id
        await state.update_data(media_file_id=file_id, media_type='video')
    else:
        await message.answer("❌ Пожалуйста, отправьте фото или видео, или нажмите 'Пропустить'")
        return

    await show_confirmation(message, state)


@task_creation_router.callback_query(F.data == "skip_media")
async def skip_media(callback: CallbackQuery, state: FSMContext):
    await state.update_data(media_file_id=None, media_type=None)
    await show_confirmation(callback.message, state)
    await callback.answer()


async def show_confirmation(message: Message, state: FSMContext):
    data = await state.get_data()
    
    task_type = "Групповая" if data.get('is_group_task') else "Индивидуальная"
    if not data.get('is_group_task'):
        if data.get('is_open_task'):
            task_type += " (Открытая для выполнения)"
        elif data.get('assignee_id'):
            assignee = await get_user_name(data['assignee_id'])
            task_type += f" (Исполнитель: {assignee})"
    
    confirmation_text = (
        "📋 Подтвердите создание задачи:\n\n"
        f"📝 Название: {data['title']}\n"
        f"📄 Описание: {data['description']}\n"
        f"📅 Дедлайн: {data['deadline'].strftime('%d.%m.%Y %H:%M')}\n"
        f"👥 Тип: {task_type}\n"
        f"📎 Медиафайл: {'Прикреплён' if data.get('media_file_id') else 'Отсутствует'}"
    )
    
    keyboard = get_confirm_keyboard()
    await state.set_state(TaskCreation.confirm_creation)
    await message.answer(confirmation_text, reply_markup=keyboard)


@sync_to_async
def get_user_name(telegram_id: int) -> str:
    try:
        user = TelegramUser.objects.get(telegram_id=telegram_id)
        return user.first_name
    except TelegramUser.DoesNotExist:
        return "Неизвестный пользователь"


@task_creation_router.callback_query(F.data == "confirm_task")
async def create_task(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    creator, _ = await identify_user(callback.from_user.id)
    
    @sync_to_async
    def save_task():
        assignee = None
        if not data.get('is_group_task') and data.get('assignee_id'):
            assignee = TelegramUser.objects.get(telegram_id=data['assignee_id'])
        
        task = Task.objects.create(
            title=data['title'],
            description=data['description'],
            creator=creator,
            assignee=assignee,
            is_group_task=data.get('is_group_task', False),
            deadline=data['deadline'],
            media_file_id=data.get('media_file_id'),
            status='open' if data.get('is_open_task') else 'assigned'
        )
        return task

    task = await save_task()
    
    # Формируем текст уведомления
    task_type = "групповая" if task.is_group_task else "индивидуальная"
    if not task.is_group_task and data.get('is_open_task'):
        task_type += " (открыта для выполнения)"
    
    notification_text = (
        f"✅ Задача '{task.title}' успешно создана!\n"
        f"Тип: {task_type}\n"
        f"Дедлайн: {task.deadline.strftime('%d.%m.%Y %H:%M')}"
    )
    
    await state.clear()
    await callback.message.edit_text(notification_text)
    await callback.answer()


@task_creation_router.callback_query(F.data == "cancel_creation")
async def cancel_creation(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("❌ Создание задачи отменено")
    await callback.answer() 