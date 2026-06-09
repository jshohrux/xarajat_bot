from django.contrib import admin
from .models import TelegramUser, TelegramGroup, Expense


@admin.register(TelegramUser)
class TelegramUserAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'username', 'telegram_id', 'created_at')


@admin.register(TelegramGroup)
class TelegramGroupAdmin(admin.ModelAdmin):
    list_display = ('title', 'chat_id', 'created_at')


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ('user', 'group', 'amount', 'description', 'status', 'created_at')
    list_filter = ('group', 'status', 'created_at')
