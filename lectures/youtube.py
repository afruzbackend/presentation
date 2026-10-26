"""YouTube videolarini sayt ichida ko'rsatish.

Avval faqat rasm (muqova) va ▶ tugmasi chiqadi — sahifa tez ochiladi. Bosilganda video shu yerning
o'zida (iframe ichida) ijro etiladi, YouTube sayti ochilmaydi.
"""
import re
from html import escape

ID_RX = re.compile(r'(?:youtu\.be/|[?&]v=|/embed/|/shorts/|/live/|/v/)([\w-]{11})')


def youtube_id(url):
    """Har qanday YouTube havolasidan 11 belgili video ID:
    youtube.com/watch?v=ID, youtu.be/ID?si=..., /shorts/ID, /live/ID, /embed/ID, m.youtube.com/..."""
    if not url:
        return ''
    url = url.strip()
    if re.fullmatch(r'[\w-]{11}', url):
        return url
    if 'youtu' not in url:
        return ''
    m = ID_RX.search(url)
    return m.group(1) if m else ''


def thumb_url(vid):
    return f'https://i.ytimg.com/vi/{vid}/hqdefault.jpg'


def embed_url(vid, autoplay=False):
    # youtube-nocookie: reklama kuzatuvisiz; rel=0: oxirida begona videolar chiqmaydi
    # enablejsapi=1: sahifa pleyerga «to'xtat» buyrug'ini bera oladi (bir vaqtda faqat bitta video)
    return (f'https://www.youtube-nocookie.com/embed/{vid}?rel=0&modestbranding=1&playsinline=1&enablejsapi=1'
            + ('&autoplay=1' if autoplay else ''))


# iframe ichidagi kichik sahifa: muqova rasm + koshin yulduzi shaklidagi ▶ tugma
SRCDOC = (
    '<meta name="referrer" content="strict-origin-when-cross-origin">'
    '<style>*{margin:0;padding:0}html,body{height:100%;overflow:hidden;background:#1B2A4A}'
    'a{position:absolute;inset:0;display:block;cursor:pointer}'
    'img{width:100%;height:100%;object-fit:cover;filter:saturate(1.05);transition:transform .4s}'
    'a:hover img{transform:scale(1.04)}'
    'b{position:absolute;left:50%;top:50%;width:96px;height:96px;margin:-48px 0 0 -48px;background:#C2562D;'
    'clip-path:polygon(50% 0,64.6% 14.6%,85.4% 14.6%,85.4% 35.4%,100% 50%,85.4% 64.6%,85.4% 85.4%,64.6% 85.4%,'
    '50% 100%,35.4% 85.4%,14.6% 85.4%,14.6% 64.6%,0 50%,14.6% 35.4%,14.6% 14.6%,35.4% 14.6%);transition:transform .4s}'
    'a:hover b{transform:rotate(45deg) scale(1.08)}'
    'i{position:absolute;left:50%;top:50%;margin:-16px 0 0 -9px;border-style:solid;border-width:16px 0 16px 28px;'
    'border-color:transparent transparent transparent #FBF6EC}'
    's{position:absolute;left:0;right:0;bottom:0;padding:22px 18px 14px;text-decoration:none;color:#FBF6EC;'
    'font:700 18px Georgia,serif;background:linear-gradient(transparent,rgba(15,25,48,.85))}</style>'
    # bosilganda sahifaga «men boshlayapman» deb xabar beradi — sahifa qolgan videolarni to'xtatadi
    '<a href="{embed}" referrerpolicy="strict-origin-when-cross-origin" onclick="parent.postMessage({ytStart:1},\'*\')">'
    '<img src="{thumb}" alt="" loading="lazy"><b></b><i></i><s>{title}</s></a>'
)


def player_html(url, title=''):
    vid = youtube_id(url)
    if not vid:
        return ''
    # .format() emas: CSS ichidagi {} qavslar bilan to'qnashmasin
    srcdoc = (SRCDOC.replace('{embed}', embed_url(vid, autoplay=True)).replace('{thumb}', thumb_url(vid))
              .replace('{title}', escape(title or '')))
    return (
        # faqat srcdoc (muqova): src bo'lsa, brauzer ba'zan YouTube pleyerni o'zi yuklab, video o'z-o'zidan ijro etiladi
        f'<div class="yt-player"><iframe srcdoc="{escape(srcdoc, quote=True)}" '
        f'title="{escape(title or "Video")}" referrerpolicy="strict-origin-when-cross-origin" '
        # sandbox'da allow-popups va allow-top-navigation yo'q: pleyerdagi «YouTube» logotipi yoki sarlavhasi
        # bosilsa ham YouTube sayti ochilmaydi — video faqat shu yerda ko'riladi
        'sandbox="allow-scripts allow-same-origin allow-presentation" '
        'allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" '
        'allowfullscreen></iframe></div>'
    )

