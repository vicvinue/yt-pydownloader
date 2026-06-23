# yt-pydownloader

[Español](README.md) | **English**

YouTube downloader with an interactive menu. Lets you download audio (Opus, M4A, MP3) and video (480p up to 2160p/4K) with a real-time progress bar.

## Requirements

**You only need Python 3.8 or newer.** Everything else is installed automatically the first time you run the script:

| Tool | Installation |
|---|---|
| Python 3.8+ | Manual (see below) |
| yt-dlp | Automatic |
| ffmpeg | Automatic (static binary included) |
| Deno | Automatic (downloaded if not present on the system) |

> **Windows:** download Python from [python.org](https://www.python.org/downloads/) and check **"Add Python to PATH"** during installation.

## Usage

### First run

On the first run, the script sets up the environment automatically:

```
Setting up environment (first time)...
Installing dependencies (yt-dlp, ffmpeg)...
Downloading Deno (JS runtime for YouTube)...
```

From the second run onwards it starts directly.

---

### Web interface (recommended)

Opens a UI in the browser at `http://localhost:7788`. Works the same on macOS, Linux and Windows.

**macOS / Linux**

```bash
python3 web.py
# or:
./run-web.sh
```

**Windows**

```bat
python web.py
rem or:
run-web.bat
```

The browser opens automatically. To stop the server press `Ctrl+C` in the terminal.

---

### Command-line interface

**macOS / Linux**

```bash
python3 downloader.py
# or:
./run.sh
```

**Windows**

```bat
python downloader.py
rem or:
run.bat
```

## Download options

### Audio

| Format | Codec | Container |
|--------|-------|-----------|
| **Opus** | Opus (native copy from YouTube) | `.opus` |
| **M4A** | AAC | `.m4a` |
| **MP3** | MP3 (VBR ~q0) | `.mp3` |

- **Opus** is the best quality per bit; if the source is already Opus it's extracted without re-encoding.
- **M4A** (AAC) is the maximum-compatibility option.
- **MP3** is re-encoded, intended for older devices.

### Video

| Resolution | Codec | Container |
|-----------|-------|-----------|
| ≤ 1080p (480p · 720p · 1080p) | H.264 + AAC | `.mp4` |
| > 1080p (1440p · 2160p) | VP9 or AV1 + audio | `.mkv` |

- Resolutions up to 1080p use **H.264 + AAC in MP4** for compatibility with QuickTime, iOS and Smart TVs.
- Higher resolutions only exist in VP9/AV1, so they're delivered in **MKV** (requires a modern player such as VLC).
- Each video option shows its **estimated size** before downloading.
- Video and audio are downloaded separately (that's how YouTube serves resolutions ≥ 480p) and merged automatically with ffmpeg.
- Files are saved to the `media/` folder inside the project (created automatically).

## Legal notice

See the [intellectual property section in release v1.0.0](https://github.com/vicvinue/yt-pydownloader/releases/tag/v1.0.0).
