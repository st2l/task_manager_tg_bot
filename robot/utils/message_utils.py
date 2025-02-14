from aiogram.exceptions import TelegramBadRequest
from aiogram.types import Message, CallbackQuery

async def safe_edit_message(message: Message, text: str, reply_markup=None):
    try:
        await message.edit_text(text, reply_markup=reply_markup)
    except TelegramBadRequest as e:
        if "message is not modified" in str(e):
            await message.answer(text, reply_markup=reply_markup)
        else:
            raise e

async def send_task_message(message: Message, task, text: str, reply_markup=None):
    # Сначала отправляем медиафайл, если есть
    if task.media_file_id:
        try:
            if task.media_type == 'photo':
                await message.answer_photo(task.media_file_id)
            else:
                await message.answer_video(task.media_file_id)
            await message.answer(text, reply_markup=reply_markup)
            return
        except Exception as e:
            print(f"Error sending media: {e}")
    
    # Затем отправляем текст задания
    await safe_edit_message(message, text, reply_markup) 