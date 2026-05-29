# yt-pydownloader

Descargador de YouTube con menú interactivo. Permite descargar audio (MP3/WAV) y video (720p, 1080p, calidad original) con barra de progreso en tiempo real.

## Requisitos

**Solo necesitas Python 3.8 o superior.** El resto se instala automáticamente la primera vez que ejecutas el script:

| Herramienta | Instalación |
|---|---|
| Python 3.8+ | Manual (ver abajo) |
| yt-dlp | Automática |
| ffmpeg | Automática (binario estático incluido) |
| Deno | Automática (descargado si no está en el sistema) |

> **Windows:** descarga Python desde [python.org](https://www.python.org/downloads/) marcando la opción **"Add Python to PATH"** durante la instalación.

## Uso

### Primera ejecución

Al ejecutar por primera vez, el script configura el entorno automáticamente:

```
Configurando entorno (primera vez)...
Instalando dependencias (yt-dlp, ffmpeg)...
Descargando Deno (runtime JS para YouTube)...
```

Desde la segunda ejecución arranca directo.

### macOS / Linux

```bash
python3 downloader.py
```

O alternativamente:

```bash
./run.sh
```

### Windows

```bat
python downloader.py
```

O alternativamente:

```bat
run.bat
```

## Opciones de descarga

| Opción | Codec video | Codec audio | Contenedor |
|--------|-------------|-------------|------------|
| Audio MP3 | — | MP3 (máxima calidad) | .mp3 |
| Audio WAV | — | WAV (sin pérdida) | .wav |
| Video 720p | H.264 | AAC | .mp4 |
| Video 1080p | H.264 | AAC | .mp4 |
| Video original | AV1 / VP9 | Opus | .mkv |

- Las opciones 720p y 1080p usan H.264 para compatibilidad con QuickTime y reproductores nativos.
- La opción "original" descarga el mejor stream disponible (generalmente AV1), más eficiente pero requiere VLC u otro reproductor moderno.
- Video y audio se descargan por separado (así los sirve YouTube para resoluciones ≥ 480p) y se unen automáticamente con ffmpeg.
- Los archivos se guardan en la misma carpeta del script.

## Aviso legal

Ver sección de [propiedad intelectual en el release v1.0.0](https://github.com/vicvinue/yt-pydownloader/releases/tag/v1.0.0).
