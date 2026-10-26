"""Zaxira nusxa: barcha darsliklar (baza) + yuklangan fayllar (media) bitta ZIP faylda.

    make_backup()         -> ZIP baytlari (Studiya → «Zaxira nusxa» → yuklab olish)
    auto_backup()         -> har ishga tushishda backups/ papkaga (oxirgi 10 tasi saqlanadi)
    restore(fayl)         -> ZIP'dan qayta tiklash (joriy darsliklar almashtiriladi)

Login/parol zaxiraga kirmaydi — tiklashdan keyin ham o'qituvchi o'z paroli bilan kiradi.
"""
import io
import json
import tempfile
import zipfile
from pathlib import Path

from django.conf import settings
from django.core.management import call_command
from django.db import transaction
from django.utils import timezone

from .models import Course

MANIFEST = 'zaxira.json'
DATA = 'baza.json'
KEEP = 10


class BackupError(Exception):
    pass


def backup_dir():
    return Path(settings.BASE_DIR) / 'backups'


def make_backup():
    out = io.StringIO()
    call_command('dumpdata', 'lectures', indent=1, stdout=out)
    media = Path(settings.MEDIA_ROOT)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as z:
        z.writestr(MANIFEST, json.dumps({'dastur': 'elektron-darslik', 'versiya': 1,
                                         'sana': timezone.localtime().strftime('%Y-%m-%d %H:%M'),
                                         'darsliklar': list(Course.objects.values_list('title', flat=True))},
                                        ensure_ascii=False, indent=1))
        z.writestr(DATA, out.getvalue())
        if media.is_dir():
            for f in media.rglob('*'):
                if f.is_file():
                    z.write(f, 'media/' + f.relative_to(media).as_posix())
    return buf.getvalue()


def backup_name():
    return f'darslik-zaxira-{timezone.localtime():%Y-%m-%d_%H-%M-%S}.zip'


def auto_backup(keep=KEEP):
    """Ishga tushishda: baza bo'sh bo'lmasa, nusxa yoziladi; eskilari o'chiriladi."""
    if not Course.objects.exists():
        return None
    d = backup_dir()
    d.mkdir(exist_ok=True)
    path = d / backup_name()
    path.write_bytes(make_backup())
    for old in sorted(d.glob('darslik-zaxira-*.zip'))[:-keep]:
        old.unlink(missing_ok=True)
    return path


def read_manifest(fileobj):
    try:
        z = zipfile.ZipFile(fileobj)
        info = json.loads(z.read(MANIFEST).decode('utf-8'))
        z.getinfo(DATA)
    except (zipfile.BadZipFile, KeyError, ValueError):
        raise BackupError('Bu fayl darslik zaxira nusxasi emas.') from None
    if info.get('dastur') != 'elektron-darslik':
        raise BackupError('Bu fayl darslik zaxira nusxasi emas.')
    return z, info


def restore(fileobj):
    z, info = read_manifest(fileobj)
    media = Path(settings.MEDIA_ROOT).resolve()
    files = []
    for name in z.namelist():
        if not name.startswith('media/') or name.endswith('/'):
            continue
        target = (media / name[len('media/'):]).resolve()
        if not target.is_relative_to(media):  # «../» bilan papkadan tashqariga yozishga yo'l qo'ymaslik
            raise BackupError('Zaxira faylida noto‘g‘ri yo‘l bor.')
        files.append((name, target))

    with tempfile.TemporaryDirectory() as tmp:
        data = Path(tmp) / DATA
        data.write_bytes(z.read(DATA))
        with transaction.atomic():
            Course.objects.all().delete()  # mavzular, testlar, resurslar... ham birga o'chadi
            call_command('loaddata', str(data), verbosity=0)

    for name, target in files:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(z.read(name))
    return info
