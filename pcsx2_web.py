"""Launcher WEB local para o PCSX2 (Python 3, biblioteca padrao).

Abre uma pagina em http://127.0.0.1:8765 para gerenciar jogos e iniciar o PCSX2.
Recursos:
- Interface moderna estilo Steam/Console com grid de capas
- Busca em tempo real
- Escaneamento automatico de pastas de ISOs/CHDs
- Autodeteccao de caminhos comuns do PCSX2 (Windows e Linux)
- Download em segundo plano do Google Drive (requer: pip install gdown)
- Busca automatica de capas oficiais no repositorio Libretro Thumbnails
"""

import difflib
import json
import os
import platform
import re
import secrets
import shutil
import subprocess
import sys
import threading
import time
import urllib.parse
import urllib.request
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent
CONFIG = Path.home() / ".pcsx2_launcher.json"
CACHE = HERE / "isos"
PORT = 8765
COVERS = HERE / "covers"
LIBRETRO = "https://thumbnails.libretro.com/Sony%20-%20PlayStation%202/Named_Boxarts/"
TOKEN = "pcsx2-token"
SUPPORTED_EXTENSIONS = {".iso", ".chd", ".bin", ".cso", ".gz", ".mdf", ".img"}

jobs = {}
lock = threading.Lock()


def auto_detect_pcsx2():
    system = platform.system()
    candidates = []

    # Pasta local relativa
    if (HERE / "pcsx2").exists():
        found = next((HERE / "pcsx2").rglob("pcsx2-qt.exe"), None) or next((HERE / "pcsx2").rglob("pcsx2*.exe"), None)
        if found:
            candidates.append(str(found))

    if system == "Windows":
        prog_files = os.environ.get("ProgramFiles", r"C:\Program Files")
        prog_files_x86 = os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")
        local_appdata = os.environ.get("LocalAppData", "")
        win_candidates = [
            Path(prog_files) / "PCSX2" / "pcsx2-qt.exe",
            Path(prog_files_x86) / "PCSX2" / "pcsx2-qt.exe",
            Path(prog_files) / "PCSX2" / "pcsx2.exe",
            Path(local_appdata) / "Programs" / "PCSX2" / "pcsx2-qt.exe",
        ]
        for p in win_candidates:
            if p.exists():
                candidates.append(str(p))
    elif system == "Linux":
        # Flatpak check
        if shutil.which("flatpak"):
            try:
                res = subprocess.run(["flatpak", "info", "net.pcsx2.PCSX2"], capture_output=True, text=True)
                if res.returncode == 0:
                    candidates.append("flatpak:net.pcsx2.PCSX2")
            except Exception:
                pass
        for cmd in ["pcsx2-qt", "pcsx2"]:
            found = shutil.which(cmd)
            if found:
                candidates.append(found)

    return candidates[0] if candidates else ""


def load():
    try:
        d = json.loads(CONFIG.read_text(encoding="utf-8"))
    except Exception:
        d = {}
    d.setdefault("exe", "")
    d.setdefault("fullscreen", True)
    d.setdefault("games", [])

    # Autodeteccao se nao houver exe configurado ou se nao existir
    if not d["exe"] or (not d["exe"].startswith("flatpak:") and not Path(d["exe"]).exists()):
        detected = auto_detect_pcsx2()
        if detected:
            d["exe"] = detected
    return d


def save(d):
    CONFIG.write_text(json.dumps(d, indent=2, ensure_ascii=False), encoding="utf-8")


def _norm(name):
    name = re.sub(r"\([^)]*\)|\[[^\]]*\]", "", name)
    return re.sub(r"[^a-z0-9]+", " ", name.lower()).strip()[:80]


def _http(url):
    req = urllib.request.Request(url, headers={"User-Agent": "pcsx2-launcher"})
    with urllib.request.urlopen(req, timeout=15) as r:
        return r.read()


def cover_index():
    f = COVERS / "_index.json"
    if f.exists():
        try:
            return json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            pass
    try:
        html = _http(LIBRETRO).decode("utf-8", "replace")
        found = re.findall(r'href="([^"?/][^"]*\.png)"', html)
        names = sorted({urllib.parse.unquote(n) for n in found})
        if names:
            COVERS.mkdir(exist_ok=True)
            f.write_text(json.dumps(names), encoding="utf-8")
        return names
    except Exception:
        return []


def cover_for(name, force_refresh=False):
    COVERS.mkdir(exist_ok=True)
    key = _norm(name) or "x"
    png = COVERS / (key.replace(" ", "_") + ".png")
    miss = png.with_suffix(".none")

    if force_refresh:
        if png.exists():
            try:
                png.unlink()
            except Exception:
                pass
        if miss.exists():
            try:
                miss.unlink()
            except Exception:
                pass

    if png.exists():
        return png.read_bytes()
    if miss.exists():
        return None

    try:
        idx = cover_index()
        if not idx:
            return None
        by = {}
        for n in idx:
            by.setdefault(_norm(n[:-4]), []).append(n)
        best = difflib.get_close_matches(key, list(by), n=1, cutoff=0.55)
        if not best:
            miss.touch()
            return None
        opts = by[best[0]]
        # Prioriza versao USA ou En se disponivel
        pick = next((o for o in opts if "(USA" in o), next((o for o in opts if "(Europe" in o), opts[0]))
        data = _http(LIBRETRO + urllib.parse.quote(pick))
        png.write_bytes(data)
        return data
    except Exception:
        return None


