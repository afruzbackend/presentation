from django import template
from django.conf import settings
from django.utils.safestring import mark_safe

from lectures import scenes
from lectures.youtube import embed_url, player_html, thumb_url, youtube_id

register = template.Library()

# Chiziqli SVG ikonkalar (24x24)
ICONS = {
    'home': '<path d="M3 10.5 12 3l9 7.5"/><path d="M5 9.5V21h5v-6h4v6h5V9.5"/>',
    'grid': '<rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/>',
    'left': '<path d="m15 18-6-6 6-6"/>',
    'right': '<path d="m9 18 6-6-6-6"/>',
    'arrowRight': '<path d="M5 12h14"/><path d="m13 6 6 6-6 6"/>',
    'arrowLeft': '<path d="M19 12H5"/><path d="m11 6-6 6 6 6"/>',
    'search': '<circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/>',
    'sun': '<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/>',
    'moon': '<path d="M20 14.5A8 8 0 1 1 9.5 4a6.5 6.5 0 0 0 10.5 10.5Z"/>',
    'close': '<path d="M6 6l12 12M18 6 6 18"/>',
    'book': '<path d="M4 4.5A2.5 2.5 0 0 1 6.5 2H20v17H6.5A2.5 2.5 0 0 0 4 21.5Z"/><path d="M4 19.5V4.5"/>',
    'list': '<path d="M8 6h13M8 12h13M8 18h13"/><circle cx="3.5" cy="6" r="1"/><circle cx="3.5" cy="12" r="1"/><circle cx="3.5" cy="18" r="1"/>',
    'test': '<path d="M9 11l3 3 8-8"/><path d="M20 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/>',
    'pen': '<path d="M12 20h9"/><path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4Z"/>',
    'user': '<circle cx="12" cy="8" r="4"/><path d="M4 21a8 8 0 0 1 16 0"/>',
    'play': '<path d="M7 4.5v15l12-7.5Z"/>',
    'plus': '<path d="M12 5v14M5 12h14"/>',
    'info': '<circle cx="12" cy="12" r="9"/><path d="M12 11v6M12 7.5v.5"/>',
    'layers': '<path d="m12 3 9 5-9 5-9-5Z"/><path d="m3 13 9 5 9-5"/>',
    'target': '<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="5"/><circle cx="12" cy="12" r="1"/>',
    'spark': '<path d="M12 3v4M12 17v4M3 12h4M17 12h4M6 6l2.5 2.5M15.5 15.5 18 18M6 18l2.5-2.5M15.5 8.5 18 6"/>',
    'clock': '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
    'wrench': '<path d="M14.7 6.3a4 4 0 0 0 5 5L21 13l-8 8-3-3 6.7-6.7a4 4 0 0 1-5-5L13 5Z" transform="translate(-2 0)"/>',
    'question': '<circle cx="12" cy="12" r="9"/><path d="M9.5 9a2.5 2.5 0 1 1 3.5 2.3c-.6.3-1 .9-1 1.6v.6M12 17v.5"/>',
    'refresh': '<path d="M20 11a8 8 0 1 0-2.3 5.7"/><path d="M20 4v7h-7"/>',
    'trophy': '<path d="M8 21h8M12 17v4M7 4h10v5a5 5 0 0 1-10 0Z"/><path d="M17 5h3v2a3 3 0 0 1-3 3M7 5H4v2a3 3 0 0 0 3 3"/>',
    'file': '<path d="M14 3H6a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9Z"/><path d="M14 3v6h6M8 13h8M8 17h5"/>',
    'cpu': '<rect x="6" y="6" width="12" height="12" rx="2"/><rect x="9.5" y="9.5" width="5" height="5"/><path d="M9 2v4M15 2v4M9 18v4M15 18v4M2 9h4M2 15h4M18 9h4M18 15h4"/>',
    'shield': '<path d="M12 3 4 6v6c0 5 3.5 8 8 9 4.5-1 8-4 8-9V6Z"/>',
    'monitor': '<rect x="3" y="4" width="18" height="12" rx="2"/><path d="M8 20h8M12 16v4"/>',
    'windows': '<rect x="3" y="3" width="8" height="8" rx="1"/><rect x="13" y="3" width="8" height="8" rx="1"/><rect x="3" y="13" width="8" height="8" rx="1"/><rect x="13" y="13" width="8" height="8" rx="1"/>',
    'fan': '<circle cx="12" cy="12" r="2"/><path d="M12 10c0-4 1-7 4-7 2 0 2 3 0 5M14 12c4 0 7 1 7 4 0 2-3 2-5 0M12 14c0 4-1 7-4 7-2 0-2-3 0-5M10 12c-4 0-7-1-7-4 0-2 3-2 5 0"/>',
    'alert': '<path d="M12 3 2 20h20Z"/><path d="M12 10v4M12 17v.5"/>',
    'hash': '<path d="M5 9h15M4 15h15M10 3 8 21M16 3l-2 18"/>',
    'graduation': '<path d="m2 9 10-5 10 5-10 5Z"/><path d="M6 11v5c3 2 9 2 12 0v-5M22 9v6"/>',
    'link': '<path d="M10 14a4 4 0 0 0 5.7 0l3-3a4 4 0 0 0-5.7-5.7l-1 1"/><path d="M14 10a4 4 0 0 0-5.7 0l-3 3a4 4 0 0 0 5.7 5.7l1-1"/>',
    'star': '<path d="m12 3 2.7 5.6 6.1.9-4.4 4.3 1 6.1L12 17l-5.4 2.9 1-6.1L3.2 9.5l6.1-.9Z"/>',
    'chevronDown': '<path d="m6 9 6 6 6-6"/>',
    'sparkles': '<path d="M12 3l1.8 4.7L18.5 9.5l-4.7 1.8L12 16l-1.8-4.7L5.5 9.5l4.7-1.8Z"/><path d="M19 15l.8 2.2L22 18l-2.2.8L19 21l-.8-2.2L16 18l2.2-.8Z"/>',
    'check': '<path d="m5 12 5 5 9-10"/>',
    'video': '<rect x="2" y="5" width="14" height="14" rx="2"/><path d="m16 10 6-3v10l-6-3"/>',
    'abc': '<path d="M3 17 6.5 7 10 17M4.3 13.5h4.4"/><path d="M13 7h3.5a2.5 2.5 0 0 1 0 5H13Zm0 5h4a2.5 2.5 0 0 1 0 5h-4Z"/>',
    'download': '<path d="M12 4v11"/><path d="m7 10 5 5 5-5"/><path d="M5 20h14"/>',
    'printer': '<path d="M7 9V3h10v6"/><rect x="3" y="9" width="18" height="8" rx="2"/><path d="M7 14h10v7H7Z"/>',
}


