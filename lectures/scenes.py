"""Sof CSS-3D sahnalar: HTML serverda (Python) yasaladi, harakatni CSS beradi.

Har bir mavzu uchun o'ziga xos animatsiyali 3D illyustratsiya.
"""
import math
import random
from itertools import count

_uid = count(1)


def node(tag, cls='', style='', inner=''):
    s = f' style="{style}"' if style else ''
    return f'<{tag} class="{cls}"{s}>{inner}</{tag}>'


def g(transform, children, cls=''):
    """3D guruh. Animatsiya klassi alohida qatlamga: aks holda u inline transformni bosib ketadi."""
    e = node('div', 'o3', f'transform:{transform}' if transform else '', ''.join(children))
    return node('div', f'o3 {cls}', '', e) if cls else e


def box(w, h, d, cls='', transform='', faces=None, extra_style=''):
    """6 yoqli quti."""
    faces = faces or {}
    spec = [
        ('front', w, h, f'translateZ({d / 2}px)'),
        ('back', w, h, f'rotateY(180deg) translateZ({d / 2}px)'),
        ('right', d, h, f'rotateY(90deg) translateZ({w / 2}px)'),
        ('left', d, h, f'rotateY(-90deg) translateZ({w / 2}px)'),
        ('top', w, d, f'rotateX(90deg) translateZ({h / 2}px)'),
        ('bottom', w, d, f'rotateX(-90deg) translateZ({h / 2}px)'),
    ]
    inner = ''.join(
        node('div', f'f f-{name}', f'width:{fw}px;height:{fh}px;margin:{-fh / 2}px 0 0 {-fw / 2}px;transform:{tr}',
             faces.get(name, ''))
        for name, fw, fh, tr in spec)
    style = (f'transform:{transform};' if transform else '') + extra_style
    return node('div', f'o3 box {cls}', style, inner)


def extrude(shape, w, h, depth, c1='#14A3A1', c2='#0E7C7B', side='#084847',
            layers=7, overlay='', cls='', transform=''):
    """Tekis SVG shaklni qatlamlab qalin 3D jismga aylantirish."""
    gid = f'gx{next(_uid)}'
    grad = (f'<defs><linearGradient id="{gid}" x1="0" y1="0" x2="1" y2="1">'
            f'<stop offset="0" stop-color="{c1}"/><stop offset="1" stop-color="{c2}"/></linearGradient></defs>')
    out = []
    for i in range(layers):
        z = -depth / 2 + depth * i / (layers - 1)
        front, back = i == layers - 1, i == 0
        fill = f'url(#{gid})' if front or back else side
        stroke = 'rgba(251,246,236,.6)' if front else 'none'
        svg = (f'<svg viewBox="0 0 {w} {h}" width="{w}" height="{h}">{grad if front or back else ""}'
               f'<g fill="{fill}" stroke="{stroke}" stroke-width="{1.2 if front else 0}">{shape}</g>'
               f'{overlay if front else ""}</svg>')
        out.append(node('div', 'ly' + (' ly-front' if front else ''),
                        f'width:{w}px;height:{h}px;margin:{-h / 2}px 0 0 {-w / 2}px;transform:translateZ({z:.1f}px)', svg))
    return node('div', f'o3 extrude {cls}', f'transform:{transform}' if transform else '', ''.join(out))


def ring(size, cls, transform='', dots=0):
    inner = ''.join(node('i', 'ring-dot', f'transform:rotate({360 / dots * i}deg) translateX({size / 2}px)')
                    for i in range(dots))
    return node('div', f'o3 ring {cls}',
                f'width:{size}px;height:{size}px;margin:{-size / 2}px 0 0 {-size / 2}px;--t:{transform or "none"}', inner)


def plane(w, h, cls, transform=''):
    return node('div', f'o3 plane {cls}', f'width:{w}px;height:{h}px;margin:{-h / 2}px 0 0 {-w / 2}px;transform:{transform}')


def gear_path(n, ro, ri, rh, c):
    step = math.tau / n

    def pt(r, a):
        return f'{c + r * math.cos(a):.1f} {c + r * math.sin(a):.1f}'

    d = ''
    for i in range(n):
        a = i * step
        d += ('L' if i else 'M') + pt(ri, a - step * .32) + 'L' + pt(ro, a - step * .16) + \
            'L' + pt(ro, a + step * .16) + 'L' + pt(ri, a + step * .32)
    d += f'ZM{c + rh} {c}A{rh} {rh} 0 1 0 {c - rh} {c}A{rh} {rh} 0 1 0 {c + rh} {c}Z'
    return f'<path fill-rule="evenodd" d="{d}"/>'


