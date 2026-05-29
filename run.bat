@echo off
setlocal

set SCRIPT_DIR=%~dp0
set VENV=%SCRIPT_DIR%.venv

if not exist "%VENV%" (
    echo Configurando entorno virtual...
    python -m venv "%VENV%"
    echo Instalando dependencias...
    "%VENV%\Scripts\pip" install --quiet yt-dlp imageio-ffmpeg
    echo.
)

"%VENV%\Scripts\python" "%SCRIPT_DIR%downloader.py" %*