@register.simple_tag
def icon(name, size=20):
    return mark_safe(
        f'<svg class="ic" width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
        f'stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">{ICONS.get(name, "")}</svg>')


@register.simple_tag
def scene(theme, small=False):
    return mark_safe(scenes.scene(theme, small))


@register.simple_tag
def rosette(text):
    return mark_safe(scenes.rosette(text))


@register.filter
def scene_icon(scene):
    """3D ko'rgazma turiga mos kichik ikonka."""
    return scenes.ICON_OF.get(scene, 'book')


@register.filter
def media(path):
    """Yuklangan fayl yo'li -> /media/... manzil"""
    base = settings.MEDIA_URL if settings.MEDIA_URL.startswith('/') else '/' + settings.MEDIA_URL
    return f'{base}{path}' if path else ''


@register.filter
def youtube(url):
    """YouTube havolasidan joylashtirish (embed) manzili ('' — YouTube emas)."""
    vid = youtube_id(url)
    return embed_url(vid) if vid else ''


@register.filter
def yt_thumb(url):
    vid = youtube_id(url)
    return thumb_url(vid) if vid else ''


@register.simple_tag
def yt_player(url, title=''):
    """Sayt ichida ijro etiladigan YouTube pleyer (avval muqova + ▶). YouTube sayti ochilmaydi."""
    return mark_safe(player_html(url, title))


def fnv1a(text):
    h = 0x811C9DC5
    for ch in text.encode():
        h = ((h ^ ch) * 0x01000193) & 0xFFFFFFFF
    return f'{h:08x}'


@register.filter
def answer_hash(q, salt):
    """Oflayn test: to'g'ri javob ochiq yozilmaydi, faqat xeshi (offline.js variantlarni xeshlab solishtiradi)."""
    return fnv1a(f'{salt}:{q.pk}:{q.answer}')


@register.filter
def pad2(n):
    return f'{int(n):02d}'


@register.filter
def delay(i, offset=0):
    """Kirish animatsiyasi kechikishi: '--d:0.21s'"""
    return f'--d:{(int(i) + int(offset)) * 0.07:.2f}s'


@register.filter
def letter(i):
    return 'ABCD'[int(i)]


@register.filter
def is_link(text):
    return any(x in text for x in ('www.', '.uz', '.com'))
