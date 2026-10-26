import secrets
import string

from django.conf import settings
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

TEMPLATE = """ELEKTRON DARSLIK — STUDIYAGA KIRISH
====================================

Manzil:  http://127.0.0.1:8000/studio/
Login:   {login}
Parol:   {password}

Kirgandan so'ng parolni o'zgartirish mumkin: Studiya -> yuqoridagi ismingiz -> «Parolni o'zgartirish».
Parolni unutsangiz, terminalda:  python manage.py ustoz --yangi
Bu faylni boshqalarga ko'rsatmang.
"""


def make_password():
    """Eslab qolish oson, lekin taxmin qilib bo'lmaydigan parol: Darslik-4821-kp"""
    digits = ''.join(secrets.choice(string.digits) for _ in range(4))
    letters = ''.join(secrets.choice('abdefhkmnprstuvxyz') for _ in range(2))
    return f'Darslik-{digits}-{letters}'


class Command(BaseCommand):
    help = "Ustoz uchun Studiya akkauntini yaratadi; login va parolni KIRISH.txt fayliga yozadi."

    def add_arguments(self, parser):
        parser.add_argument('--login', default='ustoz')
        parser.add_argument('--ism', default='Oydin Tashtemirova', help='Studiyada ko‘rinadigan ism')
        parser.add_argument('--yangi', action='store_true', help='Akkaunt bor bo‘lsa ham yangi parol berish')

    def handle(self, *args, **opts):
        user = User.objects.filter(username=opts['login']).first()
        if user and not opts['yangi']:
            self.stdout.write(self.style.WARNING(
                f"«{user.username}» akkaunti allaqachon bor. Yangi parol uchun: python manage.py ustoz --yangi"))
            return
        password = make_password()
        if user is None:
            user = User.objects.create_superuser(opts['login'], password=password, first_name=opts['ism'])
        else:
            user.set_password(password)
            user.save(update_fields=['password'])
        path = settings.BASE_DIR / 'KIRISH.txt'
        path.write_text(TEMPLATE.format(login=user.username, password=password), encoding='utf-8')
        self.stdout.write(self.style.SUCCESS(f"Tayyor. Login: {user.username}. Parol {path.name} faylida."))
