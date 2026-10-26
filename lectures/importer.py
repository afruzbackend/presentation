"""docx -> bazadagi darslik. Buyruq (import_docx) va Studiya ikkalasi ham shuni ishlatadi."""
import html
import re
from pathlib import Path

from django.conf import settings
from django.core.files import File
from django.db import transaction

from .docx_parser import parse
from .models import Course, Part, Section, TestQuestion, Topic

# Mavzu nomidagi so'zlarga qarab 3D ko'rgazmani tanlash (har qanday fan uchun)
SCENE_HINTS = [
    (r'mehnat muhofaza|texnika xavfsizlig|xavfsizlik qoida', 'safety'),
    (r'xavfsiz|himoya|virus|parol|shifr', 'shield'),
    (r'printer|skaner|kolonka|qo.shimcha qurilma', 'printer'),
    (r'disk|ssd|xotira|fleshka|saqla', 'disk'),
    (r'operatsion|windows|linux|o.rnatish', 'os'),
    (r'monitor|klaviatura|sichqoncha|asosiy qurilma|ulash', 'monitor'),
    (r'protsessor|ona plata|chipset|komponent|mikrosxema', 'chip'),
    (r'apparat|dasturiy ta.minot|arxitektura|qatlam', 'layers'),
    (r'nosozlik|bartaraf|ta.mir|tuzat', 'tools'),
    (r'diagnost|tekshir|holat|monitoring', 'pulse'),
    (r'tozala|profilakt|sovut|xizmat ko.rsat', 'fan'),
    (r'sozla|parametr|boshqaruv|xizmat|manager', 'gear'),
    (r'tizim bloki|qism|tuzilish', 'tower'),
]
FALLBACK_SCENES = ['layers', 'chip', 'monitor', 'gear', 'disk', 'os', 'pulse']


def guess_scene(title, n):
    low = title.lower()
    for rx, scene in SCENE_HINTS:
        if re.search(rx, low):
            return scene
    return FALLBACK_SCENES[(n - 1) % len(FALLBACK_SCENES)]


def model_row(model, key):
    for row in model:
        if len(row) > 1 and row[0].startswith(key):
            return row[1]
    return ''


@transaction.atomic
def create_course(data, *, title=None, author=None, author_photo=None, replace=None):
    """parse() natijasidan darslik yaratish. replace — shu darslik ma'lumotlari yangilanadi."""
    meta = data['course']
    fields = dict(
        title=title or meta['title'] or 'Yangi darslik', module=meta['module'], college=meta['college'],
        direction=meta['direction'], author=author or meta['author'] or 'Muallif',
        hours_theory=meta['hours_theory'], hours_practice=meta['hours_practice'], hours_self=meta['hours_self'],
        self_study_plan=meta.get('mustaqilPlan', []),
    )
    if replace:
        course = replace
        course.topics.all().delete()
        course.parts.all().delete()
        for k, v in fields.items():
            setattr(course, k, v)
        course.save()
    else:
        course = Course.objects.create(**fields)
    if author_photo:
        course.author_photo.save(Path(author_photo.name).name, author_photo, save=True)

    for t in data['topics']:
        topic = Topic.objects.create(
            course=course, number=t['n'], kind=t['type'], title=t['title'], scene=guess_scene(t['title'], t['n']),
            goal=model_row(t['model'], 'O‘quv mashg‘ulotining maqsadi'),
            result=model_row(t['model'], 'Mashg‘ulotdan kutilayotgan natijalar'),
            methods=model_row(t['model'], 'O‘qitish metodlari'),
            lesson_model=t['model'], tech_map=t['xarita'], prev_questions=t['prevQuestions'],
            questions=t['questions'], grading=t['grading'], self_study=t['mustaqil'], literature=t['adabiyot'],
        )
        Section.objects.bulk_create(
            Section(topic=topic, order=i, title=s['title'], blocks=s['blocks']) for i, s in enumerate(t['sections'], 1))
        TestQuestion.objects.bulk_create(
            TestQuestion(topic=topic, order=i, text=q['q'], options=q['options'], answer=q.get('a') or 0)
            for i, q in enumerate(t['tests'], 1) if len(q['options']) >= 2)
    auto_glossary(course)
    qa_from_content(course)
    return course


