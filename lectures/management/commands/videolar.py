"""«Kompyuter tizimlari» darsligining har bir mavzusiga YouTube'dan tanlangan 2-3 ta video dars.

    python manage.py videolar            # qo'shadi (borlarini takrorlamaydi)
    python manage.py videolar --tekshir  # faqat videolar ochilishini tekshiradi

Har bir video YouTube oEmbed orqali tekshiriladi: o'chirilgan yoki saytga joylashtirish taqiqlangan
videolar qo'shilmaydi.
"""
import json
import urllib.error
import urllib.parse
import urllib.request

from django.core.management.base import BaseCommand

from lectures.models import Course, Resource

# mavzu raqami -> [(video ID, tili)]   tanlov: mavzuga mosligi, o'zbek tilidagilar birinchi
VIDEOS = {
    1: [('NBWIhU_-ta0', 'uz'), ('EeGpYCLI1A0', 'uz'), ('a-XB0ja9rc4', 'ru')],
    2: [('c-QAtjc1H2g', 'uz'), ('3PV9VCaJM0Q', 'ru')],
    3: [('b2JnhOJw_sw', 'uz'), ('2OWkRUPCfdI', 'uz'), ('3-X-FVXv1yg', 'ru')],
    4: [('oNgr1RBCmQc', 'uz'), ('7ng_tA4_Jn8', 'ru'), ('MGcf4fnDLTw', 'ru')],
    5: [('Erv014XqC9Y', 'uz'), ('NWPz4uEwJAE', 'uz'), ('hscJXcQXOS4', 'ru')],
    6: [('EkMtGxVKrtw', 'uz'), ('G-dxTYJugdA', 'uz'), ('-u13PBY5YYo', 'ru')],
    7: [('YRj9o3UEWpg', 'uz'), ('29hQNSF4aZs', 'uz'), ('FSIwiEWSHyo', 'uz')],
    8: [('D43B2oKqX-o', 'uz'), ('ogNJQtvg0cI', 'uz'), ('AMHa5mdjWfI', 'ru')],
    9: [('lMSSuuxUuTo', 'uz'), ('JSh4gNzjAIw', 'uz'), ('qIhZrMg3_Tk', 'ru')],
    10: [('qWiKm6P3hZs', 'uz'), ('7iiD9MRCXKg', 'uz'), ('GE7OlC36CEY', 'ru')],
    11: [('FC_2ljPpeSU', 'uz'), ('eimFds02d1g', 'uz'), ('tjbB2vh627s', 'ru')],
    12: [('_aG394NRckg', 'uz'), ('1yIEKUz4dCk', 'uz')],
    13: [('SlLudSCduBY', 'uz'), ('-bHMIyrO58s', 'uz'), ('HnsRn4TtdVc', 'ru')],
    14: [('Yqv-asAZvG8', 'ru'), ('BFsnipJGSMw', 'ru'), ('gvmLkv7xxmQ', 'uz')],
    15: [('V5Rc0312cPI', 'uz'), ('Iqvq_gi7vnw', 'uz'), ('5rhhHgYi8vE', 'ru')],
    16: [('c6gdO6mwg8w', 'uz'), ('7OZds1UoReU', 'uz'), ('6oSt851vLBE', 'ru')],
    17: [('WbBIfDCQedg', 'uz'), ('3sYlYhXp3ac', 'uz'), ('vrGOuqpKVPw', 'ru')],
    18: [('AeZlFuER6-k', 'uz'), ('PD_O7S2W7C4', 'uz'), ('Vd_g_v__-UU', 'ru')],
    19: [('Z6RWPikefd4', 'uz'), ('jBYEKl-IoBg', 'uz'), ('HgvAF3FD17A', 'ru')],
    20: [('-da4MRirA5E', 'ru'), ('nMXiNPcoYlg', 'ru')],
    21: [('RJFROCk-QE8', 'uz'), ('S2ySxIJhkEY', 'uz'), ('39eOdSzsk_A', 'uz')],
    22: [('O5VIeMktbDk', 'uz'), ('dqE_IvJSIFs', 'uz'), ('yxWOBN-0twA', 'ru')],
    23: [('2DBB2TXwU-E', 'uz'), ('cFRYmZO3Dqk', 'uz'), ('GO2b9vTG_2Y', 'ru')],
    24: [('hK9Snkwe6Lc', 'uz'), ('mRgxMQ4vLqU', 'uz'), ('Xu4tz6HH1c8', 'uz')],
    25: [('0ITnecCj3KE', 'uz'), ('H0N4IPm8_C0', 'ru')],
    26: [('H_2wLaOV6us', 'ru'), ('x5hdw3i4cJo', 'ru')],
    27: [('cOTM7s6Gx1U', 'en'), ('OVXSosPMLy0', 'ru'), ('k1WUVAh2960', 'ru')],
    28: [('Q-1XPeGVgkE', 'uz'), ('7v9FQRNDIYo', 'ru'), ('VYy_3Yse3vY', 'ru')],
    29: [('j68xI37J0V4', 'uz'), ('3xRd5SrHjDM', 'uz'), ('m5yLPKYNj0M', 'ru')],
    30: [('IgEm0rtmpfM', 'uz'), ('1aP7j_bk49Y', 'ru'), ('mEKfxb_r_DU', 'ru')],
    31: [('YFT35OQ9QcI', 'uz'), ('d5j93dURQS4', 'ru'), ('62dbnadKESQ', 'ru')],
    32: [('QwqiFvITwSE', 'ru'), ('9c2OcXcrxd8', 'ru')],
    33: [('rGDkBPiT4Vs', 'ru'), ('TrApep9QasQ', 'ru')],
    34: [('9UGrXEEiZPc', 'ru'), ('lSppTdATOOc', 'ru'), ('hC0ts4aACiM', 'ru')],
    35: [('8cL7Lw2VAdE', 'uz'), ('iEbkTrVyRds', 'uz'), ('lpoXsPWqlB4', 'ru')],
}
LANG = {'uz': 'o‘zbek tilida', 'ru': 'rus tilida', 'en': 'ingliz tilida'}


