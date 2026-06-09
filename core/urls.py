from django.contrib import admin
from django.urls import path
from django.http import HttpResponse
from bot.views import webhook
from bot.api import expense_list, expense_create, expense_delete, total, clear
from bot.management_api import (
    cmd_migrate, cmd_setwebhook, cmd_delete_webhook,
    cmd_createsu, cmd_collectstatic,
)

urlpatterns = [
    path('', lambda request: HttpResponse('ok'), name='health'),
    path('admin/', admin.site.urls),
    path('webhook/', webhook, name='webhook'),

    # Data API
    path('api/expenses/', expense_list, name='api-expense-list'),
    path('api/expenses/add/', expense_create, name='api-expense-create'),
    path('api/expenses/<int:expense_id>/delete/', expense_delete, name='api-expense-delete'),
    path('api/total/', total, name='api-total'),
    path('api/clear/', clear, name='api-clear'),

    # Management commands API
    path('api/cmd/migrate/', cmd_migrate, name='cmd-migrate'),
    path('api/cmd/setwebhook/', cmd_setwebhook, name='cmd-setwebhook'),
    path('api/cmd/deletewebhook/', cmd_delete_webhook, name='cmd-deletewebhook'),
    path('api/cmd/createsu/', cmd_createsu, name='cmd-createsu'),
    path('api/cmd/collectstatic/', cmd_collectstatic, name='cmd-collectstatic'),
]
