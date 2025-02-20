from robot.models import TelegramUser
from asgiref.sync import sync_to_async


@sync_to_async
def identify_user(telegram_id, username = None) -> tuple[TelegramUser, bool]:
    try:
        return TelegramUser.objects.get(telegram_id=telegram_id), False
    except TelegramUser.DoesNotExist:
        if username:
            TelegramUser.objects.create(telegram_id=telegram_id, username=username)
        else:
            TelegramUser.objects.create(telegram_id=telegram_id)
        return TelegramUser.objects.get(telegram_id=telegram_id), True
