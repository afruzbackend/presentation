"""Darslik ma'lumotlaridan o'quv materiallari (PDF, A4): ma'ruza matni, reja, glossariy, savollar, topshiriqlar...

    make_materials(course)  -> yaratilgan materiallar soni

Hamma narsa bazadagi matndan olinadi (o'ylab topilgan ma'lumot yo'q). Ustoz matnni o'zgartirsa —
Studiyadagi «Materiallarni yangilash» tugmasi yoki «python manage.py materiallar» qayta yaratadi.
Test savollari to'plamida to'g'ri javoblar ko'rsatilmaydi.
"""
import html
import io
import re
from functools import lru_cache

from django.utils import timezone

from .taqdimot import FONT_DIR, FONTS, FontMissing, plain

AUTO_NOTE = 'Darslik matnidan avtomatik tayyorlangan'

INK, MUTED, TERRA, OLTIN, LINE, PAPER2, CARD = '#1B2A4A', '#6B6457', '#C2562D', '#B9862A', '#D8C8AE', '#ECDFCB', '#FBF6EC'


@lru_cache(maxsize=None)
def _fonts():
    from reportlab.lib.fonts import addMapping
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    files = {
        'Sans': FONTS[('sans', False)], 'Sans-Bold': FONTS[('sans', True)],
        'Sans-Italic': 'segoeuii.ttf', 'Sans-BoldItalic': 'segoeuiz.ttf',
        'Serif': FONTS[('serif', False)], 'Serif-Bold': FONTS[('serif', True)],
    }
    for name, file in files.items():
        path = FONT_DIR / file
        if not path.exists():
            raise FontMissing(f'Shrift topilmadi: {path}')
        pdfmetrics.registerFont(TTFont(f'M{name}', str(path)))
    addMapping('MSans', 0, 0, 'MSans')
    addMapping('MSans', 1, 0, 'MSans-Bold')
    addMapping('MSans', 0, 1, 'MSans-Italic')
    addMapping('MSans', 1, 1, 'MSans-BoldItalic')
    addMapping('MSerif', 0, 0, 'MSerif')
    addMapping('MSerif', 1, 0, 'MSerif-Bold')
    addMapping('MSerif', 0, 1, 'MSerif')
    addMapping('MSerif', 1, 1, 'MSerif-Bold')
    return True


@lru_cache(maxsize=None)
def _styles():
    from reportlab.lib.colors import HexColor
    from reportlab.lib.styles import ParagraphStyle
    _fonts()
    base = ParagraphStyle('body', fontName='MSans', fontSize=10.5, leading=15, textColor=HexColor(INK), spaceAfter=5)
    return {
        'body': base,
        'muted': ParagraphStyle('muted', parent=base, textColor=HexColor(MUTED), fontSize=9.5, leading=13),
        'h1': ParagraphStyle('h1', parent=base, fontName='MSerif-Bold', fontSize=22, leading=27, spaceAfter=6),
        'h2': ParagraphStyle('h2', parent=base, fontName='MSerif-Bold', fontSize=15, leading=19, spaceBefore=12, spaceAfter=6,
                             textColor=HexColor(INK)),
        'h3': ParagraphStyle('h3', parent=base, fontName='MSans-Bold', fontSize=11.5, leading=15, spaceBefore=8, spaceAfter=3,
                             textColor=HexColor(TERRA)),
        'li': ParagraphStyle('li', parent=base, leftIndent=14, bulletIndent=2, spaceAfter=3),
        'cell': ParagraphStyle('cell', parent=base, fontSize=9, leading=12, spaceAfter=0),
        'cellh': ParagraphStyle('cellh', parent=base, fontName='MSans-Bold', fontSize=9, leading=12, spaceAfter=0,
                                textColor=HexColor('#FBF6EC')),
        'eyebrow': ParagraphStyle('eyebrow', parent=base, fontName='MSans-Bold', fontSize=9, leading=12,
                                  textColor=HexColor(TERRA), spaceAfter=4),
    }


