from aiogram.exceptions import TelegramBadRequest
from aiogram.types import Message, CallbackQuery

async def safe_edit_message(message: Message, text: str, reply_markup=None):
    try:
        await message.edit_text(text, reply_markup=reply_markup)
    except TelegramBadRequest as e:
        await message.answer(text, reply_markup=reply_markup)

async def send_task_message(message: Message, task, text: str, reply_markup=None):
    if task.media_file_id:
        try:
            if task.media_type == 'photo':
                await message.answer_photo(task.media_file_id, caption=text, reply_markup=reply_markup)
            elif task.media_type == 'video':
                await message.answer_video(task.media_file_id, caption=text, reply_markup=reply_markup)
            elif task.media_type == 'document':  # Add document sending
                await message.answer_document(task.media_file_id, caption=text, reply_markup=reply_markup)
            return
        except Exception as e:
            logger.error(f"Error sending media: {e}")
    
    await safe_edit_message(message, text, reply_markup)