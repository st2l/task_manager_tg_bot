from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram import Bot


def get_task_management_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="📝 Создать задачу", callback_data="create_task")
    builder.button(text="📋 Мои задачи", callback_data="my_tasks")
    builder.button(text="🔍 Все задачи", callback_data="all_tasks")
    builder.button(text="📊 Отчёты", callback_data="reports")
    builder.adjust(2)
    return builder.as_markup()


def get_task_action_keyboard(task_id: int, is_admin: bool = False) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Взять в работу",
                   callback_data=f"take_task:{task_id}")
    builder.button(text="✔️ Завершить",
                   callback_data=f"complete_task:{task_id}")
    builder.button(text="💬 Комментировать",
                   callback_data=f"comment_task:{task_id}")

    if is_admin:
        builder.button(text="❌ Удалить",
                       callback_data=f"delete_task:{task_id}")

    builder.button(text="◀️ Назад", callback_data="back_to_tasks")
    builder.adjust(2)
    return builder.as_markup()


def get_open_task_keyboard(task_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(
        text="✅ Взять в работу",
        callback_data=f"take_task:{task_id}"
    )
    builder.adjust(1)
    return builder.as_markup()


async def get_group_task_keyboard(bot: Bot) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(
        text="🤖 Перейти в бота",
        url=f"https://t.me/{(await bot.get_me()).username}"  # Замените на username вашего бота
    )
    builder.adjust(1)
    return builder.as_markup()


def get_personal_task_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(
        text="📋 Перейти ко всем заданиям",
        callback_data="my_tasks"
    )
    builder.adjust(1)
    return builder.as_markup()