def para_html(s):
    """Bazadagi HTML (faqat <b>, <br>) -> reportlab Paragraph belgilashi (qolgan hammasi xavfsiz matn)."""
    out = []
    for part in re.split(r'(<[^>]+>)', s or ''):
        m = re.fullmatch(r'<\s*(/?)\s*(b|strong|i|em|br)\b[^>]*>', part, re.I)
        if m:
            tag = {'strong': 'b', 'em': 'i'}.get(m.group(2).lower(), m.group(2).lower())
            out.append('<br/>' if tag == 'br' else f'<{m.group(1)}{tag}>')
        elif not part.startswith('<'):
            out.append(html.escape(html.unescape(part), quote=False))
    text = ''.join(out)
    # yopilmay qolgan <b>/<i> — Paragraph xatoga tushmasin
    for tag in ('b', 'i'):
        diff = text.count(f'<{tag}>') - text.count(f'</{tag}>')
        text += f'</{tag}>' * max(diff, 0)
    return text


class Doc:
    """Bitta PDF hujjat: sarlavha bloki, bo'limlar, ro'yxatlar, jadvallar."""

    def __init__(self, course, title, subtitle=''):
        self.course, self.title, self.subtitle = course, title, subtitle
        self.st = _styles()
        self.flow = []
        self._cover()

    def _cover(self):
        from reportlab.platypus import Spacer
        c = self.course
        self.p(f'{c.title.upper()} · {c.module or "elektron darslik"}', 'eyebrow')
        self.p(self.title, 'h1')
        if self.subtitle:
            self.p(self.subtitle, 'muted')
        meta = ' · '.join(x for x in [c.author, c.author_role, c.college] if x)
        self.p(meta, 'muted')
        self.rule(OLTIN, 1.5)
        self.flow.append(Spacer(1, 4))

    def p(self, text, style='body', raw=False):
        from reportlab.platypus import Paragraph
        self.flow.append(Paragraph(text if raw else para_html(text), self.st[style]))

    def h2(self, text):
        from reportlab.platypus import CondPageBreak
        self.flow.append(CondPageBreak(60))
        self.p(text, 'h2')

    def h3(self, text):
        self.p(text, 'h3')

    def bullets(self, items, numbered=False, mark='◆'):
        from reportlab.platypus import Paragraph
        for i, it in enumerate(items, 1):
            self.flow.append(Paragraph(para_html(it), self.st['li'], bulletText=f'{i}.' if numbered else mark))

    def rule(self, color=LINE, width=0.6):
        from reportlab.lib.colors import HexColor
        from reportlab.platypus import HRFlowable
        self.flow.append(HRFlowable(width='100%', thickness=width, color=HexColor(color), spaceBefore=4, spaceAfter=6))

    def table(self, rows, widths=None, header=True):
        from reportlab.lib.colors import HexColor
        from reportlab.platypus import Paragraph, Table, TableStyle
        if not rows:
            return
        ncol = max(len(r) for r in rows)
        rows = [list(r) + [''] * (ncol - len(r)) for r in rows]
        data = [[Paragraph(para_html(str(c)), self.st['cellh' if header and ri == 0 else 'cell']) for c in r]
                for ri, r in enumerate(rows)]
        total = 170 * 72 / 25.4  # A4 matn kengligi (mm -> pt)
        if widths:
            col = [total * w / sum(widths) for w in widths]
        else:
            lens = [max(8, min(60, max(len(plain(str(r[i]))) for r in rows))) for i in range(ncol)]
            col = [total * x / sum(lens) for x in lens]
        t = Table(data, colWidths=col, repeatRows=1 if header else 0)
        style = [
            ('GRID', (0, 0), (-1, -1), 0.5, HexColor(LINE)),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('TOPPADDING', (0, 0), (-1, -1), 4), ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('ROWBACKGROUNDS', (0, 1 if header else 0), (-1, -1), [HexColor(CARD), HexColor('#F4EBDD')]),
        ]
        if header:
            style.append(('BACKGROUND', (0, 0), (-1, 0), HexColor(self.course.color or TERRA)))
        t.setStyle(TableStyle(style))
        self.flow.append(t)
        self.space(6)

    def space(self, h=8):
        from reportlab.platypus import Spacer
        self.flow.append(Spacer(1, h))

    def build(self):
        from reportlab.lib.colors import HexColor
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import mm
        from reportlab.platypus import SimpleDocTemplate

        course, title = self.course, self.title
        accent = course.color or TERRA

        def page(canvas, doc):
            w, h = A4
            canvas.saveState()
            canvas.setFillColor(HexColor(accent))
            canvas.rect(0, h - 5, w, 5, fill=1, stroke=0)
            for i in range(30):  # koshin hoshiyasi
                x, y, r = 12 + i * 20, h - 13, 2.6
                canvas.setFillColor(HexColor(OLTIN if i % 2 else accent))
                p = canvas.beginPath()
                p.moveTo(x, y + r)
                p.lineTo(x + r, y)
                p.lineTo(x, y - r)
                p.lineTo(x - r, y)
                p.close()
                canvas.drawPath(p, fill=1, stroke=0)
            canvas.setStrokeColor(HexColor(LINE))
            canvas.setLineWidth(0.6)
            canvas.line(20 * mm, 14 * mm, w - 20 * mm, 14 * mm)
            canvas.setFont('MSans', 8)
            canvas.setFillColor(HexColor(MUTED))
            canvas.drawString(20 * mm, 9.5 * mm, f'{course.title} · {title}')
            canvas.drawRightString(w - 20 * mm, 9.5 * mm, str(doc.page))
            canvas.restoreState()

        buf = io.BytesIO()
        doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=20 * mm, rightMargin=20 * mm, topMargin=18 * mm,
                                bottomMargin=20 * mm, title=f'{title} — {course.title}', author=course.author)
        doc.build(self.flow, onFirstPage=page, onLaterPages=page)
        return buf.getvalue(), doc.page


