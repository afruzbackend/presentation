from django.conf import settings
from django.contrib.staticfiles.views import serve as static_serve
from django.urls import include, path, re_path
from django.views.static import serve as media_serve

from lectures import errors

urlpatterns = [
    path('studio/', include('lectures.studio_urls')),
    path('xato/<int:code>/', errors.preview, name='error-preview'),
    # yuklangan rasm/videolar (lokal kompyuterda ishlaydigan dastur)
    re_path(r'^media/(?P<path>.*)$', media_serve, {'document_root': settings.MEDIA_ROOT}),
    path('', include('lectures.urls')),
]

# DEBUG o'chiq bo'lsa ham runserver CSS/rasmlarni bersin (lokal sinf kompyuteri uchun)
if not settings.DEBUG:
    urlpatterns += [re_path(r'^static/(?P<path>.*)$', static_serve, {'insecure': True})]

handler400 = 'lectures.errors.bad_request'
handler403 = 'lectures.errors.permission_denied'
handler404 = 'lectures.errors.page_not_found'
handler500 = 'lectures.errors.server_error'
