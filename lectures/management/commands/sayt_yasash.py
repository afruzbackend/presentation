"""Internetga joylash uchun statik sayt (Netlify): Django serversiz ishlaydigan nusxa «sayt/» papkasiga.

    python manage.py sayt_yasash                       # «Kompyuter tizimlari» -> sayt/
    python manage.py sayt_yasash boshqa-darslik --papka public

Sayt joriy bazadan yasaladi — Studiyada qilingan o'zgarishlar ham kiradi. O'zgartirgandan keyin
buyruqni qayta ishga tushiring va GitHub'ga push qiling: Netlify o'zi yangilaydi.
Internetdagi nusxada Studiya (tahrirlash) yo'q, testlar brauzerning o'zida tekshiriladi.
"""
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from lectures.export import write_site
from lectures.models import Course


class Command(BaseCommand):
    help = "Darslikdan Netlify uchun statik sayt yasaydi (sayt/ papkasi)."

    def add_arguments(self, parser):
        parser.add_argument('slug', nargs='?', default='kompyuter-tizimlari', help='darslik manzili (slug)')
        parser.add_argument('--papka', default='sayt', help='natija papkasi (loyiha ichida)')

    def handle(self, *args, **opts):
        course = Course.objects.filter(slug=opts['slug']).first()
        if not course:
            raise CommandError(f"Darslik topilmadi: {opts['slug']}. Avval: python manage.py import_docx")
        out = (settings.BASE_DIR / opts['papka']).resolve()
        # papka avval tozalanadi — boshqa narsa (kod, ma'lumot) turgan papkani o'chirib yubormaslik uchun
        if out == settings.BASE_DIR.resolve() or (out.is_dir() and any(out.iterdir()) and not (out / 'index.html').exists()):
            raise CommandError(f'{out} bo‘sh emas va darslik sayti emas — boshqa papka nomini bering (--papka).')
        n = write_site(course, out)
        self.stdout.write(self.style.SUCCESS(f'«{course.title}»: {n} ta fayl -> {out}'))
