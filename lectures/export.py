"""Darslikni internetsiz ochiladigan papkaga (ZIP) aylantirish.

Har bir sahifa Django orqali render qilinadi, so'ng havolalar fayl nomlariga almashtiriladi.
Natija: index.html ni ikki marta bosish kifoya — Python ham, internet ham kerak emas.
"""
import io
import re
import secrets
import shutil
import zipfile
from pathlib import Path

from django.conf import settings
from django.contrib.staticfiles import finders
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from .content import slide_count

ATTR_RX = re.compile(r'(href|src|action|data-prev|data-next)="(/[^"]*)"')

README = """{title}
{line}

Ochish: «Ochish.bat» faylini ikki marta bosing — darslik brauzerda ochiladi
(Python va boshqa dastur o'rnatish shart emas). Ochilgan qora oynani darslik bilan
ishlab bo'lguncha yopmang.

YouTube videolari darslikning ichida ijro etiladi — buning uchun internet kerak.
Internet bo'lmasa ham matn, slaydlar, 3D ko'rgazmalar va testlar ishlayveradi.

«index.html» ni to'g'ridan-to'g'ri ochsangiz ham bo'ladi, lekin bunda YouTube
videolari ijro etilmaydi (YouTube shunday sahifalarda pleyerni bloklaydi).

Fleshka yoki diskdan ham ishlaydi. Klaviatura:
  ←  →     — oldingi / keyingi slayd
  Backspace — orqaga
  Esc      — oynani yopish

Muallif: {author}
Tayyorlangan sana: {date}
"Elektron darslik" dasturida yaratilgan.
"""

EXTRA = Path(__file__).resolve().parent / 'export_files'

AUTORUN = "[autorun]\r\nshellexecute=Ochish.bat\r\nlabel={label}\r\naction=Elektron darslikni ochish\r\n"


def page_map(course):
    """Sayt manzili -> fayl nomi."""
    slug = course.slug
    pages = {
        reverse('lectures:course', args=[slug]): 'index.html',
        reverse('lectures:contents', args=[slug]): 'mavzular.html',
        reverse('lectures:plan', args=[slug]): 'reja.html',
        reverse('lectures:self_study', args=[slug]): 'mustaqil.html',
        reverse('lectures:final', args=[slug]): 'test.html',
        reverse('lectures:author', args=[slug]): 'muallif.html',
        reverse('lectures:lecture', args=[slug]): 'maruza.html',
        reverse('lectures:slides', args=[slug]): 'taqdimotlar.html',
        reverse('lectures:videos', args=[slug]): 'video.html',
        reverse('lectures:materials', args=[slug]): 'materiallar.html',
        reverse('lectures:tech', args=[slug]): 'texnologiyalar.html',
        reverse('lectures:glossary', args=[slug]): 'glossariy.html',
        reverse('lectures:qa', args=[slug]): 'savol-javob.html',
    }
    for t in course.topics.prefetch_related('sections', 'tests'):
        pages[reverse('lectures:lecture_text', args=[slug, t.number])] = f'maruza-{t.number}.html'
        for s in range(slide_count(t)):
            pages[reverse('lectures:slide', args=[slug, t.number, s])] = f'mavzu-{t.number}-{s}.html'
        pages[reverse('lectures:topic', args=[slug, t.number])] = f'mavzu-{t.number}-0.html'
    return pages


class Rewriter:
    def __init__(self, pages):
        self.pages = pages
        self.static, self.media = set(), set()

    def target(self, url):
        path, _, frag = url.partition('#')
        path = path.split('?', 1)[0]
        frag = f'#{frag}' if frag else ''
        if path in self.pages:
            return self.pages[path] + frag
        if path.startswith('/static/'):
            rel = path[len('/static/'):]
            self.static.add(rel)
            return 'static/' + rel
        media_base = settings.MEDIA_URL if settings.MEDIA_URL.startswith('/') else '/' + settings.MEDIA_URL
        if path.startswith(media_base):
            rel = path[len(media_base):]
            self.media.add(rel)
            return 'media/' + rel
        if path == '/':
            return 'index.html'
        return '#yopish'  # studiya, admin va boshqa server sahifalari oflayn nusxada yo'q

    def __call__(self, html):
        return ATTR_RX.sub(lambda m: f'{m.group(1)}="{self.target(m.group(2))}"', html)


def site_files(course):
    """Darslikning statik nusxasi: [(nisbiy yo'l, matn | fayl yo'li)] — ZIP ham, Netlify sayti ham shundan."""
    pages = page_map(course)
    client = Client(HTTP_X_DARSLIK_EXPORT='1', HTTP_X_DARSLIK_SALT=secrets.token_hex(4))
    rw = Rewriter(pages)
    files = []
    done = set()
    for url, name in pages.items():
        if name in done:
            continue
        resp = client.get(url)
        if resp.status_code != 200:
            continue
        done.add(name)
        files.append((name, rw(resp.content.decode('utf-8'))))
    for rel in sorted(rw.static | {'lectures/js/offline.js', 'lectures/js/ui.js'}):
        found = finders.find(rel)
        if found:
            files.append((f'static/{rel}', Path(found)))
    for rel in sorted(rw.media):
        p = Path(settings.MEDIA_ROOT) / rel
        if p.is_file():
            files.append((f'media/{rel}', p))
    return files


def build_zip(course):
    root = course.slug
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as z:
        for name, data in site_files(course):
            if isinstance(data, Path):
                z.write(data, f'{root}/{name}')
            else:
                z.writestr(f'{root}/{name}', data)
        z.writestr(f'{root}/O‘QING.txt', README.format(
            title=course.title, line='=' * len(course.title), author=course.author,
            date=timezone.localdate().strftime('%d.%m.%Y')).replace('\n', '\r\n'))
        z.writestr(f'{root}/autorun.inf', AUTORUN.format(label=course.title[:32]))
        for f in EXTRA.iterdir():  # Ochish.bat + server.ps1: videolar ichida ko'rinishi uchun
            z.writestr(f'{root}/{f.name}', '\r\n'.join(f.read_text(encoding='utf-8').splitlines()) + '\r\n')
    return buf.getvalue(), f'{root}-oflayn.zip'


def write_site(course, out_dir):
    """Internetga joylash uchun (Netlify, GitHub Pages...): darslik papkaga yoziladi, index.html — bosh sahifa."""
    out = Path(out_dir)
    if out.exists():
        shutil.rmtree(out)
    n = 0
    for name, data in site_files(course):
        target = out / name
        target.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(data, Path):
            shutil.copyfile(data, target)
        else:
            target.write_text(data, encoding='utf-8')
        n += 1
    return n
