"""Mavzu matnini slaydlarga moslash: qisqa bayon, kartochkalar, slaydlar ro'yxati."""
import re

TAG_RX = re.compile(r'<[^>]+>')


def strip(html):
    return TAG_RX.sub('', html or '')


def first_sentences(html, lo=170, hi=340):
    """Uzun matnni gap chegarasida qisqartirish (<b> teglarini buzmasdan)."""
    if len(strip(html)) <= hi:
        return html
    for m in re.finditer(r'[.!?](?=\s|$)', html):
        if len(strip(html[:m.end()])) >= lo:
            out = html[:m.end()]
            if out.count('<b>') > out.count('</b>'):
                out += '</b>'
            return out
    return html


def split_item(html):
    """'<b>Kalit:</b> izoh' -> ('Kalit', 'izoh')"""
    m = re.match(r'^<b>(.+?)</b>\s*[:—–-]?\s*(.*)$', html, re.S)
    if m:
        return m.group(1).rstrip(': '), m.group(2)
    plain = strip(html)
    i = plain.find(':')
    if 2 < i < 46:
        return plain[:i], plain[i + 1:].strip()
    return '', html


# ------------------------------------------------------------------ slaydlar
def slide_list(topic, sections):
    """Mavzu slaydlari: Kirish, rejalar, (taqdimot), (video), (savol-javob), (test), (mustaqil ta'lim)."""
    kinds = set(topic.resources.values_list('kind', flat=True))
    slides = [{'kind': 'intro', 'name': 'Kirish', 'icon': 'play'}]
    for i, sec in enumerate(sections, 1):
        slides.append({'kind': 'sec', 'name': f'{i}-reja', 'i': i, 'icon': 'book', 'sec': sec})
    if 'slides' in kinds:
        slides.append({'kind': 'slides', 'name': 'Taqdimot', 'icon': 'monitor'})
    if 'video' in kinds:
        slides.append({'kind': 'video', 'name': 'Video dars', 'icon': 'video'})
    if topic.qa.exists():
        slides.append({'kind': 'qa', 'name': 'Savol-javob', 'icon': 'question'})
    if topic.questions or topic.tests.exists():
        slides.append({'kind': 'test', 'name': 'Test', 'icon': 'test'})
    if topic.self_study or topic.literature or kinds & {'material', 'tech'}:
        slides.append({'kind': 'self', 'name': 'Mustaqil ta’lim', 'icon': 'pen'})
    return slides


def slide_count(topic):
    return len(slide_list(topic, list(topic.sections.all())))


# ------------------------------------------------------------------ qisqa ko'rinish
def short_content(section):
    """Reja bo'limidan slayd uchun qisqa ko'rinish tayyorlash."""
    blocks = section.blocks
    ps = [b for b in blocks if b['t'] == 'p']
    ul = next((b for b in blocks if b['t'] == 'ul'), None)
    table = next((b for b in blocks if b['t'] == 'table'), None)

    keys, keys_head = [], ''
    if ul:
        ui = blocks.index(ul)
        keys_head = next((b['text'] for b in reversed(blocks[:ui]) if b['t'] == 'h'), '')
        for i, item in enumerate(ul['items'][:6], 1):
            k, v = split_item(item)
            keys.append({'n': f'{i:02d}', 'k': k, 'v': first_sentences(v, 90, 170)})

    return {
        'lead': first_sentences(ps[0]['html']) if ps else '',
        'image': next((b for b in blocks if b['t'] == 'image'), None),
        'video': next((b for b in blocks if b['t'] == 'video'), None),
        'note': next((b for b in blocks if b['t'] == 'note'), None),
        'keys_head': keys_head,
        'keys': keys,
        # ro'yxat bo'lmasa — jadval, u ham bo'lmasa — ikkinchi xatboshi
        'table': table['rows'][:7] if table and not ul else None,
        'extra': first_sentences(ps[1]['html']) if not ul and not table and len(ps) > 1 else '',
        'has_table': bool(table and ul),
        'heads': [(b['text'], i) for i, b in enumerate(blocks) if b['t'] == 'h'],
        'fact': first_sentences(ps[-1]['html'], 120, 260) if len(ps) > 1 else '',
    }


def grade_for(score, total):
    p = round(score / total * 100) if total else 0
    grade = 5 if p >= 86 else 4 if p >= 71 else 3 if p >= 56 else 2
    msg = {5: 'A’lo! Mavzuni to‘liq o‘zlashtirdingiz.', 4: 'Yaxshi natija! Biroz takrorlash kifoya.',
           3: 'Qoniqarli. Mavzuni yana bir bor ko‘rib chiqing.', 2: 'Mavzuni qayta o‘rganish tavsiya etiladi.'}[grade]
    return {'percent': p, 'grade': grade, 'message': msg, 'score': score, 'total': total}
