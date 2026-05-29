# yt-pydownloader

Descargador de YouTube con menú interactivo. Permite descargar audio (MP3/WAV) y video (720p, 1080p, calidad original) con barra de progreso en tiempo real.

## Requisitos

- Python 3.8 o superior
- [ffmpeg](https://ffmpeg.org/) — **no es necesario instalarlo manualmente**, el script lo incluye automáticamente vía `imageio-ffmpeg`

> En Windows se necesita tener Python en el PATH. Descárgalo desde [python.org](https://www.python.org/downloads/) marcando la opción **"Add Python to PATH"** durante la instalación.

## Instalación

No requiere instalación. Al ejecutar por primera vez crea un entorno virtual y descarga las dependencias automáticamente.

## Uso

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
run.bat
```

O desde PowerShell / CMD:

```bat
python downloader.py
```

## Opciones de descarga

| Opción | Formato | Codec | Contenedor |
|--------|---------|-------|------------|
| Audio MP3 | Solo audio | MP3 (máxima calidad) | .mp3 |
| Audio WAV | Solo audio | WAV (sin pérdida) | .wav |
| Video 720p | Video + audio | H.264 + AAC | .mp4 |
| Video 1080p | Video + audio | H.264 + AAC | .mp4 |
| Video original | Video + audio | AV1/VP9 + Opus | .mkv |

Los archivos se guardan en la misma carpeta del script.

## Notas

- Las opciones 720p y 1080p usan H.264 para máxima compatibilidad con QuickTime y reproductores nativos.
- La opción "original" descarga el mejor stream disponible en YouTube (generalmente AV1), más eficiente pero requiere VLC u otro reproductor moderno.
- Video y audio se descargan por separado (así es como YouTube los sirve para resoluciones ≥ 480p) y se unen automáticamente con ffmpeg.
