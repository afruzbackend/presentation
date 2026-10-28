"""Darslik matnidan umumiy o'quv materiallari (PDF): ma'ruza matni, reja, glossariy, savollar, topshiriqlar...

    python manage.py materiallar                  # «Kompyuter tizimlari»
    python manage.py materiallar boshqa-darslik

Avvalgi avtomatik materiallar yangisi bilan almashtiriladi; o'qituvchi yuklagan fayllarga tegilmaydi.
"""
from django.core.management.base import BaseCommand, CommandError

from lectures.materiallar import make_materials
from lectures.models import Course
from lectures.taqdimot import FontMissing


class Command(BaseCommand):
    help = 'Darslik matnidan umumiy materiallar (PDF) tayyorlaydi.'

    def add_arguments(self, parser):
        parser.add_argument('slug', nargs='?', default='kompyuter-tizimlari')

    def handle(self, *args, **opts):
        course = Course.objects.filter(slug=opts['slug']).first()
        if not course:
            raise CommandError(f"Darslik topilmadi: {opts['slug']}")
        try:
            made = make_materials(course)
        except FontMissing as e:
            raise CommandError(str(e)) from None
        self.stdout.write(self.style.SUCCESS(f'«{course.title}»: {made} ta material tayyorlandi.'))