def oembed(vid):
    """(nomi, kanali) yoki xato matni. 401/403 — joylashtirish taqiqlangan, 404 — video yo'q."""
    url = 'https://www.youtube.com/oembed?format=json&url=' + urllib.parse.quote(f'https://www.youtube.com/watch?v={vid}')
    try:
        d = json.load(urllib.request.urlopen(url, timeout=20))
        return d['title'], d.get('author_name', ''), None
    except urllib.error.HTTPError as e:
        return None, None, {401: 'joylashtirish taqiqlangan', 403: 'joylashtirish taqiqlangan', 404: 'video topilmadi'}.get(e.code, f'HTTP {e.code}')
    except OSError as e:
        return None, None, f'internet xatosi: {e}'


class Command(BaseCommand):
    help = "«Kompyuter tizimlari» mavzulariga YouTube video darslarini qo'shadi."

    def add_arguments(self, parser):
        parser.add_argument('--tekshir', action='store_true', help='Faqat tekshirish, bazaga yozmaslik')

    def handle(self, *args, **opts):
        course = Course.objects.get(slug='kompyuter-tizimlari')
        added = skipped = failed = 0
        for n, items in VIDEOS.items():
            topic = course.topics.get(number=n)
            for vid, lang in items:
                url = f'https://www.youtube.com/watch?v={vid}'
                title, channel, err = oembed(vid)
                if err:
                    failed += 1
                    self.stderr.write(self.style.WARNING(f'  {n}-mavzu {vid}: {err}'))
                    continue
                if opts['tekshir']:
                    continue
                if Resource.objects.filter(course=course, kind='video', url__contains=vid).exists():
                    skipped += 1
                    continue
                Resource.objects.create(course=course, topic=topic, kind='video', title=title[:200], url=url,
                                        note=f'{channel} · {LANG[lang]}'[:300])
                added += 1
        total = sum(len(v) for v in VIDEOS.values())
        self.stdout.write(self.style.SUCCESS(
            f'Jami {total} ta: qo‘shildi {added}, oldin bor edi {skipped}, ishlamadi {failed}.'))
