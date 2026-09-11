@echo off
setlocal
cd /d "%~dp0"
echo KAIQUE STUDIO 0.5 - Instalacao
if not exist "%~dp0requirements.txt" (
 echo Extraia o ZIP inteiro antes de instalar. Nao execute dentro do WinRAR.
 pause
 exit /b 1
)
set "KAIQUE_PY="
py -3.11 -c "import sys" >nul 2>&1
if not errorlevel 1 set "KAIQUE_PY=py -3.11"
if defined KAIQUE_PY goto python_ok
python -c "import sys; sys.exit(0 if sys.version_info[:2]==(3,11) else 1)" >nul 2>&1
if not errorlevel 1 set "KAIQUE_PY=python"
if defined KAIQUE_PY goto python_ok
echo Python 3.11 nao encontrado. Abra COMECE-AQUI.txt.
pause
exit /b 1
:python_ok
%KAIQUE_PY% -m venv .venv
if errorlevel 1 goto erro
echo Baixando a interface e as ferramentas. Aguarde...
.venv\Scripts\python.exe -m pip install --log instalacao.log -r requirements.txt
if errorlevel 1 goto erro
.venv\Scripts\python.exe -c "import PySide6, faster_whisper, av, imageio_ffmpeg; print('Dependencias verificadas.')"
if errorlevel 1 goto erro
echo.
echo Instalacao concluida. Agora abra INICIAR.bat.
pause
exit /b 0
:erro
echo.
echo A instalacao nao terminou. Envie um print desta tela.
echo Detalhes adicionais podem estar em instalacao.log.
pause
exit /b 1
