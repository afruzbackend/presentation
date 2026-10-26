from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from lectures.docx_parser import parse
from lectures.importer import create_course, seed_kompyuter_tizimlari


class Command(BaseCommand):
    help = ("Ma'ruza .docx faylidan darslik yaratadi. Fayl ko'rsatilmasa — data/maruza.docx dan "
            "'Kompyuter tizimlari' darsligi yaratiladi (yoki yangilanadi).")

    def add_arguments(self, parser):
        parser.add_argument('path', nargs='?', help="docx fayl yo'li")
        parser.add_argument('--author', help='Muallif ismi')
        parser.add_argument('--title', help='Darslik nomi (docx dagi nom o‘rniga)')

    def handle(self, *args, **opts):
        if not opts['path']:
            course, problems = seed_kompyuter_tizimlari()
        else:
            path = Path(opts['path'])
            if not path.exists():
                raise CommandError(f'Fayl topilmadi: {path}')
            data = parse(path)
            course = create_course(data, title=opts['title'], author=opts['author'])
            problems = data['problems']
        for p in problems:
            self.stderr.write(self.style.WARNING('  ! ' + p))
        self.stdout.write(self.style.SUCCESS(
            f"«{course.title}»: {course.topics.count()} ta mavzu, "
            f"{sum(t.tests.count() for t in course.topics.all())} ta test savoli. Manzil: /d/{course.slug}/"))
