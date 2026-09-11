@echo off
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe goto instalar
.venv\Scripts\python.exe app.py
if errorlevel 1 pause
exit /b
:instalar
echo Abra INSTALAR.bat primeiro.
pause
