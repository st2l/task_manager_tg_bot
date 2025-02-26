from django.contrib import admin
from .models import TelegramUser, Task, TaskComment, Reminder, TaskAssignment, TaskCompletion, BotText

# Register your models here.


@admin.register(TelegramUser)
class TelegramUserAdmin(admin.ModelAdmin):
    list_display = ('username', 'first_name', 'telegram_id', 'is_admin', 'is_active')
    list_filter = ('is_active', 'is_admin')
    search_fields = ('telegram_id', 'first_name', 'username')
    ordering = ('username',)  # Добавьте эту строку для сортировки по умолчанию


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ('title', 'creator', 'assignee', 'deadline', 'status', 'is_group_task', 'is_multi_task')
    list_filter = ('status', 'is_group_task', 'is_multi_task')
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


@admin.register(TaskAssignment)
class TaskAssignmentAdmin(admin.ModelAdmin):
    list_display = ('task', 'user', 'assigned_at', 'completed', 'completed_at')
    list_filter = ('completed', 'assigned_at')
    search_fields = ('task__title', 'user__first_name')
    date_hierarchy = 'assigned_at'


@admin.register(TaskCompletion)
class TaskCompletionAdmin(admin.ModelAdmin):
    list_display = ('task', 'user', 'completed_at')
    list_filter = ('completed_at',)
    search_fields = ('task__title', 'user__first_name', 'comment')
    date_hierarchy = 'completed_at'


@admin.register(BotText)
class BotTextAdmin(admin.ModelAdmin):
    list_display = ('name', 'text')
    search_fields = ('name', 'text')