# ------------------------------------------------------------------ sahnalar
def chip():
    s = ''
    for i in range(9):
        p = 46 + i * 16
        s += f'<path class="trace" style="animation-delay:{i * .23:.2f}s" d="M{p} 0V40M{p} 240V200M0 {p}H40M240 {p}H200"/>'
        s += (f'<rect x="{p - 3}" y="38" width="6" height="10" rx="1" fill="#C8952B"/>'
              f'<rect x="{p - 3}" y="192" width="6" height="10" rx="1" fill="#C8952B"/>'
              f'<rect x="38" y="{p - 3}" width="10" height="6" rx="1" fill="#C8952B"/>'
              f'<rect x="192" y="{p - 3}" width="10" height="6" rx="1" fill="#C8952B"/>')
    traces = f'<svg viewBox="0 0 240 240" width="100%" height="100%">{s}</svg>'
    beams = [node('i', 'beam', f'left:{-90 + (i % 4) * 60}px;top:{-90 + (i // 4) * 150}px;animation-delay:{i * .4:.1f}s')
             for i in range(8)]
    return g('rotateX(58deg)', [g('', [
        box(240, 240, 12, 'pcb', '', {'front': traces}),
        box(140, 140, 22, 'chip-body', 'translateZ(17px)',
            {'front': '<div class="chip-label"><b>CPU</b><small>8 yadro · 4.6 GHz</small></div>'}),
        box(64, 64, 6, 'chip-core', 'translateZ(31px)'),
        g('translateZ(40px)', beams, 'beams'),
    ], 'spin')])


def tower():
    front = ('<div class="case-front"><i class="pwr"></i><span class="bay"></span><span class="bay"></span>'
             f'<div class="vents">{"<b></b>" * 10}</div></div>')
    back = f'<div class="case-back"><span class="fanhole"></span><span class="ports">{"<b></b>" * 6}</span></div>'
    glass = '<div class="glass"></div>'
    return g('rotateX(-14deg) rotateY(-32deg)', [
        box(130, 240, 230, 'case', '', {'front': front, 'back': back, 'left': glass, 'right': glass}),
        box(4, 200, 190, 'mobo', 'translateX(50px)'),
        box(70, 70, 50, 'cooler', 'translate3d(25px,-45px,10px)', {'left': '<div class="fanface"></div>'}),
        box(80, 16, 150, 'gpu', 'translate3d(10px,30px,0px)'),
        box(6, 60, 30, 'ram', 'translate3d(40px,-45px,-60px)'),
        box(6, 60, 30, 'ram r2', 'translate3d(30px,-45px,-60px)'),
        box(110, 50, 80, 'psu', 'translate3d(0px,90px,-60px)'),
        box(90, 26, 70, 'hdd', 'translate3d(0px,85px,60px)'),
    ], 'float')


def monitor():
    screen = ('<div class="screen"><div class="sc-bar"><i></i><i></i><i></i></div>'
              f'<div class="sc-body">{"<span></span>" * 6}</div></div>')
    keys = ''.join(f'<rect x="{8 + c * 16}" y="{8 + r * 14}" width="13" height="11" rx="2"/>'
                   for r in range(4) for c in range(13))
    return g('rotateX(-16deg)', [
        box(250, 156, 12, 'mon', 'translateY(-50px)', {'front': screen}),
        box(18, 60, 10, 'stand', 'translate3d(0,50px,-14px)'),
        box(110, 6, 60, 'stand base', 'translate3d(0,82px,-14px)'),
        box(222, 8, 72, 'kbd', 'translate3d(-10px,92px,80px)',
            {'top': f'<svg viewBox="0 0 222 72" width="222" height="72" class="keys">{keys}</svg>'}),
        box(26, 8, 40, 'mouse', 'translate3d(128px,92px,82px)'),
    ], 'float')


