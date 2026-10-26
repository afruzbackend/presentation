"""Bir bosishda ishga tushirish: baza tayyorlanadi, Django server yoqiladi, brauzer ochiladi.

    python main.py            # http://127.0.0.1:8000 — Edge/Chrome "ilova" oynasida
    python main.py --browser  # oddiy brauzer oynasida

Odatiy Django usuli ham ishlaydi:
    python manage.py migrate
    python manage.py import_docx
    python manage.py runserver
"""
import os
import shutil
import subprocess
import sys
import threading
import webbrowser

ADDR = '127.0.0.1:8000'
URL = f'http://{ADDR}/'

BROWSERS = [
    r'%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe',
    r'%ProgramFiles%\Microsoft\Edge\Application\msedge.exe',
    r'%ProgramFiles%\Google\Chrome\Application\chrome.exe',
    r'%LocalAppData%\Google\Chrome\Application\chrome.exe',
]


def open_browser():
    exe = None
    if '--browser' not in sys.argv:
        exe = next((p for p in map(os.path.expandvars, BROWSERS) if os.path.isfile(p)), None) or shutil.which('msedge')
    if exe:
        subprocess.Popen([exe, f'--app={URL}', '--start-maximized'])
    else:
        webbrowser.open(URL)


def main():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    import django
    from django.core.management import call_command
    django.setup()

    call_command('migrate', verbosity=0)
    from lectures.models import Topic
    if not Topic.objects.exists():
        call_command('import_docx')
    try:  # har ishga tushishda zaxira nusxa: backups/ papkada oxirgi 10 tasi
        from lectures.backup import auto_backup
        auto_backup()
    except Exception as e:  # noqa: BLE001 — zaxira xatosi dasturni to'xtatmasin
        print('Zaxira nusxa olinmadi:', e)

    threading.Timer(1.5, open_browser).start()
    print(f"Elektron ma'ruza: {URL}  (to'xtatish: Ctrl+C)")
    call_command('runserver', ADDR, '--noreload')


if __name__ == '__main__':
    main()