# ------------------------------------------------------------------ materiallar
def _topics(course):
    return list(course.topics.select_related('part').prefetch_related('sections', 'tests', 'terms', 'qa'))


def lecture_text(course):
    d = Doc(course, 'Ma’ruza matni', 'Barcha mavzular bo‘yicha to‘liq matn — chop etish va o‘qish uchun.')
    for t in _topics(course):
        d.h2(f'{t.number}-mavzu. {t.title}')
        d.p(f'{t.kind} mashg‘ulot · {t.hours} soat', 'muted')
        for sec in t.sections.all():
            d.h3(sec.title)
            for b in sec.blocks:
                if b['t'] == 'h':
                    d.p(f'<b>{html.escape(plain(b.get("text", "")))}</b>', raw=True)
                elif b['t'] == 'p':
                    d.p(b['html'])
                elif b['t'] == 'ul':
                    d.bullets(b['items'])
                elif b['t'] == 'table':
                    d.table(b['rows'])
                elif b['t'] == 'note':
                    d.p(b.get('html') or b.get('text', ''), 'muted')
    return d


def calendar_plan(course):
    d = Doc(course, 'Kalendar-tematik reja', f'Nazariy: {course.hours_theory} soat · amaliy: {course.hours_practice} soat · '
                                             f'mustaqil ta’lim: {course.hours_self} soat.')
    rows = [['№', 'Mavzu', 'Turi', 'Soat', 'Bo‘lim']]
    for t in _topics(course):
        rows.append([str(t.number), t.title, t.kind, str(t.hours), t.part.name if t.part else ''])
    d.table(rows, widths=[5, 52, 11, 7, 25])
    return d


