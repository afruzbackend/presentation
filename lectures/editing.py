"""Muharrir uchun: bazadagi HTML <-> ustoz yozadigan oddiy matn.

Qalin matn: **so'z**  ->  <b>so'z</b>
Ro'yxat: har bir qator — bitta band.
Jadval: har bir qator — jadval qatori, kataklar " | " bilan ajratiladi; birinchi qator — sarlavha.
"""
import html
import re

BOLD_RX = re.compile(r'\*\*(.+?)\*\*', re.S)
TAG_RX = re.compile(r'</?b>')


def text_to_html(text):
    """Ustoz yozgan matn -> xavfsiz HTML (faqat <b> ruxsat etiladi)."""
    out = html.escape((text or '').strip(), quote=False)
    return BOLD_RX.sub(r'<b>\1</b>', out)


def html_to_text(value):
    """Bazadagi HTML -> tahrirlash uchun matn."""
    value = (value or '').replace('<b>', '**').replace('</b>', '**').replace('<br>', '\n')
    value = re.sub(r'<[^>]+>', '', value)
    return html.unescape(value)


def lines(text):
    return [ln.strip() for ln in (text or '').splitlines() if ln.strip()]


def list_to_text(items):
    return '\n'.join(html_to_text(x) for x in items)


def text_to_list(text):
    return [text_to_html(x) for x in lines(text)]


def table_to_text(rows):
    return '\n'.join(' | '.join(html_to_text(c) for c in row) for row in rows)


def text_to_table(text):
    rows = [[text_to_html(c.strip()) for c in ln.split('|')] for ln in lines(text)]
    width = max((len(r) for r in rows), default=0)
    return [r + [''] * (width - len(r)) for r in rows]


BLOCK_TYPES = [
    ('h', 'Sarlavha', 'layers'),
    ('p', 'Matn (xatboshi)', 'file'),
    ('ul', 'Ro‘yxat', 'list'),
    ('table', 'Jadval', 'grid'),
    ('image', 'Rasm', 'monitor'),
    ('video', 'Video', 'play'),
    ('note', 'Eslatma', 'info'),
]
BLOCK_NAMES = {k: n for k, n, _ in BLOCK_TYPES}


def block_summary(b):
    """Bloklar ro'yxatida qisqa ko'rinish."""
    t = b.get('t')
    if t == 'h':
        return b.get('text', '')
    if t in ('p', 'note'):
        s = html_to_text(b.get('html', ''))
    elif t == 'ul':
        s = ' • '.join(html_to_text(x) for x in b.get('items', [])[:3])
    elif t == 'table':
        rows = b.get('rows', [])
        s = f"{len(rows)} qator × {len(rows[0]) if rows else 0} ustun: " + ' | '.join(html_to_text(c) for c in (rows[0] if rows else []))
    elif t in ('image', 'video'):
        s = b.get('caption') or b.get('url') or b.get('src', '')
    else:
        s = ''
    return s[:180] + ('…' if len(s) > 180 else '')
