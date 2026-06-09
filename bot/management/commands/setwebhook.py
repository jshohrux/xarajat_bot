import asyncio
from django.core.management.base import BaseCommand
from django.conf import settings
from telegram import Bot


class Command(BaseCommand):
    help = 'Telegram webhook URL ni o\'rnatadi yoki o\'chiradi'

    def add_arguments(self, parser):
        parser.add_argument('--delete', action='store_true', help='Webhookni o\'chirish')

    def handle(self, *args, **options):
        asyncio.run(self._run(options['delete']))

    async def _run(self, delete: bool):
        if not settings.BOT_TOKEN:
            self.stderr.write(self.style.ERROR('BOT_TOKEN topilmadi.'))
            return

        bot = Bot(token=settings.BOT_TOKEN)

        if delete:
            await bot.delete_webhook(drop_pending_updates=True)
            self.stdout.write(self.style.SUCCESS('Webhook o\'chirildi.'))
            return

        if not settings.WEBHOOK_URL:
            self.stderr.write(self.style.ERROR('WEBHOOK_URL topilmadi. .env ga yozing.'))
            return

        url = settings.WEBHOOK_URL.rstrip('/') + '/webhook/'
        kwargs = {'url': url, 'drop_pending_updates': True}
        if settings.WEBHOOK_SECRET:
            kwargs['secret_token'] = settings.WEBHOOK_SECRET

        await bot.set_webhook(**kwargs)
        info = await bot.get_webhook_info()
        self.stdout.write(self.style.SUCCESS(f'Webhook o\'rnatildi: {info.url}'))
        if info.last_error_message:
            self.stderr.write(self.style.WARNING(f'Oxirgi xato: {info.last_error_message}'))
