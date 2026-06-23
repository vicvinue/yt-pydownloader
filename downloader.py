#!/usr/bin/env python3
import sys
import os
import subprocess
import platform

_IS_WIN    = platform.system() == "Windows"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
VENV_DIR   = os.path.join(SCRIPT_DIR, ".venv")
VENV_BIN   = os.path.join(VENV_DIR, "Scripts" if _IS_WIN else "bin")
VENV_PY    = os.path.join(VENV_BIN, "python.exe" if _IS_WIN else "python3")
DENO_BIN   = os.path.join(VENV_BIN, "deno.exe" if _IS_WIN else "deno")

def _ensure_deno():
    """Descarga el binario de Deno al venv si no está disponible en el sistema."""
    import shutil, urllib.request, zipfile

    if shutil.which("deno") or os.path.isfile(DENO_BIN):
        return

    targets = {
        ("Darwin",  "arm64"):   "aarch64-apple-darwin",
        ("Darwin",  "x86_64"):  "x86_64-apple-darwin",
        ("Linux",   "x86_64"):  "x86_64-unknown-linux-gnu",
        ("Linux",   "aarch64"): "aarch64-unknown-linux-gnu",
        ("Windows", "amd64"):   "x86_64-pc-windows-msvc",
        ("Windows", "x86_64"):  "x86_64-pc-windows-msvc",
    }
    key    = (platform.system(), platform.machine().lower())
    target = targets.get(key)
    if not target:
        print(f"Advertencia: plataforma {key} sin soporte para Deno.", flush=True)
        return

    url      = f"https://github.com/denoland/deno/releases/latest/download/deno-{target}.zip"
    zip_path = os.path.join(VENV_DIR, "_deno_tmp.zip")
    print("Descargando Deno (runtime JS para YouTube)...", flush=True)
    try:
        urllib.request.urlretrieve(url, zip_path)
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extract("deno.exe" if _IS_WIN else "deno", VENV_BIN)
        if not _IS_WIN:
            os.chmod(DENO_BIN, 0o755)
    except Exception as e:
        print(f"Advertencia: no se pudo instalar Deno ({e}). Algunos videos pueden fallar.", flush=True)
    finally:
        if os.path.isfile(zip_path):
            os.remove(zip_path)

