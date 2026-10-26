"""Har bir mavzu uchun taqdimot (PDF + PowerPoint) — darslik matnidan avtomatik.

    python manage.py taqdimotlar                  # «Kompyuter tizimlari», barcha mavzular
    python manage.py taqdimotlar --mavzu 5        # faqat 5-mavzu
    python manage.py taqdimotlar boshqa-darslik

Avvalgi avtomatik taqdimotlar yangisi bilan almashtiriladi; o'qituvchi o'zi yuklagan taqdimotlarga tegilmaydi.
"""
from django.core.management.base import BaseCommand, CommandError

from lectures.models import Course
from lectures.taqdimot import FontMissing, make_for_topic


class Command(BaseCommand):
    help = 'Mavzular uchun taqdimot (PDF + PPTX) tayyorlaydi.'

    def add_arguments(self, parser):
        parser.add_argument('slug', nargs='?', default='kompyuter-tizimlari')
        parser.add_argument('--mavzu', type=int, help='faqat shu raqamli mavzu')

    def handle(self, *args, **opts):
        course = Course.objects.filter(slug=opts['slug']).first()
        if not course:
            raise CommandError(f"Darslik topilmadi: {opts['slug']}")
        topics = course.topics.all()
        if opts['mavzu']:
            topics = topics.filter(number=opts['mavzu'])
        total = 0
        try:
            for t in topics:
                n = make_for_topic(t)
                total += n
                self.stdout.write(f'  {t.number}-mavzu: {n} ta slayd')
        except FontMissing as e:
            raise CommandError(str(e)) from None
        self.stdout.write(self.style.SUCCESS(f'«{course.title}»: {topics.count()} ta taqdimot, jami {total} ta slayd.'))
