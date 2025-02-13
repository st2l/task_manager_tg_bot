from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from ..utils import identify_user
from ..keyboards.task_keyboards import get_task_management_keyboard
from ..keyboards.admin_keyboards import get_admin_settings_keyboard
from robot.handlers.start_handler import get_admin_keyboard, get_user_keyboard

navigation_router = Router()

@navigation_router.callback_query(F.data == "back_to_main")
async def handle_back_to_main(callback: CallbackQuery, state: FSMContext):
    # Сбрасываем состояние FSM
    await state.clear()
    
    # Получаем информацию о пользователе
    user, _ = await identify_user(callback.from_user.id)
    
    # Формируем текст и клавиатуру в зависимости от прав пользователя
    if user.is_admin:
        text = "🎛 Главное меню администратора:"
        keyboard = get_admin_keyboard()
    else:
        text = "📱 Главное меню:"
        keyboard = get_user_keyboard()
    
    # Обновляем сообщение
    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()

@navigation_router.callback_query(F.data == "back_to_tasks")
async def handle_back_to_tasks(callback: CallbackQuery, state: FSMContext):
    # Сбрасываем состояние FSM
    await state.clear()
    
    # Получаем информацию о пользователе
    user, _ = await identify_user(callback.from_user.id)
    
    if user.is_admin:
        keyboard = get_task_management_keyboard()
        text = "🗂 Управление задачами:"
    else:
        keyboard = get_user_keyboard()
        text = "📋 Мои задачи:"
    
    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer() 