def printer():
    lines = ''.join(f'<rect x="12" y="{18 + i * 16}" width="{60 + (i * 37) % 50}" height="6" rx="3"/>' for i in range(7))
    return g('rotateX(-20deg) rotateY(-28deg)', [
        box(210, 80, 140, 'prn', '',
            {'front': '<div class="prn-front"><span class="slot"></span><i class="led"></i><i class="led l2"></i></div>'}),
        box(180, 22, 120, 'prn top', 'translate3d(0,-51px,-6px)', {'top': '<div class="scan-glass"></div>'}),
        box(150, 3, 150, 'paper', 'translate3d(0,-12px,0)',
            {'top': f'<svg viewBox="0 0 150 150" width="150" height="150" class="print">{lines}<circle cx="118" cy="110" r="16"/></svg>'}),
        box(170, 6, 70, 'tray', 'translate3d(0,36px,100px)'),
    ], 'float')


def disk():
    platter = extrude('<circle cx="70" cy="70" r="68"/>', 140, 140, 6, c1='#EFE4D1', c2='#B9AC93', side='#6E6253',
                      layers=4, cls='platter',
                      overlay='<circle cx="70" cy="70" r="14" fill="#1B2A4A"/>'
                              '<circle cx="70" cy="70" r="40" fill="none" stroke="#C8952B" stroke-width="2"/>')
    return g('rotateX(60deg) rotateZ(-24deg)', [
        box(170, 220, 16, 'hdd-case'),
        g('translate3d(0,-22px,12px)', [platter]),
        box(90, 8, 6, 'arm', 'translate3d(36px,48px,18px) rotateZ(-58deg)'),
        box(120, 34, 8, 'ssd', 'translate3d(170px,40px,46px)',
            {'front': '<div class="ssd-face"><b></b><b></b><b></b><span>NVMe</span></div>'}),
        box(70, 70, 8, 'ssd sata', 'translate3d(170px,-60px,26px)', {'front': '<div class="ssd-face sq"><span>SSD</span></div>'}),
    ], 'float')


def layers():
    names = ['Apparat ta’minoti', 'BIOS / UEFI', 'Operatsion tizim', 'Amaliy dasturlar']
    slabs = [box(200, 200, 8, f'slab s{i}', f'translateZ({i * 52}px)',
                 {'front': f'<div class="slab-label"><i>{i + 1}</i>{n}</div>'}, f'--z:{i * 52}px')
             for i, n in enumerate(names)]
    return g('rotateX(60deg) rotateZ(-38deg)', [g('translateZ(-70px)', slabs, 'spinslow')])


def os_windows():
    def win(title, kind):
        return (f'<div class="win {kind}"><div class="win-bar"><i></i><i></i><i></i><span>{title}</span></div>'
                '<div class="win-body"><aside></aside><main><b></b><b></b><b></b><em></em></main></div></div>')
    logo = extrude('<rect x="0" y="0" width="38" height="38" rx="4"/><rect x="42" y="0" width="38" height="38" rx="4"/>'
                   '<rect x="0" y="42" width="38" height="38" rx="4"/><rect x="42" y="42" width="38" height="38" rx="4"/>',
                   80, 80, 14, c1='#2F68B8', c2='#24508F', side='#14305A', transform='translate3d(110px,70px,110px)')
    return g('rotateX(-8deg) rotateY(24deg)', [
        box(220, 150, 4, 'winbox w1', 'translate3d(-60px,-50px,-70px)', {'front': win('Sozlamalar', 'k1')}),
        box(220, 150, 4, 'winbox w2', 'translate3d(0,0,0)', {'front': win('Explorer', 'k2')}),
        box(220, 150, 4, 'winbox w3', 'translate3d(60px,50px,70px)', {'front': win('Task Manager', 'k3')}),
        g('', [logo], 'bob'),
    ], 'float')


def shield():
    shape = '<path d="M80 4 152 30v62c0 48-32 80-72 94C40 172 8 140 8 92V30Z"/>'
    lock = ('<g fill="none" stroke="#fff" stroke-width="9" stroke-linecap="round"><path d="M60 92V74a20 20 0 0 1 40 0v18"/></g>'
            '<rect x="50" y="90" width="60" height="46" rx="9" fill="#fff"/><circle cx="80" cy="110" r="7" fill="#0E7C7B"/>'
            '<rect x="77" y="112" width="6" height="14" rx="3" fill="#0E7C7B"/>')
    return g('', [
        extrude(shape, 160, 192, 26, overlay=lock, layers=8),
        ring(300, 'r1', 'rotateX(74deg)', 3),
        ring(250, 'r2', 'rotateY(70deg) rotateX(20deg)', 2),
        plane(220, 6, 'scanline', 'translateZ(20px)'),
    ], 'sway')


