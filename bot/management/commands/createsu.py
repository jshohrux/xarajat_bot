import os
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model


class Command(BaseCommand):
    help = 'Superuser mavjud bo\'lmasa avtomatik yaratadi'

    def handle(self, *args, **options):
        User = get_user_model()
        username = os.getenv('DJANGO_SUPERUSER_USERNAME', 'admin')
        password = os.getenv('DJANGO_SUPERUSER_PASSWORD')
        email = os.getenv('DJANGO_SUPERUSER_EMAIL', '')

        if not password:
            self.stderr.write('DJANGO_SUPERUSER_PASSWORD topilmadi.')
            return

        if User.objects.filter(username=username).exists():
            self.stdout.write(f'Superuser "{username}" allaqachon mavjud.')
            return

        User.objects.create_superuser(username=username, password=password, email=email)
        self.stdout.write(self.style.SUCCESS(f'Superuser "{username}" yaratildi.'))