def glossary(course):
    terms = list(course.glossary.select_related('topic'))
    d = Doc(course, 'Glossariy', f'{len(terms)} ta atama — alifbo tartibida, qaysi mavzuda uchrashi bilan.')
    letter = None
    for g in terms:
        if g.letter != letter:
            letter = g.letter
            d.h3(letter)
        src = f' <font color="{MUTED}">({g.topic.number}-mavzu)</font>' if g.topic else ''
        d.p(f'<b>{html.escape(g.term)}</b> — {para_html(g.definition)}{src}', raw=True)
    return d


def test_bank(course):
    d = Doc(course, 'Test savollari to‘plami', 'Har bir mavzu bo‘yicha test savollari (to‘g‘ri javoblar ko‘rsatilmagan) — '
                                                'mustaqil tayyorgarlik uchun.')
    n = 0
    for t in _topics(course):
        qs = list(t.tests.all())
        if not qs:
            continue
        d.h2(f'{t.number}-mavzu. {t.title}')
        for q in qs:
            n += 1
            d.p(f'<b>{n}. {html.escape(plain(q.text))}</b>', raw=True)
            d.bullets([f'{"ABCD"[i]}) {plain(o)}' for i, o in enumerate(q.options)], mark='')
    return d


def questions(course, field, title, subtitle):
    d = Doc(course, title, subtitle)
    for t in _topics(course):
        items = getattr(t, field) or []
        if items:
            d.h3(f'{t.number}-mavzu. {t.title}')
            d.bullets(items, numbered=True)
    return d


def self_study(course):
    d = Doc(course, 'Mustaqil ta’lim topshiriqlari', f'Jami {course.hours_self} soat: reja va har bir mavzu bo‘yicha topshiriqlar.')
    if course.self_study_plan:
        d.h2('Mustaqil ta’lim rejasi')
        d.table([['№', 'Mavzu', 'Mavzular', 'Soat']] + [list(map(str, r[:4])) for r in course.self_study_plan],
                widths=[6, 64, 15, 9])
    d.h2('Mavzular bo‘yicha topshiriqlar')
    for t in _topics(course):
        if t.self_study:
            d.h3(f'{t.number}-mavzu. {t.title}')
            d.bullets(t.self_study)
    return d


def grading(course):
    d = Doc(course, 'Baholash mezonlari', 'Har bir mavzu bo‘yicha o‘quvchi bilimini baholash mezonlari.')
    for t in _topics(course):
        if t.grading:
            d.h3(f'{t.number}-mavzu. {t.title}')
            d.table(t.grading, widths=[78, 22])
    return d


def literature(course):
    d = Doc(course, 'Adabiyotlar va manbalar', 'Fan bo‘yicha asosiy va qo‘shimcha adabiyotlar, me’yoriy hujjatlar.')
    seen = []
    for t in _topics(course):
        for item in t.literature or []:
            if plain(item) not in [plain(x) for x in seen]:
                seen.append(item)
    d.bullets(seen, numbered=True)
    return d


def qa_cards(course):
    d = Doc(course, 'Tezkor savol-javob', 'Mavzular bo‘yicha qisqa savol va javoblar — takrorlash va og‘zaki so‘rov uchun.')
    for t in _topics(course):
        qa = list(t.qa.all())
        if qa:
            d.h3(f'{t.number}-mavzu. {t.title}')
            for x in qa:
                d.p(f'<b>Savol:</b> {html.escape(plain(x.question))}<br/><b>Javob:</b> {para_html(x.answer)}', raw=True)
    return d


