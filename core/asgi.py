import asyncio
import os

import httpx
from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

_django_app = get_asgi_application()


def _health_url() -> str:
    webhook_url = os.getenv('WEBHOOK_URL', '')
    if not webhook_url:
        return ''
    return webhook_url.split('/webhook')[0] + '/'


async def _keep_alive():
    url = _health_url()
    if not url:
        return
    await asyncio.sleep(60)
    while True:
        try:
            async with httpx.AsyncClient() as client:
                await client.get(url, timeout=10)
        except Exception:
            pass
        await asyncio.sleep(4 * 60)  # har 4 daqiqada ping


async def application(scope, receive, send):
    if scope['type'] == 'lifespan':
        while True:
            event = await receive()
            if event['type'] == 'lifespan.startup':
                asyncio.create_task(_keep_alive())
                await send({'type': 'lifespan.startup.complete'})
            elif event['type'] == 'lifespan.shutdown':
                await send({'type': 'lifespan.shutdown.complete'})
                return
    else:
        await _django_app(scope, receive, send)