def safety():
    tri = '<path d="M100 8c6 0 10 3 13 8l82 146c6 11-1 22-13 22H18c-12 0-19-11-13-22L87 16c3-5 7-8 13-8Z"/>'
    bolt = '<path d="M108 52 70 120h28l-10 46 42-72h-30l14-42Z" fill="#1B2A4A"/>'
    return g('', [
        extrude(tri, 200, 190, 24, c1='#E0A23B', c2='#C2562D', side='#6E2A12', overlay=bolt, layers=8),
        ring(290, 'r1 warm', 'rotateX(76deg)', 4),
        ring(230, 'r2 warm', 'rotateX(76deg) rotateY(14deg)', 0),
    ], 'sway')


def gear():
    return g('rotateX(-10deg)', [
        g('translate3d(-50px,-20px,0)', [extrude(gear_path(14, 98, 80, 26, 100), 200, 200, 24,
                                                 c1='#2F68B8', c2='#24508F', side='#14305A', cls='gspin')]),
        g('translate3d(92px,78px,10px)', [extrude(gear_path(9, 60, 46, 16, 62), 124, 124, 22,
                                                  c1='#D86A3E', c2='#C2562D', side='#6E2A12', cls='gspin rev')]),
        g('translate3d(100px,-90px,-30px)', [extrude(gear_path(8, 40, 30, 11, 42), 84, 84, 16,
                                                     c1='#E0A23B', c2='#C8952B', side='#6B4E12', cls='gspin rev2')]),
    ], 'sway')


def tools():
    wrench = '<path d="M150 18a40 40 0 0 0-48 50L20 150a14 14 0 0 0 20 20l82-82a40 40 0 0 0 50-48l-24 24-22-6-6-22Z"/>'
    driver = '<path d="M30 160l60-60 12 12-60 60c-4 4-9 4-12 0s-4-8 0-12Z"/><path d="M96 92l50-50 8-26 14 14-26 8-50 50Z"/>'
    return g('', [
        extrude(wrench, 190, 190, 20, c1='#E6DAC4', c2='#B9AC93', side='#5E5240', transform='rotateZ(-8deg) translateZ(-14px)'),
        extrude(driver, 190, 190, 16, transform='rotateZ(86deg) translateZ(14px)'),
        ring(280, 'r1', 'rotateX(76deg)', 3),
    ], 'sway')


def pulse():
    pid = f'pg{next(_uid)}'
    panel = (f'<div class="ecg"><svg viewBox="0 0 240 140" width="240" height="140" preserveAspectRatio="none">'
             f'<defs><pattern id="{pid}" width="20" height="20" patternUnits="userSpaceOnUse">'
             f'<path d="M20 0H0V20" fill="none" stroke="rgba(244,235,221,.13)"/></pattern></defs>'
             f'<rect width="240" height="140" fill="url(#{pid})"/>'
             '<path class="ecg-line" d="M0 80H50l10-28 12 56 12-70 12 70 10-28H140l8-14 8 14H240"/></svg>'
             '<div class="ecg-stat"><b>CPU 37%</b><b>RAM 52%</b><b>48°C</b></div></div>')
    glass = extrude('<path fill-rule="evenodd" d="M58 4a54 54 0 1 1 0 108A54 54 0 0 1 58 4Zm0 14a40 40 0 1 0 0 80 40 40 0 0 0 0-80Z"/>'
                    '<path d="M96 98l14-14 52 52a10 10 0 0 1-14 14Z"/>',
                    170, 170, 14, c1='#E0A23B', c2='#C2562D', side='#6E2A12')
    return g('rotateX(-6deg)', [
        box(250, 150, 8, 'panel', '', {'front': panel}),
        g('', [g('', [glass], 'mag')], 'magwrap'),
    ], 'sway')


def fan():
    blades = ''.join(f'<path transform="rotate({i * 51.4:.1f} 80 80)" d="M80 80C70 50 76 24 96 14c10 18 6 44-16 66Z"/>'
                     for i in range(7))
    rnd = random.Random(7)  # har safar bir xil manzara
    dust = [node('i', 'dust', f'--dx:{rnd.uniform(-160, 160):.0f}px;--dy:{rnd.uniform(-160, 160):.0f}px;'
                              f'animation-delay:{i * .27:.2f}s') for i in range(12)]
    return g('rotateX(-12deg) rotateY(-22deg)', [
        box(180, 14, 30, 'frame', 'translateY(-83px)'), box(180, 14, 30, 'frame', 'translateY(83px)'),
        box(14, 152, 30, 'frame', 'translateX(-83px)'), box(14, 152, 30, 'frame', 'translateX(83px)'),
        extrude(blades + '<circle cx="80" cy="80" r="20"/>', 160, 160, 10, cls='blades', layers=5),
        g('translateZ(30px)', dust, 'dusts'),
    ], 'sway')


