"""Xato sahifalari (400, 403, 404, 405, 413, 500, CSRF) — hammasi Samarqand uslubidagi HTML/CSS.

Shablon so'rov kontekstisiz render qilinadi: baza ishlamay qolgan paytda (500)
ham sahifa ochilishi uchun.
"""
from django.http import Http404, HttpResponse
from django.template.loader import render_to_string
from django.utils.http import url_has_allowed_host_and_scheme

ERRORS = {400: '400.html', 403: '403.html', 404: '404.html', 405: '405.html', 413: '413.html', 500: '500.html'}


def template_for(code):
    """Alohida sahifasi bo'lmagan kodlar eng yaqin sahifaga: 410 -> 404, 429 -> 400, 502 -> 500."""
    if code in ERRORS:
        return ERRORS[code]
    return ERRORS[500] if code >= 500 else ERRORS[404] if code == 410 else ERRORS[400]


def back_url(request):
    """Qayerdan kelgan bo'lsa — o'sha yerga, aks holda bosh sahifaga."""
    ref = request.META.get('HTTP_REFERER', '')
    if ref and url_has_allowed_host_and_scheme(ref, allowed_hosts={request.get_host()}) and not ref.endswith(request.path):
        return ref
    return '/'


def render_error(request, code, template=None, **extra):
    ctx = {
        'code': str(code),
        'path': request.path,
        'back': back_url(request),
        'theme': request.COOKIES.get('theme', 'light'),
        **extra,
    }
    return HttpResponse(render_to_string(template or template_for(code), ctx), status=code)


def bad_request(request, exception=None):
    return render_error(request, 400)


def permission_denied(request, exception=None):
    return render_error(request, 403)


def page_not_found(request, exception=None):
    return render_error(request, 404)


def server_error(request):
    return render_error(request, 500)


def csrf_failure(request, reason=''):
    return render_error(request, 403, '403_csrf.html')


def preview(request, code):
    """Xato sahifalarini ko'rish uchun: /xato/404/"""
    if code not in ERRORS:
        raise Http404
    return render_error(request, code)


class StyledErrorsMiddleware:
    """Django ba'zi xatolarni bo'sh sahifa bilan qaytaradi (masalan, 405 — faqat POST qabul qiladigan
    tugma manzili brauzerda to'g'ridan-to'g'ri ochilsa). Bunday bo'sh javoblarni chiroyli xato sahifasiga
    almashtiradi. API (JSON) javoblariga tegmaydi."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        code = response.status_code
        if (code >= 400 and not getattr(response, 'streaming', False) and not response.content.strip()
                and not request.path.startswith('/api/')):
            styled = render_error(request, code)
            for header in ('Allow', 'Retry-After'):
                if header in response:
                    styled[header] = response[header]
            return styled
        return response
