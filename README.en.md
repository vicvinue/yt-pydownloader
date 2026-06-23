# yt-pydownloader

[Español](README.md) | **English**

YouTube downloader with an interactive menu. Lets you download audio (MP3/WAV) and video (720p, 1080p, original quality) with a real-time progress bar.

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

| Option | Video codec | Audio codec | Container |
|--------|-------------|-------------|-----------|
| Audio MP3 | — | MP3 (highest quality) | .mp3 |
| Audio WAV | — | WAV (lossless) | .wav |
| Video 720p | H.264 | AAC | .mp4 |
| Video 1080p | H.264 | AAC | .mp4 |
| Video original | AV1 / VP9 | Opus | .mkv |

- The 720p and 1080p options use H.264 for compatibility with QuickTime and native players.
- The "original" option downloads the best available stream (usually AV1), more efficient but requires VLC or another modern player.
- Video and audio are downloaded separately (that's how YouTube serves resolutions ≥ 480p) and merged automatically with ffmpeg.
- Files are saved to the `media/` folder inside the project (created automatically).

## Legal notice

See the [intellectual property section in release v1.0.0](https://github.com/vicvinue/yt-pydownloader/releases/tag/v1.0.0).