def practicals(course):
    d = Doc(course, 'Amaliy mashg‘ulotlar', 'Amaliy mashg‘ulotlar ro‘yxati: maqsadi va kutilayotgan natija.')
    for t in _topics(course):
        if t.kind != 'Amaliy':
            continue
        d.h3(f'{t.number}-mavzu. {t.title} ({t.hours} soat)')
        if t.goal:
            d.p(f'<b>Maqsad:</b> {para_html(t.goal)}', raw=True)
        if t.result:
            d.p(f'<b>Natija:</b> {para_html(t.result)}', raw=True)
        secs = [s.title for s in t.sections.all()]
        if secs:
            d.p('<b>Reja:</b>', raw=True)
            d.bullets(secs, numbered=True)
    return d


def lesson_models(course):
    d = Doc(course, 'Ta’lim texnologiyasi modellari', 'Har bir mashg‘ulotning ta’lim texnologiyasi modeli.')
    for t in _topics(course):
        if t.lesson_model:
            d.h2(f'{t.number}-mavzu. {t.title}')
            d.table(t.lesson_model, widths=[32, 68])
    return d


def tech_maps(course):
    d = Doc(course, 'Texnologik xaritalar', 'Mashg‘ulot bosqichlari: o‘qituvchi va o‘quvchi faoliyati.')
    for t in _topics(course):
        if t.tech_map:
            d.h2(f'{t.number}-mavzu. {t.title}')
            d.table(t.tech_map, widths=[26, 42, 32])
    return d


# (fayl nomi, turi, nomi, yaratuvchi)
MATERIALS = [
    ('maruza-matni', 'material', 'Ma’ruza matni (to‘liq)', lecture_text),
    ('kalendar-reja', 'material', 'Kalendar-tematik reja', calendar_plan),
    ('glossariy', 'material', 'Glossariy — atamalar lug‘ati', glossary),
    ('test-savollari', 'material', 'Test savollari to‘plami', test_bank),
    ('nazorat-savollari', 'material', 'Mustahkamlash (nazorat) savollari',
     lambda c: questions(c, 'questions', 'Mustahkamlash savollari', 'Har bir mavzu oxirida beriladigan savollar.')),
    ('takrorlash-savollari', 'material', 'O‘tgan mavzuni takrorlash savollari',
     lambda c: questions(c, 'prev_questions', 'O‘tgan mavzuni takrorlash savollari',
                         'Dars boshida o‘tgan mavzuni eslash uchun savollar.')),
    ('mustaqil-talim', 'material', 'Mustaqil ta’lim topshiriqlari', self_study),
    ('amaliy-mashgulotlar', 'material', 'Amaliy mashg‘ulotlar ro‘yxati', practicals),
    ('savol-javob', 'material', 'Tezkor savol-javob kartochkalari', qa_cards),
    ('baholash-mezonlari', 'material', 'Baholash mezonlari', grading),
    ('adabiyotlar', 'material', 'Adabiyotlar va manbalar', literature),
    ('talim-texnologiyasi', 'tech', 'Ta’lim texnologiyasi modellari (barcha mavzular)', lesson_models),
    ('texnologik-xaritalar', 'tech', 'Texnologik xaritalar (barcha mavzular)', tech_maps),
]


def make_materials(course):
    """Umumiy materiallarni (PDF) yaratish; avvalgi avtomatik nusxalar almashtiriladi, ustoz yuklaganlari qoladi."""
    from django.core.files.base import ContentFile

    from .models import Resource

    made = 0
    for slug, kind, title, builder in MATERIALS:
        doc = builder(course)
        if len(doc.flow) <= 5:  # faqat sarlavha — bu bo'limda ma'lumot yo'q
            continue
        data, pages = doc.build()
        for old in course.resources.filter(topic=None, kind=kind, title=title, note__startswith=AUTO_NOTE):
            old.file.delete(save=False)
            old.delete()
        r = Resource(course=course, topic=None, kind=kind, title=title,
                     note=f'{AUTO_NOTE} · PDF, {pages} bet · {timezone.localdate():%d.%m.%Y}')
        r.file.save(f'{course.slug}-{slug}.pdf', ContentFile(data), save=True)
        made += 1
    return made