# ------------------------------------------------------------------ "Kompyuter tizimlari" darsligi
# Bo'limlar va har bir mavzuning 3D ko'rgazmasi qo'lda tanlangan.
KT_PARTS = [
    ('Xavfsizlik va mehnat muhofazasi', 1, 4, '#C2562D', 'shield'),
    ('Kompyuter tizimining tuzilishi', 5, 11, '#0E7C7B', 'cpu'),
    ('Asosiy va qo‘shimcha qurilmalar', 12, 18, '#9E2A3A', 'monitor'),
    ('Operatsion tizimlar', 19, 27, '#24508F', 'windows'),
    ('Texnik xizmat ko‘rsatish', 28, 30, '#3F7D4E', 'fan'),
    ('Nosozliklarni aniqlash va bartaraf etish', 31, 35, '#B07D1E', 'wrench'),
]
KT_SCENES = {
    1: 'safety', 2: 'tools', 3: 'shield', 4: 'shield', 5: 'tower', 6: 'tower', 7: 'layers', 8: 'layers',
    9: 'chip', 10: 'chip', 11: 'disk', 12: 'monitor', 13: 'printer', 14: 'monitor', 15: 'printer',
    16: 'chip', 17: 'pulse', 18: 'gear', 19: 'os', 20: 'disk', 21: 'os', 22: 'gear', 23: 'gear', 24: 'os',
    25: 'gear', 26: 'pulse', 27: 'gear', 28: 'fan', 29: 'tools', 30: 'fan', 31: 'pulse', 32: 'pulse',
    33: 'tools', 34: 'pulse', 35: 'tools',
}
KT_AUTHOR = 'Oydin Tashtemirova'
IMG = Path(__file__).resolve().parent / 'static' / 'lectures' / 'img'
KT_PHOTO = IMG / 'muallif.jpg'   # ustoz (portret)
KT_COVER = IMG / 'muqova.jpg'    # bosh sahifa foni: ustoz dars o'tayotgan payt


@transaction.atomic
def seed_kompyuter_tizimlari(path=None):
    """data/maruza.docx dan namunaviy darslikni yaratish (yoki yangilash)."""
    data = parse(path or settings.LECTURE_DOCX)
    existing = Course.objects.filter(slug='kompyuter-tizimlari').first()
    course = create_course(data, author=KT_AUTHOR, replace=existing)
    set_kt_images(course)
    for i, (name, a, b, color, icon) in enumerate(KT_PARTS, 1):
        part = Part.objects.create(course=course, order=i, name=name, color=color, icon=icon)
        course.topics.filter(number__gte=a, number__lte=b).update(part=part)
    for n, scene in KT_SCENES.items():
        course.topics.filter(number=n).update(scene=scene)
    return course, data['problems']


def set_kt_images(course):
    """Muallif portreti va bosh sahifa fon rasmini o'rnatish (eskisini almashtiradi)."""
    for field, path in (('author_photo', KT_PHOTO), ('cover_image', KT_COVER)):
        f = getattr(course, field)
        if f:
            f.delete(save=False)
        with open(path, 'rb') as fh:
            f.save(path.name, File(fh, name=path.name), save=False)
    course.save()



# ------------------------------------------------------------------ glossariy va tezkor savol-javob
TERM_P_RX = re.compile(r'^(?:<b>)?([A-ZА-ЯЎҚҒҲ][^<>—:.()«»]{1,48}?)(?:</b>)?\s*(\([^)]{1,50}\))?\s+—\s+(.+)$', re.S)
TERM_LI_RX = re.compile(r'^<b>([^<>:]{2,40}?):?</b>:?\s*(.+)$', re.S)
STOP_START = ('shunday', 'bir ', 'oldingi', 'barcha', 'bu ', 'ushbu', 'har ', 'agar', 'masalan', 'endi', 'avval',
              'keyin', 'asosiy qurilmalarni', 'ekrandagi', 'tashqi dunyo')


def _plain(text):
    return html.unescape(re.sub(r'<[^>]+>', '', text or '')).strip()


def _first_sentence(text, lo=30, hi=320):
    for m in re.finditer(r'[.!?](?=\s|$)', text):
        if m.end() >= lo:
            return text[:m.end()]
    return text[:hi]


