#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="$SCRIPT_DIR/.venv"

if [ ! -d "$VENV" ]; then
    echo "Creando entorno virtual..."
    python3 -m venv "$VENV"
    echo "Instalando dependencias..."
    "$VENV/bin/pip" install --quiet yt-dlp imageio-ffmpeg
    echo ""
fi

exec "$VENV/bin/python" "$SCRIPT_DIR/downloader.py" "$@"
