#!/usr/bin/env python3
"""YT-Downloader — Web UI"""
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

# ── bootstrap ─────────────────────────────────────────────────────────────────

def _ensure_deno():
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
        return
    url      = f"https://github.com/denoland/deno/releases/latest/download/deno-{target}.zip"
    zip_path = os.path.join(VENV_DIR, "_deno_tmp.zip")
    try:
        urllib.request.urlretrieve(url, zip_path)
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extract("deno.exe" if _IS_WIN else "deno", VENV_BIN)
        if not _IS_WIN:
            os.chmod(DENO_BIN, 0o755)
    except Exception:
        pass
    finally:
        if os.path.isfile(zip_path):
            os.remove(zip_path)

def _bootstrap():
    if sys.executable == VENV_PY or sys.executable.startswith(VENV_DIR):
        return

    if not os.path.isdir(VENV_DIR):
        print("Configurando entorno (primera vez)...", flush=True)
        subprocess.check_call(
            [sys.executable, "-m", "venv", VENV_DIR],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )

    try:
        subprocess.check_call(
            [VENV_PY, "-c", "import yt_dlp; import imageio_ffmpeg; import flask"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
    except subprocess.CalledProcessError:
        print("Instalando dependencias...", flush=True)
        subprocess.check_call(
            [VENV_PY, "-m", "pip", "install", "--quiet", "--disable-pip-version-check",
             "yt-dlp", "imageio-ffmpeg", "flask"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )

    _ensure_deno()

    env = os.environ.copy()
    env["PATH"] = VENV_BIN + os.pathsep + env.get("PATH", "")
    os.execve(VENV_PY, [VENV_PY] + sys.argv, env)

_bootstrap()

# ── imports (inside venv) ─────────────────────────────────────────────────────

import yt_dlp
import imageio_ffmpeg
import threading
import queue
import uuid
import json
import webbrowser
from flask import Flask, request, jsonify, Response

# ── app setup ─────────────────────────────────────────────────────────────────

app        = Flask(__name__)
FFMPEG_BIN = imageio_ffmpeg.get_ffmpeg_exe()
EXTRA_OPTS = {"remote_components": "ejs:github"}
MEDIA_DIR  = os.path.join(SCRIPT_DIR, "media")
os.makedirs(MEDIA_DIR, exist_ok=True)
_jobs: dict = {}

class _SilentLogger:
    def debug(self, msg):   pass
    def info(self, msg):    pass
    def warning(self, msg): pass
    def error(self, msg):   pass

_SILENT = {
    "quiet": True, "no_warnings": True, "noprogress": True,
    "logger": _SilentLogger(), "ffmpeg_location": FFMPEG_BIN,
}

# ── HTML ──────────────────────────────────────────────────────────────────────

HTML = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>YT-Downloader</title>
<link rel="icon" type="image/svg+xml" href="/icon.svg">
<style>
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

  body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    background: #f3f4f6;
    color: #111827;
    min-height: 100vh;
    display: flex;
    flex-direction: column;
    align-items: center;
    padding: 2.5rem 1rem 5rem;
  }

  header {
    text-align: center;
    margin-bottom: 2rem;
  }

  .logo {
    width: 56px;
    height: 56px;
    background: #ef4444;
    border-radius: 14px;
    display: flex;
    align-items: center;
    justify-content: center;
    margin: 0 auto 0.75rem;
    box-shadow: 0 4px 12px rgba(239,68,68,.35);
  }

  .logo svg { fill: white; }

  header h1 {
    font-size: 1.5rem;
    font-weight: 700;
    letter-spacing: -0.02em;
  }

  header p {
    color: #6b7280;
    font-size: 0.875rem;
    margin-top: 0.2rem;
  }

  .container {
    width: 100%;
    max-width: 540px;
    display: flex;
    flex-direction: column;
    gap: 0.875rem;
  }

  .card {
    background: white;
    border-radius: 14px;
    padding: 1.25rem 1.375rem;
    box-shadow: 0 1px 3px rgba(0,0,0,.07), 0 1px 2px rgba(0,0,0,.04);
    animation: fadeIn .2s ease;
  }

  @keyframes fadeIn {
    from { opacity: 0; transform: translateY(6px); }
    to   { opacity: 1; transform: translateY(0); }
  }

  /* ── url row ── */
  .url-row {
    display: flex;
    gap: 0.5rem;
  }

  input[type="text"] {
    flex: 1;
    padding: 0.6rem 0.875rem;
    border: 1.5px solid #e5e7eb;
    border-radius: 9px;
    font-size: 0.875rem;
    outline: none;
    transition: border-color .15s;
    min-width: 0;
  }

  input[type="text"]:focus { border-color: #3b82f6; }
  input[type="text"]::placeholder { color: #9ca3af; }

  button {
    padding: 0.6rem 1.1rem;
    border: none;
    border-radius: 9px;
    font-size: 0.875rem;
    font-weight: 600;
    cursor: pointer;
    transition: background .15s, opacity .15s;
    white-space: nowrap;
  }
  button:disabled { opacity: .45; cursor: not-allowed; }

  .btn-primary { background: #2563eb; color: white; }
  .btn-primary:hover:not(:disabled) { background: #1d4ed8; }

  .btn-dl {
    background: #16a34a;
    color: white;
    width: 100%;
    padding: 0.75rem;
    margin-top: 1rem;
    font-size: 0.9375rem;
  }
  .btn-dl:hover:not(:disabled) { background: #15803d; }

  .btn-ghost {
    background: #f3f4f6;
    color: #374151;
    margin-top: 0.75rem;
  }
  .btn-ghost:hover { background: #e5e7eb; }

  /* ── error ── */
  .error-box {
    margin-top: 0.75rem;
    padding: 0.625rem 0.875rem;
    background: #fef2f2;
    border: 1px solid #fecaca;
    border-radius: 8px;
    font-size: 0.8125rem;
    color: #dc2626;
    line-height: 1.4;
  }

  /* ── loading ── */
  .loading-row {
    display: flex;
    align-items: center;
    gap: 0.625rem;
    color: #6b7280;
    font-size: 0.875rem;
  }

  /* ── video info ── */
  .video-row {
    display: flex;
    gap: 0.875rem;
    align-items: flex-start;
  }

  .thumb-wrap {
    flex-shrink: 0;
    width: 112px;
    height: 63px;
    border-radius: 7px;
    overflow: hidden;
    background: #f3f4f6;
  }

  .thumb-wrap img {
    width: 100%;
    height: 100%;
    object-fit: cover;
  }

  .video-meta h2 {
    font-size: 0.9rem;
    font-weight: 600;
    line-height: 1.45;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
  }

  .video-meta .dur {
    margin-top: 0.3rem;
    font-size: 0.8rem;
    color: #6b7280;
  }

  .divider {
    border: none;
    border-top: 1px solid #f3f4f6;
    margin: 1rem 0;
  }

  /* ── formats ── */
  .section-label {
    display: flex;
    align-items: center;
    gap: 0.4rem;
    font-size: 0.8rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: .06em;
    color: #9ca3af;
    margin-bottom: 0.75rem;
  }
  .section-label svg { width: 16px; height: 16px; fill: currentColor; }

  .fmt-cols { display: flex; gap: 1.25rem; align-items: flex-start; }
  .fmt-col  { flex: 1; min-width: 0; }
  @media (max-width: 640px) { .fmt-cols { flex-direction: column; gap: 1rem; } }

  .format-list {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
  }

  .format-opt {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    padding: 0.75rem 0.875rem;
    border: 1.5px solid #e5e7eb;
    border-radius: 14px;
    cursor: pointer;
    transition: border-color .12s, background .12s;
    user-select: none;
  }

  .format-opt:hover { background: #f9fafb; border-color: #d1d5db; }

  .format-opt.sel { border-color: #3b82f6; background: #eff6ff; }

  .rdot {
    width: 18px;
    height: 18px;
    border-radius: 50%;
    border: 2px solid #d1d5db;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
    transition: border-color .12s;
  }

  .format-opt.sel .rdot { border-color: #3b82f6; }

  .rdot::after {
    content: "";
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: #3b82f6;
    opacity: 0;
    transition: opacity .12s;
  }

  .format-opt.sel .rdot::after { opacity: 1; }

  .fmt-text  { flex: 1; min-width: 0; }
  .fmt-title { font-size: 0.95rem; font-weight: 700; color: #111827; }
  .fmt-sub   { font-size: 0.8rem; color: #9ca3af; margin-top: 1px; }

  .badge {
    flex-shrink: 0;
    padding: 0.3rem 0.7rem;
    border-radius: 9px;
    font-size: 0.72rem;
    font-weight: 700;
    letter-spacing: .03em;
    color: #fff;
  }
  .badge--gray   { background: #6b7280; }
  .badge--blue   { background: #3b82f6; }
  .badge--green  { background: #34d399; }
  .badge--indigo { background: #6366f1; }
  .badge--purple { background: #a855f7; }

  /* ── progress ── */
  .prog-title {
    font-size: 0.875rem;
    font-weight: 600;
    margin-bottom: 0.875rem;
    color: #374151;
  }

  .prog-row {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    margin-bottom: 0.3rem;
  }

  .prog-phase {
    font-size: 0.78rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: .06em;
    color: #6b7280;
  }

  .prog-pct {
    font-size: 0.8125rem;
    font-weight: 700;
    color: #111827;
  }

  .track {
    width: 100%;
    height: 7px;
    background: #e5e7eb;
    border-radius: 99px;
    overflow: hidden;
  }

  .fill {
    height: 100%;
    background: linear-gradient(90deg, #3b82f6, #60a5fa);
    border-radius: 99px;
    transition: width .35s ease;
    width: 0%;
  }

  .fill.indeterminate {
    width: 35% !important;
    animation: slide 1.3s ease-in-out infinite;
  }

  @keyframes slide {
    0%   { transform: translateX(-150%); }
    100% { transform: translateX(400%); }
  }

  .prog-stats {
    margin-top: 0.35rem;
    font-size: 0.75rem;
    color: #9ca3af;
  }

  .pp-row {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    margin-top: 0.875rem;
    font-size: 0.8125rem;
    color: #6b7280;
  }

  /* ── done ── */
  .done-wrap {
    text-align: center;
    padding: 1rem 0 0.25rem;
  }

  .done-icon {
    width: 52px;
    height: 52px;
    background: #dcfce7;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    margin: 0 auto 0.75rem;
  }

  .done-icon svg { fill: #16a34a; }

  .done-title { font-size: 1rem; font-weight: 700; }
  .done-sub   { font-size: 0.8125rem; color: #6b7280; margin-top: 0.3rem; }

  /* ── spinner ── */
  .spin {
    width: 15px;
    height: 15px;
    border: 2px solid #e5e7eb;
    border-top-color: #3b82f6;
    border-radius: 50%;
    flex-shrink: 0;
    animation: rot .7s linear infinite;
  }

  @keyframes rot { to { transform: rotate(360deg); } }

  .hidden { display: none !important; }

  /* ── footer ── */
  footer {
    position: fixed;
    bottom: 0;
    left: 0;
    right: 0;
    background: white;
    border-top: 1px solid #e5e7eb;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 1rem;
    padding: 0.625rem 1rem;
    z-index: 100;
  }

  .footer-link {
    display: flex;
    align-items: center;
    gap: 0.375rem;
    font-size: 0.8rem;
    color: #6b7280;
    text-decoration: none;
    transition: color .15s;
  }

  .footer-link:hover { color: #111827; }

  .footer-link svg { flex-shrink: 0; }

  .footer-divider {
    width: 1px;
    height: 14px;
    background: #d1d5db;
  }

  .footer-copy {
    font-size: 0.8rem;
    color: #9ca3af;
  }
</style>
</head>
<body>

<header>
  <div class="logo">
    <!-- App icon -->
    <svg width="32" height="32" viewBox="0 0 626 626"><path d="M162.6,520.8l-.3-298-94.9,54.2c-6.2,3.5-11.3,7.2-15.7,12.6-11.3,16.3-6,38.6,11.5,48.1l83.9,48v34.7s-101.9-58.8-101.9-58.8c-17.9-11-28.8-29.1-29.4-50.2-.8-23.6,10.9-45.7,31.5-57.6l115.3-66.3.2-100.6c0-23.2,19-40.7,41.5-42.9,11.7-.6,22.4,2.8,32.5,8.9l67,40.4,93.4,55.5,74.3,43.7v-104.8c0-11.6-7-21-17.1-25.7-7.9-3.3-16.1-2.5-23.7,1.5l-70.3,39.9-29.4-17.3,83.4-46.9c22.1-14,49.3-11.4,68.8,6.2,8.9,9.6,16.4,21.8,16.4,35.9l.4,127.7,85.6,49.3c10.3,6,17.8,14.5,22.2,25.5,7.6,22.7-1.3,47.8-22.4,59.9l-85.8,49-171.5,97.7,80.2,45.5,18,9.6c12.2,5,25.7,3.7,35.5-5.5s9.3-11.3,9.3-18.8v-84.8c.1,0,29-16.4,29-16.4v101.9c0,25.5-15.6,46.7-39.4,55-16.8,5.8-34.2,4.4-50-4.2l-57-32.6-56.5-32.7-79.2,44.4c-10.8,6-22.4,5.4-33.5,1-10.8-6.4-21.7-17.6-21.7-32Z"/></svg>
  </div>
  <h1>YT-Downloader</h1>
  <p>Descarga videos y audio de YouTube</p>
</header>

<div class="container">

  <!-- URL input -->
  <div class="card">
    <div class="url-row">
      <input type="text" id="url-input"
             placeholder="https://www.youtube.com/watch?v=..."
             autocomplete="off" spellcheck="false">
      <button class="btn-primary" id="search-btn" onclick="fetchInfo()">Buscar</button>
    </div>
    <div id="error-box" class="error-box hidden"></div>
  </div>

  <!-- Loading -->
  <div class="card hidden" id="loading-card">
    <div class="loading-row">
      <div class="spin"></div>
      <span>Obteniendo informacion del video...</span>
    </div>
  </div>

  <!-- Info + formats -->
  <div class="card hidden" id="info-card">
    <div class="video-row">
      <div class="thumb-wrap">
        <img id="thumb" src="" alt="">
      </div>
      <div class="video-meta">
        <h2 id="vtitle"></h2>
        <div class="dur" id="vdur"></div>
      </div>
    </div>

    <hr class="divider">

    <div class="fmt-cols">
      <div class="fmt-col">
        <div class="section-label">
          <svg viewBox="0 0 24 24"><path d="M12 3v10.55A4 4 0 1 0 14 17V7h4V3h-6z"/></svg>
          Audio
        </div>
        <div class="format-list" id="audio-list"></div>
      </div>
      <div class="fmt-col">
        <div class="section-label">
          <svg viewBox="0 0 24 24"><path d="M17 10.5V7a1 1 0 0 0-1-1H4a1 1 0 0 0-1 1v10a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1v-3.5l4 4v-11l-4 4z"/></svg>
          Video
        </div>
        <div class="format-list" id="video-list"></div>
      </div>
    </div>

    <button class="btn-dl" id="dl-btn" onclick="startDownload()" disabled>
      Descargar
    </button>
  </div>

  <!-- Progress -->
  <div class="card hidden" id="prog-card">
    <div class="prog-title" id="prog-title">Descargando...</div>
    <div class="prog-row">
      <span class="prog-phase" id="prog-phase">iniciando</span>
      <span class="prog-pct"  id="prog-pct"></span>
    </div>
    <div class="track"><div class="fill" id="fill"></div></div>
    <div class="prog-stats" id="prog-stats"></div>
    <div class="pp-row hidden" id="pp-row">
      <div class="spin"></div>
      <span id="pp-text"></span>
    </div>
  </div>

  <!-- Done -->
  <div class="card hidden" id="done-card">
    <div class="done-wrap">
      <div class="done-icon">
        <svg width="26" height="26" viewBox="0 0 24 24"><path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z"/></svg>
      </div>
      <div class="done-title">Descarga completada</div>
      <div class="done-sub">El archivo se guardo en la carpeta <strong>media/</strong>.</div>
      <button class="btn-ghost" onclick="reset()">Descargar otro</button>
    </div>
  </div>

</div>

<footer>
  <span class="footer-copy">© 2026 vicvinue</span>
  <div class="footer-divider"></div>
  <a class="footer-link" href="https://github.com/vicvinue" target="_blank" rel="noopener">
    <svg width="15" height="15" viewBox="0 0 24 24" fill="currentColor">
      <path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0 0 24 12c0-6.63-5.37-12-12-12z"/>
    </svg>
    GitHub
  </a>
  <div class="footer-divider"></div>
  <a class="footer-link" href="https://www.paypal.com/donate/?business=DKBNN7D7E2Q96&no_recurring=1&currency_code=USD" target="_blank" rel="noopener">
    <svg width="15" height="15" viewBox="0 0 24 24" fill="currentColor">
      <path d="M7.076 21.337H2.47a.641.641 0 0 1-.633-.74L4.944.901C5.026.382 5.474 0 5.998 0h7.46c2.57 0 4.578.543 5.69 1.81 1.01 1.15 1.304 2.42 1.012 4.287-.023.143-.047.288-.077.437-.983 5.05-4.349 6.797-8.647 6.797h-2.19c-.524 0-.968.382-1.05.9l-1.12 7.106zm14.146-14.42a3.35 3.35 0 0 0-.607-.541c-.013.076-.026.175-.041.254-.93 4.778-4.005 7.201-9.138 7.201h-2.19a.563.563 0 0 0-.556.479l-1.187 7.527h-.506l-.24 1.516a.56.56 0 0 0 .554.647h3.882c.46 0 .85-.334.922-.788.06-.26.76-4.852.816-5.09a.932.932 0 0 1 .923-.788h.58c3.76 0 6.705-1.528 7.565-5.946.36-1.847.174-3.388-.777-4.471z"/>
    </svg>
    Donar con PayPal
  </a>
</footer>

<script>
  let currentUrl = "";
  let selectedFmt = "";
  let evtSrc = null;

  const urlInput   = document.getElementById("url-input");
  const searchBtn  = document.getElementById("search-btn");
  const errorBox   = document.getElementById("error-box");
  const loadingCard = document.getElementById("loading-card");
  const infoCard   = document.getElementById("info-card");
  const progCard   = document.getElementById("prog-card");
  const doneCard   = document.getElementById("done-card");

  urlInput.addEventListener("keydown", e => { if (e.key === "Enter") fetchInfo(); });

  function showCards(...ids) {
    ["loading-card","info-card","prog-card","done-card"]
      .forEach(id => document.getElementById(id).classList.add("hidden"));
    ids.forEach(id => document.getElementById(id).classList.remove("hidden"));
  }

  function setError(msg) {
    if (msg) { errorBox.textContent = msg; errorBox.classList.remove("hidden"); }
    else      { errorBox.classList.add("hidden"); }
  }

  const YT_RE = /^https?:\/\/(www\.|m\.|music\.)?(youtube\.com\/(watch\?.*v=[\w-]+|shorts\/[\w-]+|live\/[\w-]+|embed\/[\w-]+|v\/[\w-]+|playlist\?.*list=[\w-]+)|youtu\.be\/[\w-]+)/i;

  async function fetchInfo() {
    const url = urlInput.value.trim();
    if (!url) { setError("Ingresa una URL de YouTube."); return; }
    if (!YT_RE.test(url)) { setError("El enlace no parece ser de YouTube. Formatos válidos: youtube.com/watch, youtu.be, /shorts, /live, /playlist."); return; }

    setError(null);
    searchBtn.disabled = true;
    showCards("loading-card");

    try {
      const res  = await fetch("/info", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Error desconocido");

      currentUrl  = url;
      selectedFmt = "";

      document.getElementById("thumb").src   = data.thumbnail || "";
      document.getElementById("vtitle").textContent = data.title;
      const meta = ["⏱ " + data.duration, data.channel, data.views].filter(Boolean).join("  ·  ");
      document.getElementById("vdur").textContent = meta;

      const render = (containerId, items) => {
        const list = document.getElementById(containerId);
        list.innerHTML = "";
        items.forEach(opt => {
          const el = document.createElement("div");
          el.className = "format-opt";
          const badge = opt.badge
            ? `<div class="badge badge--${opt.color}">${opt.badge}</div>` : "";
          el.innerHTML =
            `<div class="rdot"></div>` +
            `<div class="fmt-text"><div class="fmt-title">${opt.title}</div>` +
            `<div class="fmt-sub">${opt.subtitle}</div></div>` + badge;
          el.addEventListener("click", () => selectFmt(el, opt.key));
          list.appendChild(el);
        });
      };
      render("audio-list", data.audio || []);
      render("video-list", data.video || []);

      document.getElementById("dl-btn").disabled = true;
      showCards("info-card");
    } catch (e) {
      setError(e.message);
      showCards();
    } finally {
      searchBtn.disabled = false;
    }
  }

  function selectFmt(el, key) {
    document.querySelectorAll(".format-opt").forEach(o => o.classList.remove("sel"));
    el.classList.add("sel");
    selectedFmt = key;
    document.getElementById("dl-btn").disabled = false;
  }

  async function startDownload() {
    if (!selectedFmt) return;

    // reset progress UI
    document.getElementById("fill").className = "fill";
    document.getElementById("fill").style.width = "0%";
    document.getElementById("prog-phase").textContent = "iniciando";
    document.getElementById("prog-pct").textContent   = "";
    document.getElementById("prog-stats").textContent  = "";
    document.getElementById("prog-title").textContent  = "Descargando...";
    document.getElementById("pp-row").classList.add("hidden");

    showCards("prog-card");

    const res  = await fetch("/download", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url: currentUrl, choice: selectedFmt }),
    });
    const data = await res.json();
    if (!res.ok) { setError(data.error); showCards("info-card"); return; }

    if (evtSrc) evtSrc.close();
    evtSrc = new EventSource("/progress/" + data.job_id);
    evtSrc.onmessage = e => handle(JSON.parse(e.data));
    evtSrc.onerror   = () => { evtSrc.close(); };
  }

  function handle(ev) {
    if (ev.type === "ping") return;

    if (ev.type === "progress") {
      const fill  = document.getElementById("fill");
      const phase = document.getElementById("prog-phase");
      const pct   = document.getElementById("prog-pct");
      const stats = document.getElementById("prog-stats");

      phase.textContent = ev.phase;

      if (ev.pct !== undefined) {
        fill.classList.remove("indeterminate");
        fill.style.width    = ev.pct + "%";
        pct.textContent     = ev.pct.toFixed(1) + "%";
        if (ev.tot_mb) {
          const spd = ev.speed_kb >= 1024
            ? (ev.speed_kb / 1024).toFixed(1) + " MB/s"
            : ev.speed_kb + " KB/s";
          stats.textContent = ev.dl_mb + " / " + ev.tot_mb + " MB  ·  " + spd;
        }
      } else {
        fill.classList.add("indeterminate");
        pct.textContent = "";
        const spd = ev.speed_kb >= 1024
          ? (ev.speed_kb / 1024).toFixed(1) + " MB/s"
          : ev.speed_kb + " KB/s";
        stats.textContent = ev.dl_mb + " MB descargados  ·  " + spd;
      }

      if (ev.done) {
        fill.classList.remove("indeterminate");
        fill.style.width = "100%";
        pct.textContent  = "100%";
        stats.textContent = "";
      }
    }

    if (ev.type === "postprocess") {
      document.getElementById("pp-row").classList.remove("hidden");
      document.getElementById("pp-text").textContent = ev.msg;
      document.getElementById("prog-title").textContent = ev.msg;
    }

    if (ev.type === "done") {
      evtSrc.close();
      showCards("done-card");
    }

    if (ev.type === "error") {
      evtSrc.close();
      setError(ev.msg);
      showCards("info-card");
    }
  }

  function reset() {
    urlInput.value = "";
    currentUrl = "";
    selectedFmt = "";
    setError(null);
    showCards();
  }
</script>
</body>
</html>"""

# ── routes ────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return HTML, 200, {"Content-Type": "text/html; charset=utf-8"}

@app.route("/icon.svg")
def icon_svg():
    with open(os.path.join(SCRIPT_DIR, "icon.svg"), "rb") as f:
        return Response(f.read(), mimetype="image/svg+xml")

@app.route("/info", methods=["POST"])
def route_info():
    url = (request.json or {}).get("url", "").strip()
    if not url:
        return jsonify({"error": "URL vacía"}), 400

    try:
        with yt_dlp.YoutubeDL({**_SILENT, **EXTRA_OPTS}) as ydl:
            info = ydl.extract_info(url, download=False)
    except Exception as e:
        return jsonify({"error": str(e)}), 400

    formats  = info.get("formats", [])
    duration = info.get("duration") or 0

    def _size(f):
        s = f.get("filesize") or f.get("filesize_approx")
        if s:
            return s
        tbr = f.get("tbr")
        return int(tbr * 1000 / 8 * duration) if (tbr and duration) else 0

    def _human_mb(num_bytes):
        return f"{num_bytes / 1_000_000:.1f} MB" if num_bytes else "—"

    # Mejor audio por tipo, para estimar el tamaño combinado de cada video.
    audio_only = [f for f in formats if f.get("vcodec") == "none" and f.get("acodec") != "none"]
    def _best_audio(pred):
        cands = [f for f in audio_only if pred(f)]
        return max(cands, key=lambda f: f.get("abr") or f.get("tbr") or 0) if cands else None
    m4a_sz  = _size(_best_audio(lambda f: f.get("ext") == "m4a") or {})
    opus_sz = _size(_best_audio(lambda f: f.get("acodec") == "opus") or {})

    heights    = sorted({f["height"] for f in formats
                         if f.get("height") and f.get("vcodec") != "none"})
    max_height = heights[-1] if heights else None

    def _video_size(h):
        cands = [f for f in formats if f.get("height") == h
                 and f.get("vcodec") != "none" and f.get("acodec") == "none"]
        if not cands:
            return 0
        avc  = [f for f in cands if (f.get("vcodec") or "").startswith("avc")]
        pool = avc if (h <= 1080 and avc) else cands
        return _size(max(pool, key=lambda f: f.get("tbr") or 0))

    def _badge(h):
        if h <= 480:  return ("SD",  "gray")
        if h <= 720:  return ("HD",  "blue")
        if h <= 1080: return ("FHD", "green")
        if h <= 1440: return ("2K",  "indigo")
        if h <= 2160: return ("4K",  "purple")
        return ("8K", "purple")

    def _human_views(n):
        if not n:                  return ""
        if n >= 1_000_000_000:     return f"{n/1_000_000_000:.1f}B vistas"
        if n >= 1_000_000:         return f"{n/1_000_000:.1f}M vistas"
        if n >= 1_000:             return f"{n/1_000:.0f}K vistas"
        return f"{n} vistas"

    audio = [
        {"key": "audio_opus", "title": "Opus", "subtitle": "Calidad original",    "badge": "HQ", "color": "green"},
        {"key": "audio_m4a",  "title": "M4A",  "subtitle": "Compatible con todo",  "badge": None, "color": None},
        {"key": "audio_mp3",  "title": "MP3",  "subtitle": "Para equipos antiguos","badge": None, "color": None},
    ]

    TIERS        = [480, 720, 1080, 1440, 2160, 4320]
    tier_heights = [h for h in TIERS if h in heights] or ([max_height] if max_height else [])
    video = []
    for h in tier_heights:
        badge, color = _badge(h)
        combined = _video_size(h) + (m4a_sz if h <= 1080 else (opus_sz or m4a_sz))
        video.append({"key": f"video_{h}", "title": f"{h}p",
                       "subtitle": _human_mb(combined), "badge": badge, "color": color})

    mins, secs = divmod(int(duration), 60)

    return jsonify({
        "title":     info.get("title", "Sin título"),
        "duration":  f"{mins}:{secs:02d}",
        "channel":   info.get("uploader") or info.get("channel") or "",
        "views":     _human_views(info.get("view_count")),
        "thumbnail": info.get("thumbnail"),
        "audio":     audio,
        "video":     video,
    })

@app.route("/download", methods=["POST"])
def route_download():
    data   = request.json or {}
    url    = data.get("url", "").strip()
    choice = data.get("choice", "").strip()
    if not url or not choice:
        return jsonify({"error": "Faltan parámetros"}), 400

    job_id = str(uuid.uuid4())
    q      = queue.Queue()
    _jobs[job_id] = q

    threading.Thread(target=_run_download, args=(url, choice, q), daemon=True).start()
    return jsonify({"job_id": job_id})

@app.route("/progress/<job_id>")
def route_progress(job_id):
    q = _jobs.get(job_id)
    if not q:
        return Response('data: {"type":"error","msg":"Job no encontrado"}\n\n',
                        content_type="text/event-stream")

    def generate():
        while True:
            try:
                ev = q.get(timeout=25)
                yield f"data: {json.dumps(ev)}\n\n"
                if ev.get("type") in ("done", "error"):
                    _jobs.pop(job_id, None)
                    break
            except queue.Empty:
                yield 'data: {"type":"ping"}\n\n'

    return Response(
        generate(),
        content_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )

# ── download worker ───────────────────────────────────────────────────────────

def _run_download(url: str, choice: str, q: queue.Queue):
    is_audio_only = choice.startswith("audio")
    phase_labels  = {1: "audio"} if is_audio_only else {1: "video", 2: "audio"}
    state = {"phase": 0, "last_file": None}

    def progress_hook(d):
        if d["status"] == "downloading":
            fname = d.get("filename", "")
            if fname != state["last_file"]:
                state["last_file"] = fname
                state["phase"] += 1

            label      = phase_labels.get(state["phase"], f"p{state['phase']}")
            downloaded = d.get("downloaded_bytes", 0)
            total      = d.get("total_bytes") or d.get("total_bytes_estimate", 0)
            speed      = d.get("speed") or 0

            ev = {
                "type":     "progress",
                "phase":    label,
                "dl_mb":    round(downloaded / 1_048_576, 1),
                "speed_kb": round(speed / 1024),
            }
            if total:
                ev["pct"]    = round(downloaded / total * 100, 1)
                ev["tot_mb"] = round(total / 1_048_576, 1)
            q.put(ev)

        elif d["status"] == "finished":
            label = phase_labels.get(state["phase"], f"p{state['phase']}")
            q.put({"type": "progress", "phase": label, "pct": 100.0, "done": True})

    def postprocessor_hook(d):
        msgs = {"Merger": "Uniendo video y audio...", "ExtractAudio": "Convirtiendo audio..."}
        msg  = msgs.get(d.get("postprocessor", ""))
        if msg and d["status"] == "started":
            q.put({"type": "postprocess", "msg": msg})

    base_opts = {
        **_SILENT, **EXTRA_OPTS,
        "outtmpl":             os.path.join(MEDIA_DIR, "%(title)s.%(ext)s"),
        "noplaylist":          True,
        "progress_hooks":      [progress_hook],
        "postprocessor_hooks": [postprocessor_hook],
    }

    if choice == "audio_mp3":
        opts = {**base_opts, "format": "bestaudio/best",
                "postprocessors": [{"key": "FFmpegExtractAudio",
                                    "preferredcodec": "mp3", "preferredquality": "0"}]}
    elif choice == "audio_m4a":
        # Prefiere el stream AAC nativo de YouTube; si la fuente ya es AAC ffmpeg solo copia (sin pérdida).
        opts = {**base_opts, "format": "bestaudio[ext=m4a]/bestaudio/best",
                "postprocessors": [{"key": "FFmpegExtractAudio",
                                    "preferredcodec": "m4a", "preferredquality": "0"}]}
    elif choice == "audio_opus":
        # Opus nativo de YouTube (mejor calidad por bit); si la fuente ya es Opus ffmpeg solo copia.
        opts = {**base_opts, "format": "bestaudio[acodec=opus]/bestaudio/best",
                "postprocessors": [{"key": "FFmpegExtractAudio",
                                    "preferredcodec": "opus", "preferredquality": "0"}]}
    elif choice == "video_original":
        opts = {**base_opts, "format": "bestvideo+bestaudio/best", "merge_output_format": "mkv"}
    else:
        h = int(choice.split("_")[1])
        if h <= 1080:
            # H.264 + AAC en MP4 para máxima compatibilidad (QuickTime, iOS, Smart TVs).
            opts = {
                **base_opts,
                "format": (f"bestvideo[height<={h}][vcodec^=avc]+bestaudio[ext=m4a]"
                           f"/bestvideo[height<={h}][ext=mp4]+bestaudio[ext=m4a]"
                           f"/bestvideo[height<={h}]+bestaudio/best[height<={h}]"),
                "merge_output_format": "mp4",
            }
        else:
            # >1080 solo existe en VP9/AV1 (sin H.264) → MKV, que admite Opus.
            opts = {
                **base_opts,
                "format": f"bestvideo[height<={h}]+bestaudio/best[height<={h}]",
                "merge_output_format": "mkv",
            }

    try:
        null_fd   = os.open(os.devnull, os.O_WRONLY)
        saved_err = os.dup(2)
        os.dup2(null_fd, 2)
        os.close(null_fd)
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                ydl.download([url])
        finally:
            os.dup2(saved_err, 2)
            os.close(saved_err)
        q.put({"type": "done"})
    except Exception as e:
        q.put({"type": "error", "msg": str(e)})

# ── entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    PORT = 7788
    print(f"\nYT-Downloader  →  http://localhost:{PORT}")
    print("Ctrl+C para salir\n")
    threading.Timer(1.1, lambda: webbrowser.open(f"http://localhost:{PORT}")).start()
    app.run(host="127.0.0.1", port=PORT, debug=False, threaded=True, use_reloader=False)
