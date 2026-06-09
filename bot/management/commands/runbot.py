from django.core.management.base import BaseCommand
from django.conf import settings


class Command(BaseCommand):
    help = 'Telegram botni ishga tushiradi'

    def handle(self, *args, **options):
        if not settings.BOT_TOKEN or settings.BOT_TOKEN == 'your_bot_token_here':
            self.stderr.write(self.style.ERROR(
                "BOT_TOKEN topilmadi. .env faylida BOT_TOKEN ni to'ldiring."
            ))
            return

        self.stdout.write(self.style.SUCCESS('Bot ishga tushmoqda...'))

        from bot.handlers import build_application
        app = build_application()
        app.run_polling(drop_pending_updates=True)
