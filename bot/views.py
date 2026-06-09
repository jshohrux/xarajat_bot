import json
import asyncio
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from telegram import Update
from bot.handlers import build_application

_app = None
_lock = asyncio.Lock()


async def _get_app():
    global _app
    if _app is not None:
        return _app
    async with _lock:
        if _app is None:
            _app = build_application()
            await _app.initialize()
            await _app.start()
    return _app


@csrf_exempt
async def webhook(request):
    if request.method != 'POST':
        return HttpResponse(status=405)

    secret = request.headers.get('X-Telegram-Bot-Api-Secret-Token', '')
    if settings.WEBHOOK_SECRET and secret != settings.WEBHOOK_SECRET:
        return HttpResponse(status=403)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return HttpResponse(status=400)

    app = await _get_app()
    update = Update.de_json(data, app.bot)
    await app.process_update(update)
    return HttpResponse('ok')