def _bootstrap():
    """Si no estamos dentro del venv del proyecto, créalo y relanza el script en él."""
    if sys.executable == VENV_PY or sys.executable.startswith(VENV_DIR):
        return  # ya estamos en el venv correcto

    if not os.path.isdir(VENV_DIR):
        print("Configurando entorno (primera vez)...", flush=True)
        subprocess.check_call(
            [sys.executable, "-m", "venv", VENV_DIR],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )

    # Instalar dependencias Python si faltan
    try:
        subprocess.check_call(
            [VENV_PY, "-c", "import yt_dlp; import imageio_ffmpeg"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
    except subprocess.CalledProcessError:
        print("Instalando dependencias (yt-dlp, ffmpeg)...", flush=True)
        subprocess.check_call(
            [VENV_PY, "-m", "pip", "install", "--quiet", "--disable-pip-version-check",
             "yt-dlp", "imageio-ffmpeg"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )

    # Instalar Deno si falta
    _ensure_deno()

    # Pasar PATH con venv/bin incluido para que yt-dlp encuentre deno
    env = os.environ.copy()
    env["PATH"] = VENV_BIN + os.pathsep + env.get("PATH", "")
    os.execve(VENV_PY, [VENV_PY] + sys.argv, env)

_bootstrap()

import yt_dlp
import imageio_ffmpeg

FFMPEG_BIN  = imageio_ffmpeg.get_ffmpeg_exe()
MEDIA_DIR   = os.path.join(SCRIPT_DIR, "media")
os.makedirs(MEDIA_DIR, exist_ok=True)

PHASE_LABELS = {1: "video", 2: "audio"}

def make_progress_hook():
    # La barra tiene overhead fijo de ~45 chars (label + corchetes + stats).
    # Usamos get_terminal_size() para que nunca supere el ancho del terminal
    # y evitar el wrap que crea múltiples filas visibles.
    try:
        bar_width = max(10, os.get_terminal_size().columns - 45)
    except OSError:
        bar_width = 30

    state = {"last_file": None, "phase": 0, "needs_nl": False}

    def hook(d):
        if d["status"] == "downloading":
            filename = d.get("filename", "")
            if filename != state["last_file"]:
                if state["needs_nl"]:
                    sys.stdout.write("\n")
                    sys.stdout.flush()
                state["last_file"] = filename
                state["phase"] += 1
                state["needs_nl"] = False

            label  = PHASE_LABELS.get(state["phase"], f"p{state['phase']}")
            downloaded = d.get("downloaded_bytes", 0)
            total  = d.get("total_bytes") or d.get("total_bytes_estimate", 0)
            speed  = d.get("speed") or 0

            if total:
                pct    = downloaded / total
                filled = int(bar_width * pct)
                bar    = "█" * filled + "░" * (bar_width - filled)
                dl_mb  = downloaded / 1_048_576
                tot_mb = total / 1_048_576
                spd_kb = speed / 1024
                line   = f"\r\033[2K  {label} [{bar}] {pct*100:5.1f}%  {dl_mb:.1f}/{tot_mb:.1f}MB  {spd_kb:.0f}KB/s"
            else:
                dl_mb  = downloaded / 1_048_576
                spd_kb = speed / 1024
                spinner = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
                tick    = (downloaded // 65536) % len(spinner)
                line    = f"\r\033[2K  {label} {spinner[tick]} {dl_mb:.1f}MB  {spd_kb:.0f}KB/s"

            sys.stdout.write(line)
            sys.stdout.flush()
            state["needs_nl"] = True

        elif d["status"] == "finished":
            try:
                bar_width_now = max(10, os.get_terminal_size().columns - 45)
            except OSError:
                bar_width_now = bar_width
            label = PHASE_LABELS.get(state["phase"], f"p{state['phase']}")
            sys.stdout.write(f"\r\033[2K  {label} [{'█' * bar_width_now}] 100%  listo\n")
            sys.stdout.flush()
            state["needs_nl"] = False

    return hook

PP_MESSAGES = {
    "Merger":       "  uniendo video y audio...",
    "ExtractAudio": "  convirtiendo audio...",
}
_pp_shown = set()

def postprocessor_hook(d):
    name = d.get("postprocessor", "")
    msg  = PP_MESSAGES.get(name)
    if not msg:
        return
    if d["status"] == "started" and name not in _pp_shown:
        _pp_shown.add(name)
        sys.stdout.write(f"\r\033[2K{msg}")
        sys.stdout.flush()
    elif d["status"] == "finished" and name in _pp_shown:
        _pp_shown.discard(name)
        sys.stdout.write(f"\r\033[2K{msg} listo\n")
        sys.stdout.flush()

EXTRA_OPTS = {"remote_components": "ejs:github"}

class _SilentLogger:
    def debug(self, msg): pass
    def info(self, msg): pass
    def warning(self, msg): pass
    def error(self, msg): pass

_SILENT = {
    "quiet": True,
    "no_warnings": True,
    "noprogress": True,
    "logger": _SilentLogger(),
    "ffmpeg_location": FFMPEG_BIN,
}

def get_available_formats(url):
    ydl_opts = {**_SILENT, **EXTRA_OPTS}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)

    formats = info.get("formats", [])
    available_heights = set()
    for f in formats:
        h = f.get("height")
        if h and f.get("vcodec") != "none":
            available_heights.add(h)

    max_height = max(available_heights) if available_heights else None
    return info, available_heights, max_height

def build_menu(available_heights, max_height):
    options = []
    options.append(("audio_opus", "Audio Opus (calidad original)"))
    options.append(("audio_m4a",  "Audio M4A (máxima compatibilidad)"))
    options.append(("audio_mp3",  "Audio MP3"))

    for res in [720, 1080]:
        if res in available_heights:
            options.append((f"video_{res}", f"Video {res}p con audio"))

    extra = sorted(h for h in available_heights if h > 1080)
    for h in extra:
        options.append((f"video_{h}", f"Video {h}p con audio"))

    if max_height and max_height not in {720, 1080}:
        options.append(("video_original", f"Video calidad original ({max_height}p, mejor disponible) con audio"))
    elif max_height:
        options.append(("video_original", f"Video calidad original (AV1/{max_height}p, menor tamaño) con audio"))

    return options

def download(url, choice):
    base_opts = {
        **_SILENT,
        **EXTRA_OPTS,
        "outtmpl": os.path.join(MEDIA_DIR, "%(title)s.%(ext)s"),
        "noplaylist": True,
        "progress_hooks": [make_progress_hook()],
        "postprocessor_hooks": [postprocessor_hook],
    }

    if choice == "audio_opus":
        # Opus nativo de YouTube (mejor calidad por bit); si la fuente ya es Opus ffmpeg solo copia.
        opts = {
            **base_opts,
            "format": "bestaudio[acodec=opus]/bestaudio/best",
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "opus",
                "preferredquality": "0",
            }],
        }
    elif choice == "audio_m4a":
        # AAC nativo; si la fuente ya es AAC ffmpeg solo copia (sin pérdida).
        opts = {
            **base_opts,
            "format": "bestaudio[ext=m4a]/bestaudio/best",
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "m4a",
                "preferredquality": "0",
            }],
        }
    elif choice == "audio_mp3":
        opts = {
            **base_opts,
            "format": "bestaudio/best",
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "0",
            }],
        }
    elif choice == "video_original":
        opts = {
            **base_opts,
            "format": "bestvideo+bestaudio/best",
            "merge_output_format": "mkv",
        }
    else:
        h = int(choice.split("_")[1])
        if h <= 1080:
            # H.264 + AAC en MP4 para máxima compatibilidad (QuickTime, iOS, Smart TVs).
            opts = {
                **base_opts,
                "format": (
                    f"bestvideo[height<={h}][vcodec^=avc]+bestaudio[ext=m4a]"
                    f"/bestvideo[height<={h}][ext=mp4]+bestaudio[ext=m4a]"
                    f"/bestvideo[height<={h}]+bestaudio/best[height<={h}]"
                ),
                "merge_output_format": "mp4",
            }
        else:
            # >1080 solo existe en VP9/AV1 (sin H.264) → MKV, que admite Opus.
            opts = {
                **base_opts,
                "format": f"bestvideo[height<={h}]+bestaudio/best[height<={h}]",
                "merge_output_format": "mkv",
            }

    # Silenciar stderr a nivel de fd para que nada rompa la barra de progreso
    null_fd    = os.open(os.devnull, os.O_WRONLY)
    saved_err  = os.dup(2)
    os.dup2(null_fd, 2)
    os.close(null_fd)
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([url])
    finally:
        sys.stdout.flush()
        os.dup2(saved_err, 2)
        os.close(saved_err)