def drive_job(job, url):
    try:
        import gdown
    except ImportError:
        jobs[job] = {"status": "error", "message": "Dependencia ausente: instale gdown com 'pip install gdown'"}
        return
    try:
        jobs[job] = {"status": "downloading", "message": "Iniciando download do Google Drive..."}
        CACHE.mkdir(exist_ok=True)
        out = gdown.download(url=url, output=str(CACHE) + os.sep, fuzzy=True, quiet=False)
        if not out:
            raise RuntimeError("Nao foi possivel baixar. Certifique-se de que o link e publico.")
        out_path = Path(out).resolve()
        with lock:
            d = load()
            if not any(g["path"] == str(out_path) for g in d["games"]):
                d["games"].append({
                    "name": out_path.stem,
                    "path": str(out_path),
                    "added_at": int(time.time()),
                    "last_played": None
                })
                save(d)
        jobs[job] = {"status": "completed", "message": f"Concluido: {out_path.name}"}
        # Limpa apos 8 segundos
        time.sleep(8)
        jobs.pop(job, None)
    except Exception as e:
        jobs[job] = {"status": "error", "message": f"Erro: {e}"}


def scan_directory(folder_path):
    p = Path(folder_path).resolve()
    if not p.is_dir():
        raise ValueError(f"O caminho '{folder_path}' nao e uma pasta valida.")
    
    found_files = []
    for item in p.rglob("*"):
        if item.is_file() and item.suffix.lower() in SUPPORTED_EXTENSIONS:
            found_files.append(item)
            
    with lock:
        d = load()
        existing_paths = {g["path"] for g in d["games"]}
        added_count = 0
        for f in found_files:
            abs_p = str(f.resolve())
            if abs_p not in existing_paths:
                d["games"].append({
                    "name": f.stem,
                    "path": abs_p,
                    "added_at": int(time.time()),
                    "last_played": None
                })
                existing_paths.add(abs_p)
                added_count += 1
        save(d)
    return added_count, len(found_files)


def play(d, i):
    exe = d.get("exe", "").strip()
    if not exe:
        return "Configure o executavel do PCSX2 nas configuracoes."
    
    try:
        game = d["games"][i]
    except IndexError:
        return "Indice de jogo invalido."
        
    game_path = game["path"]
    if not Path(game_path).exists():
        return f"Arquivo do jogo nao encontrado em: {game_path}"

    flag = "-fullscreen" if d.get("fullscreen", True) else "-nofullscreen"

    # Atualiza last_played
    game["last_played"] = int(time.time())
    save(d)

    try:
        if exe.startswith("flatpak:"):
            app_id = exe.split(":", 1)[1]
            cmd = ["flatpak", "run", app_id, "-batch", flag, "--", game_path]
        else:
            if not Path(exe).exists():
                return f"Executavel PCSX2 nao encontrado em: {exe}"
            cmd = [exe, "-batch", flag, "--", game_path]
        subprocess.Popen(cmd)
        return ""
    except Exception as e:
        return f"Falha ao iniciar o emulador: {e}"


