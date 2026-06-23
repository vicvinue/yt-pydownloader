# yt-pydownloader

**Español** | [English](README.en.md)

Descargador de YouTube con menú interactivo. Permite descargar audio (Opus, M4A, MP3) y video (480p hasta 2160p/4K) con barra de progreso en tiempo real.

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

---

### Interfaz web (recomendada)

Abre una UI en el navegador en `http://localhost:7788`. Funciona igual en macOS, Linux y Windows.

**macOS / Linux**

```bash
python3 web.py
# o bien:
./run-web.sh
```

**Windows**

```bat
python web.py
rem o bien:
run-web.bat
```

El navegador se abre automáticamente. Para cerrar el servidor presiona `Ctrl+C` en la terminal.

---

### Interfaz de línea de comandos

**macOS / Linux**

```bash
python3 downloader.py
# o bien:
./run.sh
```

**Windows**

```bat
python downloader.py
rem o bien:
run.bat
```

Muestra un menú con colores agrupado en **Audio / Video**, con badges de calidad (HQ, SD, HD, FHD, 2K, 4K) y metadatos del video (duración, canal, vistas). Los colores se desactivan automáticamente si la salida no es una terminal o si defines `NO_COLOR`.

Funciona en **bucle continuo**: tras cada descarga vuelve a pedir otro enlace; escribe `0` para salir. Los errores no cierran el programa, simplemente vuelve al prompt.

## Opciones de descarga

### Audio

| Formato | Códec | Contenedor |
|---------|-------|------------|
| **Opus** | Opus (copia nativa de YouTube) | `.opus` |
| **M4A** | AAC | `.m4a` |
| **MP3** | MP3 (VBR ~q0) | `.mp3` |

- **Opus** es la mejor calidad por bit; si la fuente ya es Opus se extrae sin recodificar.
- **M4A** (AAC) es la opción de máxima compatibilidad.
- **MP3** se recodifica, pensada para equipos antiguos.

### Video

| Resolución | Códec | Contenedor |
|-----------|-------|------------|
| ≤ 1080p (480p · 720p · 1080p) | H.264 + AAC | `.mp4` |
| > 1080p (1440p · 2160p) | VP9 o AV1 + audio | `.mkv` |

- Las resoluciones hasta 1080p usan **H.264 + AAC en MP4** para compatibilidad con QuickTime, iOS y Smart TVs.
- Las resoluciones superiores solo existen en VP9/AV1, así que se entregan en **MKV** (requiere un reproductor moderno como VLC).
- Cada opción de video muestra el **tamaño estimado** antes de descargar.
- Video y audio se descargan por separado (así los sirve YouTube en ≥ 480p) y se unen automáticamente con ffmpeg.
- Los archivos se guardan en la carpeta `media/` dentro del proyecto (se crea automáticamente).

## Aviso legal

Ver sección de [propiedad intelectual en el release v1.0.0](https://github.com/vicvinue/yt-pydownloader/releases/tag/v1.0.0).
