from django.contrib import admin
from .models import TelegramUser, Task, TaskComment, Reminder

# Register your models here.


@admin.register(TelegramUser)
class TelegramUserAdmin(admin.ModelAdmin):
    list_display = ('telegram_id', 'first_name', 'username', 'is_admin', 'is_active')
    list_filter = ('is_active', 'is_admin')
    search_fields = ('telegram_id', 'first_name', 'username')


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ('title', 'creator', 'assignee', 'deadline', 'status')
    list_filter = ('status', 'is_group_task')
    search_fields = ('title', 'description')
    date_hierarchy = 'created_at'


@admin.register(TaskComment)
class TaskCommentAdmin(admin.ModelAdmin):
    list_display = ('task', 'user', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('text',)


@admin.register(Reminder)
class ReminderAdmin(admin.ModelAdmin):
    list_display = ('task', 'reminder_time', 'is_sent')
    list_filter = ('is_sent',)