PAGE = """<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>PCSX2 Web Station</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap" rel="stylesheet">
  <style>
    :root {
      --bg: #0c0f17;
      --surface: #141824;
      --surface-elevated: #1e2436;
      --surface-card: #181d2c;
      --border: rgba(255, 255, 255, 0.08);
      --border-active: rgba(59, 130, 246, 0.5);
      --accent: #2563eb;
      --accent-hover: #3b82f6;
      --accent-glow: rgba(37, 99, 235, 0.35);
      --ps2-blue: #00439c;
      --fg: #f3f4f6;
      --fg-muted: #94a3b8;
      --danger: #ef4444;
      --success: #10b981;
      --warning: #f59e0b;
      --radius: 12px;
      --radius-sm: 8px;
      --transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
    }

    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      background: var(--bg);
      color: var(--fg);
      font-family: 'Plus Jakarta Sans', system-ui, -apple-system, sans-serif;
      min-height: 100vh;
      display: flex;
      flex-direction: column;
      overflow-x: hidden;
      background-image: 
        radial-gradient(circle at 10% 20%, rgba(37, 99, 235, 0.08) 0%, transparent 40%),
        radial-gradient(circle at 90% 80%, rgba(0, 67, 156, 0.1) 0%, transparent 40%);
    }

    header {
      background: rgba(20, 24, 36, 0.75);
      backdrop-filter: blur(16px);
      -webkit-backdrop-filter: blur(16px);
      border-bottom: 1px solid var(--border);
      position: sticky;
      top: 0;
      z-index: 50;
      padding: 14px 28px;
    }

    .nav-container {
      max-width: 1400px;
      margin: 0 auto;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 20px;
    }

    .brand {
      display: flex;
      align-items: center;
      gap: 12px;
      font-weight: 800;
      font-size: 20px;
      letter-spacing: -0.5px;
    }

    .brand-badge {
      background: linear-gradient(135deg, #00439c, #2563eb);
      color: #fff;
      font-size: 11px;
      font-weight: 800;
      padding: 3px 8px;
      border-radius: 6px;
      letter-spacing: 1px;
      box-shadow: 0 0 12px var(--accent-glow);
    }

    .header-actions {
      display: flex;
      align-items: center;
      gap: 12px;
      flex: 1;
      max-width: 600px;
      justify-content: flex-end;
    }

    .search-box {
      position: relative;
      width: 100%;
      max-width: 340px;
    }

    .search-box input {
      width: 100%;
      background: var(--surface);
      border: 1px solid var(--border);
      color: var(--fg);
      padding: 10px 16px 10px 38px;
      border-radius: 30px;
      font-size: 14px;
      outline: none;
      transition: var(--transition);
    }

    .search-box input:focus {
      border-color: var(--accent-hover);
      box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.2);
      background: var(--surface-elevated);
    }

    .search-icon {
      position: absolute;
      left: 14px;
      top: 50%;
      transform: translateY(-50%);
      color: var(--fg-muted);
      pointer-events: none;
      font-size: 14px;
    }

    .btn {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: 8px;
      padding: 10px 18px;
      border-radius: var(--radius-sm);
      font-size: 14px;
      font-weight: 600;
      cursor: pointer;
      border: 1px solid var(--border);
      background: var(--surface-elevated);
      color: var(--fg);
      transition: var(--transition);
      white-space: nowrap;
    }

    .btn:hover {
      background: rgba(255, 255, 255, 0.1);
      border-color: rgba(255, 255, 255, 0.2);
    }

    .btn-primary {
      background: var(--accent);
      border-color: var(--accent);
      color: #fff;
      box-shadow: 0 2px 10px var(--accent-glow);
    }

    .btn-primary:hover {
      background: var(--accent-hover);
      border-color: var(--accent-hover);
      box-shadow: 0 4px 14px rgba(59, 130, 246, 0.5);
    }

    .btn-sm { padding: 6px 12px; font-size: 12px; }
    .btn-danger { background: rgba(239, 68, 68, 0.15); color: #f87171; border-color: rgba(239, 68, 68, 0.3); }
    .btn-danger:hover { background: var(--danger); color: #fff; }

    main {
      max-width: 1400px;
      width: 100%;
      margin: 0 auto;
      padding: 28px;
      flex: 1;
    }

    .status-bar {
      display: flex;
      align-items: center;
      justify-content: space-between;
      flex-wrap: wrap;
      gap: 16px;
      background: var(--surface);
      border: 1px solid var(--border);
      padding: 14px 20px;
      border-radius: var(--radius);
      margin-bottom: 24px;
    }

    .status-indicator {
      display: flex;
      align-items: center;
      gap: 10px;
      font-size: 13px;
    }

    .dot {
      width: 10px;
      height: 10px;
      border-radius: 50%;
      background: var(--danger);
      box-shadow: 0 0 8px rgba(239, 68, 68, 0.5);
    }

    .dot.active {
      background: var(--success);
      box-shadow: 0 0 8px rgba(16, 185, 129, 0.6);
    }

    .status-details {
      display: flex;
      align-items: center;
      gap: 16px;
      color: var(--fg-muted);
      font-size: 13px;
    }

    .jobs-banner {
      display: none;
      background: linear-gradient(90deg, rgba(37, 99, 235, 0.2), rgba(0, 67, 156, 0.2));
      border: 1px solid var(--border-active);
      border-radius: var(--radius);
      padding: 12px 18px;
      margin-bottom: 24px;
      align-items: center;
      gap: 12px;
      font-size: 14px;
      animation: pulse 2s infinite ease-in-out;
    }

    @keyframes pulse {
      0%, 100% { opacity: 0.9; }
      50% { opacity: 1; box-shadow: 0 0 16px rgba(37, 99, 235, 0.25); }
    }

    .section-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 18px;
    }

    .section-title {
      font-size: 18px;
      font-weight: 700;
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .count-badge {
      background: var(--surface-elevated);
      color: var(--fg-muted);
      font-size: 12px;
      padding: 2px 8px;
      border-radius: 20px;
      font-weight: 600;
      border: 1px solid var(--border);
    }

    /* Grid de Jogos estilo Steam */
    .game-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(185px, 1fr));
      gap: 22px;
    }

    .game-card {
      background: var(--surface-card);
      border: 1px solid var(--border);
      border-radius: var(--radius);
      overflow: hidden;
      display: flex;
      flex-direction: column;
      position: relative;
      transition: var(--transition);
      cursor: pointer;
    }

    .game-card:hover {
      transform: translateY(-6px);
      border-color: var(--border-active);
      box-shadow: 0 12px 28px rgba(0, 0, 0, 0.4), 0 0 14px rgba(37, 99, 235, 0.2);
    }

    .cover-container {
      position: relative;
      width: 100%;
      aspect-ratio: 3 / 4.25;
      background: #0f131d;
      overflow: hidden;
      display: flex;
      align-items: center;
      justify-content: center;
    }

    .cover-img {
      width: 100%;
      height: 100%;
      object-fit: cover;
      transition: transform 0.3s ease;
    }

    .game-card:hover .cover-img {
      transform: scale(1.05);
    }

    .cover-fallback {
      width: 100%;
      height: 100%;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      padding: 16px;
      text-align: center;
      background: linear-gradient(135deg, #182032, #0c111e);
      color: var(--fg-muted);
      border-bottom: 1px solid var(--border);
    }

    .cover-fallback .icon {
      font-size: 32px;
      margin-bottom: 8px;
      opacity: 0.6;
    }

    .cover-fallback span {
      font-size: 13px;
      font-weight: 700;
      color: var(--fg);
      display: -webkit-box;
      -webkit-line-clamp: 3;
      -webkit-box-orient: vertical;
      overflow: hidden;
    }

    .play-overlay {
      position: absolute;
      inset: 0;
      background: rgba(12, 15, 23, 0.7);
      backdrop-filter: blur(4px);
      display: flex;
      align-items: center;
      justify-content: center;
      opacity: 0;
      transition: var(--transition);
    }

    .game-card:hover .play-overlay {
      opacity: 1;
    }

    .play-btn-circle {
      width: 52px;
      height: 52px;
      background: var(--accent);
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      color: #fff;
      font-size: 20px;
      box-shadow: 0 4px 16px var(--accent-glow);
      transition: var(--transition);
    }

    .play-btn-circle:hover {
      transform: scale(1.1);
      background: var(--accent-hover);
    }

    .card-body {
      padding: 12px;
      display: flex;
      flex-direction: column;
      gap: 4px;
      flex: 1;
    }

    .game-title {
      font-size: 14px;
      font-weight: 700;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
      color: var(--fg);
    }

    .game-path {
      font-size: 11px;
      color: var(--fg-muted);
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }

    .card-footer {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 8px 12px;
      border-top: 1px solid var(--border);
      background: rgba(0, 0, 0, 0.15);
    }

    .card-actions {
      display: flex;
      gap: 6px;
      margin-left: auto;
    }

    .icon-btn {
      background: transparent;
      border: none;
      color: var(--fg-muted);
      cursor: pointer;
      padding: 4px;
      border-radius: 4px;
      font-size: 13px;
      transition: var(--transition);
      display: flex;
      align-items: center;
      justify-content: center;
    }

    .icon-btn:hover {
      color: var(--fg);
      background: rgba(255, 255, 255, 0.1);
    }

    .icon-btn.delete:hover {
      color: var(--danger);
      background: rgba(239, 68, 68, 0.15);
    }

    /* Modal */
    .modal-backdrop {
      position: fixed;
      inset: 0;
      background: rgba(0, 0, 0, 0.7);
      backdrop-filter: blur(8px);
      z-index: 100;
      display: none;
      align-items: center;
      justify-content: center;
      padding: 20px;
    }

    .modal-backdrop.open {
      display: flex;
    }

    .modal {
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: var(--radius);
      width: 100%;
      max-width: 520px;
      box-shadow: 0 20px 40px rgba(0, 0, 0, 0.6);
      overflow: hidden;
      animation: modalIn 0.25s cubic-bezier(0.16, 1, 0.3, 1);
    }

    @keyframes modalIn {
      from { opacity: 0; transform: scale(0.95) translateY(10px); }
      to { opacity: 1; transform: scale(1) translateY(0); }
    }

    .modal-header {
      padding: 18px 24px;
      border-bottom: 1px solid var(--border);
      display: flex;
      align-items: center;
      justify-content: space-between;
    }

    .modal-title {
      font-size: 16px;
      font-weight: 700;
    }

    .modal-body {
      padding: 24px;
      display: flex;
      flex-direction: column;
      gap: 16px;
    }

    .form-group {
      display: flex;
      flex-direction: column;
      gap: 6px;
    }

    .form-group label {
      font-size: 13px;
      font-weight: 600;
      color: var(--fg-muted);
    }

    .form-group input[type="text"] {
      background: var(--bg);
      border: 1px solid var(--border);
      color: var(--fg);
      padding: 10px 14px;
      border-radius: var(--radius-sm);
      font-size: 14px;
      outline: none;
    }

    .form-group input[type="text"]:focus {
      border-color: var(--accent);
    }

    .checkbox-label {
      display: flex;
      align-items: center;
      gap: 10px;
      font-size: 14px;
      cursor: pointer;
      color: var(--fg);
    }

    .modal-footer {
      padding: 16px 24px;
      border-top: 1px solid var(--border);
      background: rgba(0, 0, 0, 0.2);
      display: flex;
      justify-content: flex-end;
      gap: 10px;
    }

    /* Tabs no modal de adicionar */
    .modal-tabs {
      display: flex;
      border-bottom: 1px solid var(--border);
      padding: 0 24px;
      background: rgba(0, 0, 0, 0.15);
    }

    .tab-btn {
      padding: 12px 16px;
      background: transparent;
      border: none;
      color: var(--fg-muted);
      font-size: 13px;
      font-weight: 600;
      cursor: pointer;
      border-bottom: 2px solid transparent;
      transition: var(--transition);
    }

    .tab-btn.active {
      color: var(--fg);
      border-bottom-color: var(--accent);
    }

    .empty-state {
      text-align: center;
      padding: 60px 20px;
      background: var(--surface);
      border: 1px dashed var(--border);
      border-radius: var(--radius);
      margin: 20px 0;
    }

    .empty-state h3 {
      font-size: 18px;
      margin-bottom: 8px;
    }

    .empty-state p {
      color: var(--fg-muted);
      font-size: 14px;
      margin-bottom: 20px;
    }

    .toast {
      position: fixed;
      bottom: 24px;
      right: 24px;
      background: var(--surface-elevated);
      border: 1px solid var(--border-active);
      color: var(--fg);
      padding: 12px 20px;
      border-radius: var(--radius);
      box-shadow: 0 8px 24px rgba(0,0,0,0.4);
      z-index: 200;
      display: none;
      font-size: 14px;
      animation: toastIn 0.3s ease;
    }

    @keyframes toastIn {
      from { transform: translateY(20px); opacity: 0; }
      to { transform: translateY(0); opacity: 1; }
    }
  </style>
</head>
<body>
  <header>
    <div class="nav-container">
      <div class="brand">
        <span>PCSX2</span>
        <span class="brand-badge">WEB STATION</span>
      </div>

      <div class="header-actions">
        <div class="search-box">
          <span class="search-icon">🔍</span>
          <input type="text" id="searchInput" placeholder="Buscar na biblioteca..." oninput="filterGames()">
        </div>
        <button class="btn btn-primary" onclick="openAddModal()">
          <span>➕ Adicionar</span>
        </button>
        <button class="btn" onclick="openSettingsModal()" title="Configuracoes">
          <span>⚙️</span>
        </button>
      </div>
    </div>
  </header>

  <main>
    <div class="status-bar">
      <div class="status-indicator">
        <div class="dot" id="statusDot"></div>
        <span id="statusText">Verificando emulador...</span>
      </div>
      <div class="status-details">
        <span id="gameTotalCount">0 jogos</span>
        <span>•</span>
        <span id="fullscreenIndicator">Tela cheia: Ativa</span>
      </div>
    </div>

    <div class="jobs-banner" id="jobsBanner">
      <span>⏳</span>
      <span id="jobsText">Baixando arquivo em segundo plano...</span>
    </div>

    <div class="section-header">
      <div class="section-title">
        <span>Sua Colecao</span>
        <span class="count-badge" id="visibleCount">0</span>
      </div>
    </div>

    <div id="gameGrid" class="game-grid"></div>

    <div id="emptyState" class="empty-state" style="display: none;">
      <h3>Nenhum jogo encontrado</h3>
      <p>Adicione arquivos .iso, .chd, escaneie uma pasta inteira ou baixe direto do Google Drive.</p>
      <button class="btn btn-primary" onclick="openAddModal()">Adicionar Jogos Agora</button>
    </div>
  </main>

  <!-- Modal Adicionar -->
  <div class="modal-backdrop" id="addModal">
    <div class="modal">
      <div class="modal-header">
        <div class="modal-title">Adicionar Jogos</div>
        <button class="icon-btn" onclick="closeModal('addModal')">✕</button>
      </div>
      <div class="modal-tabs">
        <button class="tab-btn active" id="tabScanBtn" onclick="switchAddTab('scan')">📁 Varrer Pasta</button>
        <button class="tab-btn" id="tabFileBtn" onclick="switchAddTab('file')">📄 Arquivo Unico</button>
        <button class="tab-btn" id="tabDriveBtn" onclick="switchAddTab('drive')">☁️ Google Drive</button>
      </div>
      <div class="modal-body">
        <!-- Tab 1: Varrer Pasta -->
        <div id="tabScan" class="tab-content">
          <div class="form-group">
            <label>Caminho da Pasta com Jogos (.iso, .chd, .cso, .bin)</label>
            <input type="text" id="scanPathInput" placeholder="Ex: D:\Emuladores\PS2\ISOs ou ./isos">
          </div>
          <p style="font-size: 12px; color: var(--fg-muted); margin-top: 6px;">
            A varredura analisa subpastas recursivamente e adiciona automaticamente todos os jogos compativeis sem duplicar.
          </p>
        </div>

        <!-- Tab 2: Arquivo Unico -->
        <div id="tabFile" class="tab-content" style="display: none;">
          <div class="form-group">
            <label>Caminho Completo do Arquivo</label>
            <input type="text" id="filePathInput" placeholder="Ex: C:\Jogos\Shadow of the Colossus.iso">
          </div>
        </div>

        <!-- Tab 3: Google Drive -->
        <div id="tabDrive" class="tab-content" style="display: none;">
          <div class="form-group">
            <label>Link Compartilhado do Google Drive</label>
            <input type="text" id="driveUrlInput" placeholder="https://drive.google.com/file/d/.../view">
          </div>
          <p style="font-size: 12px; color: var(--fg-muted); margin-top: 6px;">
            O arquivo sera baixado em segundo plano para a pasta local <code>isos/</code> via <code>gdown</code>.
          </p>
        </div>
      </div>
      <div class="modal-footer">
        <button class="btn" onclick="closeModal('addModal')">Cancelar</button>
        <button class="btn btn-primary" id="addSubmitBtn" onclick="submitAdd()">Confirmar</button>
      </div>
    </div>
  </div>

  <!-- Modal Configuracoes -->
  <div class="modal-backdrop" id="settingsModal">
    <div class="modal">
      <div class="modal-header">
        <div class="modal-title">Configuracoes do Emulador</div>
        <button class="icon-btn" onclick="closeModal('settingsModal')">✕</button>
      </div>
      <div class="modal-body">
        <div class="form-group">
          <label>Caminho do Executavel PCSX2 (pcsx2-qt.exe ou comando Linux)</label>
          <input type="text" id="settingsExeInput" placeholder="C:\Program Files\PCSX2\pcsx2-qt.exe">
        </div>
        <div class="form-group">
          <label class="checkbox-label">
            <input type="checkbox" id="settingsFsInput">
            <span>Iniciar jogos automaticamente em Tela Cheia (-fullscreen)</span>
          </label>
        </div>
      </div>
      <div class="modal-footer">
        <button class="btn" onclick="closeModal('settingsModal')">Cancelar</button>
        <button class="btn btn-primary" onclick="submitSettings()">Salvar Configuracoes</button>
      </div>
    </div>
  </div>

  <!-- Modal Renomear Jogo -->
  <div class="modal-backdrop" id="renameModal">
    <div class="modal">
      <div class="modal-header">
        <div class="modal-title">Editar Nome do Jogo</div>
        <button class="icon-btn" onclick="closeModal('renameModal')">✕</button>
      </div>
      <div class="modal-body">
        <input type="hidden" id="renameIndex">
        <div class="form-group">
          <label>Titulo do Jogo (usado para buscar a capa oficial)</label>
          <input type="text" id="renameTitleInput">
        </div>
      </div>
      <div class="modal-footer">
        <button class="btn" onclick="closeModal('renameModal')">Cancelar</button>
        <button class="btn btn-primary" onclick="submitRename()">Salvar e Atualizar Capa</button>
      </div>
    </div>
  </div>

  <div class="toast" id="toast"></div>

  <script>
    const TOKEN = "__TOKEN__";
    let state = { exe: "", fullscreen: true, games: [], jobs: {} };
    let currentTab = 'scan';

    const $ = id => document.getElementById(id);

    async function api(path, body) {
      const opts = {
        method: body ? "POST" : "GET",
        headers: { "X-Token": TOKEN, "Content-Type": "application/json" }
      };
      if (body) opts.body = JSON.stringify(body);
      const res = await fetch(path, opts);
      return res.json();
    }

    function showToast(msg) {
      const t = $("toast");
      t.textContent = msg;
      t.style.display = "block";
      setTimeout(() => { t.style.display = "none"; }, 3500);
    }

    async function loadState() {
      const s = await api("/api/state");
      state = s;
      updateHeaderStatus();
      renderGames();
      updateJobs();
    }

    function updateHeaderStatus() {
      const dot = $("statusDot");
      const text = $("statusText");
      if (state.exe) {
        dot.classList.add("active");
        text.textContent = "PCSX2 configurado: " + (state.exe.split(/\\|\//).pop() || state.exe);
      } else {
        dot.classList.remove("active");
        text.textContent = "Emulador nao configurado";
      }
      $("gameTotalCount").textContent = `${state.games.length} ${state.games.length === 1 ? 'jogo' : 'jogos'}`;
      $("fullscreenIndicator").textContent = `Tela cheia: ${state.fullscreen ? 'Ativa' : 'Desativada'}`;
    }

    function updateJobs() {
      const banner = $("jobsBanner");
      const text = $("jobsText");
      const jobList = Object.values(state.jobs || {});
      if (jobList.length > 0) {
        banner.style.display = "flex";
        text.textContent = jobList.map(j => typeof j === 'object' ? j.message : j).join(" | ");
        setTimeout(loadState, 3000);
      } else {
        banner.style.display = "none";
      }
    }

    function renderGames() {
      const grid = $("gameGrid");
      const empty = $("emptyState");
      const q = $("searchInput").value.toLowerCase().trim();
      grid.innerHTML = "";

      const filtered = state.games
        .map((g, idx) => ({ ...g, originalIndex: idx }))
        .filter(g => g.name.toLowerCase().includes(q));

      $("visibleCount").textContent = filtered.length;

      if (filtered.length === 0) {
        empty.style.display = "block";
        return;
      }
      empty.style.display = "none";

      filtered.forEach(g => {
        const card = document.createElement("div");
        card.className = "game-card";

        const coverWrap = document.createElement("div");
        coverWrap.className = "cover-container";

        const img = document.createElement("img");
        img.className = "cover-img";
        img.alt = g.name;
        img.src = `/cover/${g.originalIndex}?t=${TOKEN}&n=${encodeURIComponent(g.name)}`;

        const fallback = document.createElement("div");
        fallback.className = "cover-fallback";
        fallback.innerHTML = `<div class="icon">🎮</div><span>${escapeHtml(g.name)}</span>`;
        fallback.style.display = "none";

        img.onerror = () => {
          img.style.display = "none";
          fallback.style.display = "flex";
        };

        const overlay = document.createElement("div");
        overlay.className = "play-overlay";
        overlay.innerHTML = `<div class="play-btn-circle" title="Jogar">▶</div>`;
        overlay.onclick = (e) => {
          e.stopPropagation();
          playGame(g.originalIndex);
        };

        coverWrap.append(img, fallback, overlay);

        const body = document.createElement("div");
        body.className = "card-body";
        body.innerHTML = `
          <div class="game-title" title="${escapeHtml(g.name)}">${escapeHtml(g.name)}</div>
          <div class="game-path" title="${escapeHtml(g.path)}">${escapeHtml(g.path)}</div>
        `;

        const footer = document.createElement("div");
        footer.className = "card-footer";

        const lastPlayed = document.createElement("span");
        lastPlayed.style.fontSize = "11px";
        lastPlayed.style.color = "var(--fg-muted)";
        lastPlayed.textContent = g.last_played ? "Jogado recentemente" : "Nunca jogado";

        const actions = document.createElement("div");
        actions.className = "card-actions";

        const renameBtn = document.createElement("button");
        renameBtn.className = "icon-btn";
        renameBtn.title = "Renomear titulo";
        renameBtn.innerHTML = "✏️";
        renameBtn.onclick = (e) => {
          e.stopPropagation();
          openRenameModal(g.originalIndex, g.name);
        };

        const refreshCoverBtn = document.createElement("button");
        refreshCoverBtn.className = "icon-btn";
        refreshCoverBtn.title = "Recarregar capa";
        refreshCoverBtn.innerHTML = "🔄";
        refreshCoverBtn.onclick = async (e) => {
          e.stopPropagation();
          await api("/api/refresh_cover", { index: g.originalIndex });
          img.src = `/cover/${g.originalIndex}?t=${TOKEN}&n=${encodeURIComponent(g.name)}&r=${Date.now()}`;
          showToast("Atualizando capa...");
        };

        const delBtn = document.createElement("button");
        delBtn.className = "icon-btn delete";
        delBtn.title = "Remover da lista";
        delBtn.innerHTML = "🗑️";
        delBtn.onclick = (e) => {
          e.stopPropagation();
          if (confirm(`Remover "${g.name}" da biblioteca? O arquivo no disco nao sera excluido.`)) {
            removeGame(g.originalIndex);
          }
        };

        actions.append(refreshCoverBtn, renameBtn, delBtn);
        footer.append(lastPlayed, actions);

        card.append(coverWrap, body, footer);
        grid.append(card);
      });
    }

    function filterGames() {
      renderGames();
    }

    function escapeHtml(str) {
      return (str || "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
    }

    async function playGame(index) {
      showToast("Iniciando PCSX2...");
      const res = await api("/api/play", { index });
      if (res.error) {
        alert("Erro ao iniciar jogo: " + res.error);
      }
      loadState();
    }

    async function removeGame(index) {
      await api("/api/remove", { index });
      showToast("Jogo removido da biblioteca.");
      loadState();
    }

    function openAddModal() {
      $("addModal").classList.add("open");
    }

    function openSettingsModal() {
      $("settingsExeInput").value = state.exe || "";
      $("settingsFsInput").checked = state.fullscreen;
      $("settingsModal").classList.add("open");
    }

    function openRenameModal(index, currentName) {
      $("renameIndex").value = index;
      $("renameTitleInput").value = currentName;
      $("renameModal").classList.add("open");
    }

    function closeModal(id) {
      $(id).classList.remove("open");
    }

    function switchAddTab(tab) {
      currentTab = tab;
      $("tabScan").style.display = tab === 'scan' ? 'block' : 'none';
      $("tabFile").style.display = tab === 'file' ? 'block' : 'none';
      $("tabDrive").style.display = tab === 'drive' ? 'block' : 'none';

      $("tabScanBtn").classList.toggle('active', tab === 'scan');
      $("tabFileBtn").classList.toggle('active', tab === 'file');
      $("tabDriveBtn").classList.toggle('active', tab === 'drive');
    }

    async function submitAdd() {
      if (currentTab === 'scan') {
        const path = $("scanPathInput").value.trim();
        if (!path) return alert("Digite o caminho da pasta.");
        showToast("Varrendo pasta...");
        const res = await api("/api/scan", { path });
        if (res.error) return alert("Erro: " + res.error);
        showToast(`Varredura concluida: +${res.added} novos jogos adicionados!`);
        $("scanPathInput").value = "";
      } else if (currentTab === 'file') {
        const path = $("filePathInput").value.trim();
        if (!path) return alert("Digite o caminho do arquivo.");
        const res = await api("/api/add", { path });
        if (res.error) return alert("Erro: " + res.error);
        showToast("Jogo adicionado com sucesso!");
        $("filePathInput").value = "";
      } else if (currentTab === 'drive') {
        const url = $("driveUrlInput").value.trim();
        if (!url) return alert("Cole o link do Google Drive.");
        const res = await api("/api/drive", { url });
        if (res.error) return alert("Erro: " + res.error);
        showToast("Download iniciado em segundo plano!");
        $("driveUrlInput").value = "";
      }
      closeModal('addModal');
      loadState();
    }

    async function submitSettings() {
      const exe = $("settingsExeInput").value.trim();
      const fullscreen = $("settingsFsInput").checked;
      await api("/api/settings", { exe, fullscreen });
      showToast("Configuracoes salvas!");
      closeModal('settingsModal');
      loadState();
    }

    async function submitRename() {
      const index = parseInt($("renameIndex").value, 10);
      const name = $("renameTitleInput").value.trim();
      if (!name) return alert("O nome nao pode ficar vazio.");
      await api("/api/rename", { index, name });
      showToast("Nome alterado e capa atualizada!");
      closeModal('renameModal');
      loadState();
    }

    // Fecha modais com ESC
    window.addEventListener("keydown", (e) => {
      if (e.key === "Escape") {
        document.querySelectorAll(".modal-backdrop.open").forEach(m => m.classList.remove("open"));
      }
    });

    loadState();
  </script>
</body>
</html>
"""


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "X-Token, Content-Type, Origin")
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(204)
        self.end_headers()

    def _send(self, code, body, ctype="application/json"):
        b = body if isinstance(body, bytes) else body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype if ctype.startswith("image") else ctype + "; charset=utf-8")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def _ok(self, need_token=True):
        host = self.headers.get("Host", "").split(":")[0]
        if False:
            return False
        return not need_token or self.headers.get("X-Token") == TOKEN

    def do_GET(self):
        u = urllib.parse.urlparse(self.path)
        if u.path.startswith("/cover/") and self._ok(False):
            qs = urllib.parse.parse_qs(u.query)
            if qs.get("t", [""])[0] != TOKEN:
                return self._send(403, "{}")
            try:
                idx = int(u.path.rsplit("/", 1)[1])
                game = load()["games"][idx]
            except (ValueError, IndexError):
                return self._send(404, "{}")
            force = bool(qs.get("r"))
            data = cover_for(game["name"], force_refresh=force)
            return self._send(200, data, "image/png") if data else self._send(404, "{}")

        if self.path == "/" and self._ok(False):
            return self._send(200, PAGE.replace("__TOKEN__", TOKEN), "text/html")

        if self.path == "/api/state" and self._ok():
            d = load()
            d["jobs"] = dict(jobs)
            return self._send(200, json.dumps(d))

        self._send(403, "{}")

    def do_POST(self):
        if not self._ok():
            return self._send(403, "{}")
        try:
            n = int(self.headers.get("Content-Length") or 0)
            raw = self.rfile.read(n) if n > 0 else b"{}"
            body = json.loads(raw.decode("utf-8") or "{}")
        except ValueError:
            return self._send(400, "{}")

        err = ""
        extra_res = {}
        with lock:
            d = load()
            try:
                p = self.path
                if p == "/api/add":
                    path = str(body.get("path", "")).strip().strip('"')
                    if not Path(path).is_file():
                        raise ValueError("O arquivo nao existe no caminho especificado.")
                    p_obj = Path(path).resolve()
                    d["games"].append({
                        "name": p_obj.stem,
                        "path": str(p_obj),
                        "added_at": int(time.time()),
                        "last_played": None
                    })
                elif p == "/api/scan":
                    folder = str(body.get("path", "")).strip().strip('"')
                    added, total = scan_directory(folder)
                    extra_res["added"] = added
                    extra_res["total"] = total
                elif p == "/api/rename":
                    idx = int(body["index"])
                    new_name = str(body["name"]).strip()
                    if not new_name:
                        raise ValueError("O nome nao pode ser vazio.")
                    d["games"][idx]["name"] = new_name
                    # Limpa cache da capa para forcar recarregamento
                    cover_for(new_name, force_refresh=True)
                elif p == "/api/refresh_cover":
                    idx = int(body["index"])
                    name = d["games"][idx]["name"]
                    cover_for(name, force_refresh=True)
                elif p == "/api/remove":
                    del d["games"][int(body["index"])]
                elif p == "/api/settings":
                    if "exe" in body:
                        d["exe"] = str(body["exe"]).strip().strip('"')
                    if "fullscreen" in body:
                        d["fullscreen"] = bool(body["fullscreen"])
                elif p == "/api/play":
                    err = play(d, int(body["index"]))
                elif p == "/api/drive":
                    job = secrets.token_hex(4)
                    jobs[job] = {"status": "starting", "message": "Conectando ao Google Drive..."}
                    threading.Thread(target=drive_job, args=(job, str(body.get("url", ""))), daemon=True).start()
                else:
                    return self._send(404, "{}")
                save(d)
            except (KeyError, ValueError, IndexError) as e:
                err = str(e) or "Parametros invalidos."

        resp = {"error": err}
        resp.update(extra_res)
        self._send(200, json.dumps(resp))


def start_server():
    port = PORT
    server = None
    for attempt in range(5):
        try:
            server = ThreadingHTTPServer(("0.0.0.0", port), Handler)
            break
        except OSError as e:
            if "Address already in use" in str(e) or e.errno == 98 or e.errno == 10048:
                port += 1
            else:
                raise e

    if not server:
        print("Erro: Nao foi possivel vincular o servidor a nenhuma porta proxima a 8765.")
        sys.exit(1)

    import socket
    local_ip = "127.0.0.1"
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
    except Exception:
        pass
    url = f"http://127.0.0.1:{port}/"
    lan_url = f"http://{local_ip}:{port}/"
    print(f" Acesso na Rede (Celular/Outro PC): {lan_url}")
    print("=" * 60)
    print(" PCSX2 Web Station - Launcher Local")
    print(f" Servidor iniciado em: {url}")
    print(" Pressione Ctrl+C para encerrar o servidor.")
    print("=" * 60)
    webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nEncerrando servidor...")


if __name__ == "__main__":
    start_server()
