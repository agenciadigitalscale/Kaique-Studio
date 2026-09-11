@echo off
cd /d "%~dp0"
.venv\Scripts\python.exe -c "import sys; print(sys.version); import PySide6, av, faster_whisper, core; print('Interface e transcricao: OK'); exe=core.ffmpeg(); print('FFmpeg:',exe); result=core.run([exe,'-hide_banner','-filters']); print('Suporte a legendas:', 'subtitles' in result.stdout)"
pause
