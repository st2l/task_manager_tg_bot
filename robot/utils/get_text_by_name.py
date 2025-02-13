from robot.models import BotText
from asgiref.sync import sync_to_async


@sync_to_async
def get_text_by_name(name, text=""):
    try:
        return BotText.objects.get(name=name).text
    except BotText.DoesNotExist:
        BotText.objects.create(name=name, text=text)
        return text
