from django.db import models
from django.utils import timezone
from zoneinfo import ZoneInfo


class TelegramUser(models.Model):
    telegram_id = models.BigIntegerField(unique=True)
    first_name = models.CharField(max_length=255)
    username = models.CharField(max_length=255, blank=True, null=True)
    is_bot = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    is_admin = models.BooleanField(default=False)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)
    last_login = models.DateTimeField(auto_now=True)
    date_joined = models.DateTimeField(auto_now_add=True)
    notification_enabled = models.BooleanField(default=True)

    def identify_user(self, telegram_id) -> tuple["TelegramUser", bool]:
        try:
            return self.objects.get(telegram_id=telegram_id), False
        except self.DoesNotExist:
            self.objects.create(telegram_id=telegram_id)
            return self.objects.get(telegram_id=telegram_id), True

    def __str__(self):
        if self.username:
            return f"{self.first_name} (@{self.username})"
        return f"{self.first_name}"


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


class Task(models.Model):
    STATUS_CHOICES = [
        ('open', 'Open'),  # Открытая задача, доступная для взятия
        ('assigned', 'Assigned'),  # Назначена конкретному исполнителю
        ('in_progress', 'In Progress'),
        ('submitted', 'Submitted'),  # Сдана на проверку
        ('completed', 'Completed'),
        ('overdue', 'Overdue'),
        ('revision', 'Revision'),  # Отправлена на доработку
    ]

    title = models.CharField(max_length=255)
    description = models.TextField()
    creator = models.ForeignKey(TelegramUser, on_delete=models.CASCADE, related_name='created_tasks')
    assignee = models.ForeignKey(TelegramUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_tasks')
    assignees = models.ManyToManyField(TelegramUser, through='TaskAssignment', related_name='multi_assigned_tasks')
    is_group_task = models.BooleanField(default=False)
    is_multi_task = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    deadline = models.DateTimeField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')
    completed_at = models.DateTimeField(null=True, blank=True)
    media_file_id = models.CharField(max_length=255, blank=True, null=True)
    media_type = models.CharField(max_length=10, choices=[
        ('photo', 'Photo'),
        ('video', 'Video')
    ], null=True, blank=True)
    
    def __str__(self):
        return self.title
    
    def mark_submitted(self):
        self.status = 'submitted'
        self.save()
        
    def mark_completed(self):
        self.status = 'completed'
        self.completed_at = timezone.now().astimezone(ZoneInfo("Europe/Moscow"))
        self.save()
        
    def mark_revision(self, new_deadline=None):
        self.status = 'revision'
        if new_deadline:
            self.deadline = new_deadline
        self.save()

    @property
    def is_overdue(self):
        if self.status in ['completed', 'overdue']:
            return False
        return self.deadline < timezone.now().astimezone(ZoneInfo("Europe/Moscow"))


class TaskAssignment(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='assignments')
    user = models.ForeignKey(TelegramUser, on_delete=models.CASCADE)
    assigned_at = models.DateTimeField(auto_now_add=True)
    accepted = models.BooleanField(default=False)
    accepted_at = models.DateTimeField(null=True, blank=True)
    completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        unique_together = ['task', 'user']
    
    def mark_accepted(self):
        self.accepted = True
        self.accepted_at = timezone.now().astimezone(ZoneInfo("Europe/Moscow"))
        self.save()
    
    def mark_completed(self):
        self.completed = True
        self.completed_at = timezone.now().astimezone(ZoneInfo("Europe/Moscow"))
        self.save()
    
    def __str__(self):
        return f"{self.user.first_name} - {self.task.title}"


class TaskComment(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='comments')
    user = models.ForeignKey(TelegramUser, on_delete=models.CASCADE)
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Comment on {self.task.title} by {self.user.first_name}"


class Reminder(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='reminders')
    reminder_time = models.DateTimeField()
    is_sent = models.BooleanField(default=False)
    
    def __str__(self):
        return f"Reminder for {self.task.title} at {self.reminder_time}"


class TaskCompletion(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='completions')
    user = models.ForeignKey(TelegramUser, on_delete=models.CASCADE)
    completed_at = models.DateTimeField(auto_now_add=True)
    comment = models.TextField(blank=True, null=True)
    
    class Meta:
        unique_together = ['task', 'user']
