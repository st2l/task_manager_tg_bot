from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram import Bot


def get_task_management_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="📝 Create Task", callback_data="create_task")
    builder.button(text="📋 My Tasks", callback_data="my_tasks")
    builder.button(text="🔍 All Tasks", callback_data="all_tasks")
    builder.button(text="📊 Reports", callback_data="reports")
    builder.adjust(2)
    return builder.as_markup()


def get_task_action_keyboard(task_id: int, is_admin: bool = False) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Take Task",
                   callback_data=f"take_task:{task_id}")
    builder.button(text="✔️ Complete",
                   callback_data=f"complete_task:{task_id}")
    builder.button(text="💬 Comment",
                   callback_data=f"comment_task:{task_id}")

    if is_admin:
        builder.button(text="❌ Delete",
                       callback_data=f"delete_task:{task_id}")

    builder.button(text="◀️ Back", callback_data="back_to_tasks")
    builder.adjust(2)
    return builder.as_markup()


def get_open_task_keyboard(task_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(
        text="✅ Take Task",
        callback_data=f"take_task:{task_id}"
    )
    builder.adjust(1)
    return builder.as_markup()


async def get_group_task_keyboard(bot: Bot) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(
        text="🤖 Go to Bot",
        url=f"https://t.me/{(await bot.get_me()).username}"  # Replace with your bot's username
    )
    builder.adjust(1)
    return builder.as_markup()


def get_personal_task_keyboard(task_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(
        text="✅ Accept Task",
        callback_data=f"accept_task:{task_id}"
    )
    builder.button(
        text="📋 Go to All Tasks",
        callback_data="my_tasks"
    )
    builder.adjust(1)
    return builder.as_markup()