def main():
    print("=" * 52)
    print("               YT-Downloader")
    print("=" * 52)

    url = input("\nIngresa el enlace de YouTube: ").strip()
    if not url:
        print("URL vacía. Saliendo.")
        sys.exit(1)

    print("\nObteniendo información del video...")
    try:
        info, available_heights, max_height = get_available_formats(url)
    except Exception as e:
        print(f"Error al obtener el video: {e}")
        sys.exit(1)

    title = info.get("title", "Sin título")
    duration = info.get("duration", 0)
    mins, secs = divmod(duration, 60)
    print(f"\nTítulo  : {title}")
    print(f"Duración: {mins}:{secs:02d}")

    options = build_menu(available_heights, max_height)

    print("\nOpciones de descarga disponibles:")
    for i, (_, label) in enumerate(options, 1):
        print(f"  {i}) {label}")
    print("  0) Salir")

    while True:
        try:
            sel = int(input("\nElige una opción: "))
        except ValueError:
            print("Ingresa un número válido.")
            continue
        if sel == 0:
            print("Saliendo.")
            sys.exit(0)
        if 1 <= sel <= len(options):
            break
        print(f"Opción inválida. Elige entre 0 y {len(options)}.")

    choice_key, choice_label = options[sel - 1]
    print(f"\nDescargando: {choice_label}")
    print(f"Destino    : {MEDIA_DIR}\n")

    try:
        download(url, choice_key)
        print(f"\nDescarga completada.")
    except Exception as e:
        print(f"\nError durante la descarga: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
