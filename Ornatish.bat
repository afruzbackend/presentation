@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo.
echo  Kerakli kutubxonalar (Django, Django REST Framework) o'rnatilmoqda...
echo.
python -m pip install -r requirements.txt
echo.
if errorlevel 1 (
  echo  [XATO] O'rnatib bo'lmadi. Yuqoridagi xabarni nusxalab yuboring.
) else (
  echo  [TAYYOR] Endi Ishga_tushirish.bat ni bosing yoki: python manage.py runserver
)
echo.
pause
