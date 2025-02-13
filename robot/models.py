from django.db import models


class TelegramUser(models.Model):
    telegram_id = models.BigIntegerField(unique=True)
    first_name = models.CharField(max_length=255)
    is_bot = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)
    last_login = models.DateTimeField(auto_now=True)
    date_joined = models.DateTimeField(auto_now_add=True)

    def identify_user(self, telegram_id) -> tuple["TelegramUser", bool]:
        try:
            return self.objects.get(telegram_id=telegram_id), False
        except self.DoesNotExist:
            self.objects.create(telegram_id=telegram_id)
            return self.objects.get(telegram_id=telegram_id), True

    def __str__(self):
        return self.first_name


class BotText(models.Model):
    name = models.CharField(max_length=255)
    text = models.TextField()

    def get_text_by_name(self, name, text=""):
        try:
            return self.objects.get(name=name).text
        except self.DoesNotExist:
            self.objects.create(name=name, text=text)
            return text

    def __str__(self):
        return self.name
