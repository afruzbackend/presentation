from pathlib import Path

# CSS/JS o'zgarsa, havola ham o'zgaradi (?v=...) — brauzer eski nusxani keshdan olmaydi
_STATIC = Path(__file__).resolve().parent / 'static' / 'lectures'


def asset_version():
    return str(int(max((f.stat().st_mtime for f in _STATIC.rglob('*') if f.suffix in ('.css', '.js')), default=0)))


ASSET_V = asset_version()


def site(request):
    return {
        'theme': request.COOKIES.get('theme', 'light'),
        # eksport paytida (oflayn papka) server talab qiladigan tugmalar yashiriladi
        'exporting': request.META.get('HTTP_X_DARSLIK_EXPORT') == '1',
        'v': ASSET_V,
        # har eksportga alohida «tuz» — test javoblari xeshi nusxadan nusxaga farq qiladi
        'salt': request.META.get('HTTP_X_DARSLIK_SALT', ''),
    }