BUILDERS = {
    'chip': chip, 'tower': tower, 'monitor': monitor, 'printer': printer, 'disk': disk, 'layers': layers,
    'os': os_windows, 'shield': shield, 'safety': safety, 'gear': gear, 'tools': tools, 'pulse': pulse, 'fan': fan,
}

ICON_OF = {'safety': 'alert', 'tools': 'wrench', 'shield': 'shield', 'tower': 'cpu', 'layers': 'layers', 'chip': 'cpu',
           'disk': 'layers', 'monitor': 'monitor', 'printer': 'file', 'os': 'windows', 'gear': 'spark',
           'pulse': 'target', 'fan': 'fan'}


def scene(theme, small=False):
    parts = ''.join(node('i', '', f'left:{(i * 37) % 100}%;animation-delay:{(i * .7) % 6:.1f}s;animation-duration:{6 + i % 5}s')
                    for i in range(14))
    stage = node('div', 'o3 s-stage', '', BUILDERS.get(theme, chip)())
    return node('div', f'scene3d th-{theme}{" small" if small else ""}', '',
                node('div', 'floor') + node('div', 'parts', '', parts) + node('div', 'o3 s-tilt', '', stage))


# ------------------------------------------------------------------ bosh sahifa rozetkasi
def star(n, outer, inner, rot=0.0):
    pts = []
    for i in range(n * 2):
        a = rot + math.pi * i / n - math.pi / 2
        d = inner if i % 2 else outer
        pts.append(f'{d * math.cos(a):.1f},{d * math.sin(a):.1f}')
    return ' '.join(pts)


def khatam(s, cls=''):
    """Ikki kvadratdan iborat 8 qirrali "xotam" yulduzi."""
    return (f'<g class="{cls}"><rect x="{-s}" y="{-s}" width="{s * 2}" height="{s * 2}"/>'
            f'<rect x="{-s}" y="{-s}" width="{s * 2}" height="{s * 2}" transform="rotate(45)"/></g>')


def rosette(text):
    def layer(cls, depth, inner):
        return (f'<div class="ro-layer {cls}" style="--z:{depth}px">'
                f'<svg viewBox="-300 -300 600 600" xmlns="http://www.w3.org/2000/svg">{inner}</svg></div>')

    ring12 = ''.join(
        f'<g transform="translate({math.cos(i / 12 * math.tau) * 236:.1f} {math.sin(i / 12 * math.tau) * 236:.1f}) '
        f'rotate({i * 30})">{khatam(17)}<circle r="5"/></g>' for i in range(12))
    petals = ''.join(f'<path transform="rotate({i * 22.5})" d="M0 -205 C 22 -175 22 -150 0 -128 C -22 -150 -22 -175 0 -205Z"/>'
                     for i in range(16))
    dots = ''.join(f'<circle transform="rotate({i * 7.5})" cx="0" cy="-272" r="{2.5 if i % 4 else 5}"/>' for i in range(48))
    return (
        layer('l-back', -60, f'<polygon class="r-big" points="{star(16, 290, 250)}"/><g class="r-dots">{dots}</g>') +
        layer('l-ring spin-slow', -30, f'<circle class="r-line" r="262"/><circle class="r-line" r="210"/><g class="r-stars">{ring12}</g>') +
        layer('l-petal spin-rev', 0, f'<g class="r-petals">{petals}</g><polygon class="r-mid" points="{star(8, 196, 150)}"/>') +
        layer('l-text spin-text', 20, '<defs><path id="roText" d="M0,-178 a178,178 0 1,1 -0.1,0"/></defs>'
              f'<text class="r-text"><textPath href="#roText" textLength="1100" lengthAdjust="spacing">{text}</textPath></text>') +
        layer('l-core', 40, f'<polygon class="r-core" points="{star(8, 140, 108, math.pi / 8)}"/>{khatam(84, "r-khatam")}')
    )