def _term_ok(term):
    words = term.split()
    return (1 <= len(words) <= 4 and not any(ch.isdigit() for ch in term)
            and not term.lower().startswith(STOP_START) and len(term) >= 2)


def extract_terms(course):
    """Matndan atamalar: «Atama — ta'rif.» xatboshilari va «**Atama:** izoh» ro'yxat bandlari."""
    found = {}
    for t in course.topics.prefetch_related('sections'):
        for s in t.sections.all():
            for b in s.blocks:
                items = []
                if b['t'] == 'p':
                    m = TERM_P_RX.match(b['html'])
                    if m:
                        term = m.group(1).strip() + (f' {m.group(2)}' if m.group(2) else '')
                        items.append((m.group(1).strip(), term, m.group(3)))
                elif b['t'] == 'ul':
                    for it in b['items']:
                        m = TERM_LI_RX.match(it)
                        if m:
                            items.append((m.group(1).strip(), m.group(1).strip(), m.group(2)))
                for key, term, definition in items:
                    definition = _first_sentence(_plain(definition))
                    if not _term_ok(key) or len(definition) < 20:
                        continue
                    found.setdefault(key.lower(), (term, definition[:1].upper() + definition[1:], t))
    return list(found.values())


def auto_glossary(course, replace=False):
    from .models import GlossaryTerm
    if replace:
        course.glossary.all().delete()
    existing = {g.term.lower() for g in course.glossary.all()}
    new = [GlossaryTerm(course=course, topic=t, term=term, definition=d)
           for term, d, t in extract_terms(course) if term.lower() not in existing]
    GlossaryTerm.objects.bulk_create(new)
    return len(new)


QA_PER_TOPIC = 6


def _qa_candidates(topic, terms):
    """Mavzu matnidan savol-javob nomzodlari (test savollaridan EMAS — aks holda testni yodlab olishadi)."""
    # 1) glossariy atamalari
    for g in terms:
        yield f'«{g.term}» nima?', g.definition
    for sec in topic.sections.all():
        blocks = sec.blocks
        for i, b in enumerate(blocks):
            # 2) ro'yxatdagi kalit tushunchalar: «**Kalit:** izoh»
            if b['t'] == 'ul':
                for it in b['items']:
                    m = TERM_LI_RX.match(it)
                    if m and len(m.group(1).strip()) > 3:
                        yield f'«{m.group(1).strip()}» — bu nima?', _first_sentence(_plain(m.group(2)), 20, 260)
            # 3) sarlavha + undan keyingi xatboshining birinchi gapi
            elif b['t'] == 'h' and i + 1 < len(blocks) and blocks[i + 1]['t'] == 'p':
                head = b['text'].strip()
                q = head if head.endswith('?') else f'«{head}» bo‘yicha asosiy fikr nima?'
                yield q, _first_sentence(_plain(blocks[i + 1]['html']), 40, 300)


def qa_from_content(course, topics=None, per_topic=QA_PER_TOPIC):
    """Savol-javobi yo'q mavzularga matndan kartochkalar yaratish."""
    from .models import QuickQA
    new = []
    topics = topics or list(course.topics.prefetch_related('sections', 'qa', 'terms'))
    for t in topics:
        if t.qa.exists():
            continue
        test_texts = {q.text.strip().lower() for q in t.tests.all()}
        seen, order = set(), 0
        for q, a in _qa_candidates(t, t.terms.all()):
            key = q.lower()
            a = (a or '').strip()
            # sifatsiz juftliklar: javob belgidan boshlansa («→», «(»), juda qisqa bo'lsa,
            # savol tugmalar birikmasi («Ctrl + Alt») yoki qadam raqami («2-qadam») bo'lsa
            if (key in seen or len(a) < 25 or not a[:1].isalpha() or key in test_texts
                    or '+' in q or re.search(r'«\d', q)):
                continue
            a = a[:1].upper() + a[1:]
            seen.add(key)
            order += 1
            new.append(QuickQA(topic=t, order=order, question=q, answer=a))
            if order >= per_topic:
                break
    QuickQA.objects.bulk_create(new)
    return len(new)
