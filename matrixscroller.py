#!/usr/bin/env python3
"""
fpp-matrixscroller daemon
Watches FPP status and drives fpp-matrixtools overlays on N matrix panels.
Each panel has independent config for media-playing and no-media modes.
Exposes a REST API on port 32329 for config and status.
"""

import json
import logging
import os
import signal
import subprocess
import sys
import threading
import time
import unicodedata
import urllib.request
import urllib.error
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Dict, Optional

# ── Paths ────────────────────────────────────────────────────────────────────
PLUGIN_DIR   = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH  = "/home/fpp/media/config/plugin.matrixscroller.json"
DEFAULT_CFG  = os.path.join(PLUGIN_DIR, "config.json")
LOG_PATH     = "/home/fpp/media/logs/matrixscroller.log"
API_PORT     = 32329

# ── Logging ──────────────────────────────────────────────────────────────────
os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_PATH),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("matrixscroller")

# ── Config helpers ────────────────────────────────────────────────────────────

def load_config() -> dict:
    """Load config from user path, fall back to plugin default."""
    for path in [CONFIG_PATH, DEFAULT_CFG]:
        if os.path.exists(path):
            try:
                with open(path) as f:
                    cfg = json.load(f)
                log.info("Loaded config from %s", path)
                return cfg
            except Exception as e:
                log.error("Failed to load config from %s: %s", path, e)
    log.warning("No config found, using empty defaults")
    return {"global": {}, "panels": []}


def save_config(cfg: dict):
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    with open(CONFIG_PATH, "w") as f:
        json.dump(cfg, f, indent=4)
    log.info("Config saved to %s", CONFIG_PATH)


# ── FPP API helpers ───────────────────────────────────────────────────────────

def fpp_get(host: str, path: str, timeout: float = 2.0) -> Optional[dict]:
    url = f"http://{host}{path}"
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            return json.loads(resp.read())
    except Exception as e:
        log.debug("FPP GET %s failed: %s", url, e)
        return None


def get_fpp_status(host: str) -> Optional[dict]:
    return fpp_get(host, "/api/fppd/status")


def get_fpp_models(host: str) -> list:
    data = fpp_get(host, "/api/overlays/models")
    if isinstance(data, list):
        return data
    return []


# ── Text sanitisation ─────────────────────────────────────────────────────────

_CHAR_MAP = {
    '–': '-',    # en dash
    '—': ' - ',  # em dash
    '‘': "'",    # left single quote
    '’': "'",    # right single quote
    '“': '"',    # left double quote
    '”': '"',    # right double quote
    '…': '...',  # ellipsis
    '·': '.',    # middle dot
    '®': '(R)',  # registered sign
    '™': '(TM)', # trade mark sign
}

def _sanitize_text(text: str) -> str:
    """Transliterate Unicode to ASCII so all chars are renderable by bitmap fonts."""
    for ch, repl in _CHAR_MAP.items():
        text = text.replace(ch, repl)
    normalized = unicodedata.normalize('NFKD', text)
    return normalized.encode('ascii', errors='ignore').decode('ascii').strip()


# ── Message builder ───────────────────────────────────────────────────────────

def build_message(panel_cfg: dict, mode: str, metadata: Optional[dict] = None) -> str:
    """
    Assemble the scroll message from enabled fields.
    mode: 'media' or 'no_media'
    metadata: dict with keys artist/title/album/fallback (media mode only)
    """
    fields = panel_cfg.get(mode, {})
    gap_cfg = fields.get("gap", {})
    gap = gap_cfg.get("text", " | ") if gap_cfg.get("enabled", True) else " "

    parts = []

    pre = fields.get("pre_roll", {})
    if pre.get("enabled") and pre.get("text", "").strip():
        parts.append(pre["text"].strip())

    tune = fields.get("tune_to", {})
    if tune.get("enabled") and tune.get("text", "").strip():
        parts.append(tune["text"].strip())

    if mode == "media" and metadata:
        song_parts = []
        if fields.get("artist", {}).get("enabled", True) and metadata.get("artist"):
            song_parts.append(metadata["artist"])
        if fields.get("title",  {}).get("enabled", True) and metadata.get("title"):
            song_parts.append(metadata["title"])
        if fields.get("album",  {}).get("enabled", False) and metadata.get("album"):
            song_parts.append(metadata["album"])
        if not song_parts and metadata.get("fallback"):
            song_parts.append(metadata["fallback"])
        parts.extend(song_parts)

    post = fields.get("post_roll", {})
    if post.get("enabled") and post.get("text", "").strip():
        parts.append(post["text"].strip())

    return gap.join(parts) if parts else ""


# ── Panel controller ──────────────────────────────────────────────────────────

class PanelController:
    """Manages a single matrix panel's matrixtools subprocess."""

    def __init__(self, panel_cfg: dict, global_cfg: dict):
        self.cfg = panel_cfg
        self.gcfg = global_cfg
        self._proc: Optional[subprocess.Popen] = None
        self._lock = threading.Lock()
        self.current_message = ""
        self.current_mode = ""
        self.current_song_key = ""

    def _matrixtools_path(self) -> str:
        return self.gcfg.get(
            "matrixtools_path",
            "/home/fpp/media/plugins/fpp-matrixtools/scripts/matrixtools",
        )

    def _get_song_overrides(self, song_key: str) -> dict:
        """Return the song_overrides entry matching song_key (case-insensitive, extension-optional)."""
        overrides_dict = self.cfg.get("song_overrides", {})
        if not song_key or not overrides_dict:
            return {}
        if song_key in overrides_dict:
            return overrides_dict[song_key]
        song_key_lower = song_key.lower()
        for k, v in overrides_dict.items():
            if os.path.splitext(k)[0].lower() == song_key_lower or k.lower() == song_key_lower:
                return v
        return {}

    def _build_cmd(self, message: str, overrides: dict = None) -> list:
        cfg = self.cfg
        ov = overrides or {}
        host = self.gcfg.get("fpp_host", "localhost")
        cmd = [
            self._matrixtools_path(),
            "--host", host,
            "--blockname", cfg.get("model", ""),
            "--enable", "1",
            "--message", message,
            "--color",          ov.get("color")          or cfg.get("color",          "#ff0000"),
            "--font",           ov.get("font")           or cfg.get("font",           "Helvetica"),
            "--fontsize",   str(ov.get("fontsize")       or cfg.get("fontsize",       10)),
            "--position",       ov.get("position")       or cfg.get("position",       "R2L"),
            "--pixelspersecond", str(ov.get("pixelspersecond") or cfg.get("pixelspersecond", 15)),
        ]
        return cmd

    def _stop_proc(self):
        """Kill the running matrixtools subprocess if any."""
        if self._proc and self._proc.poll() is None:
            try:
                self._proc.terminate()
                self._proc.wait(timeout=2)
            except Exception:
                try:
                    self._proc.kill()
                except Exception:
                    pass
        self._proc = None

    def _clear_model(self):
        """Send a clear command to disable the overlay block."""
        host = self.gcfg.get("fpp_host", "localhost")
        model = self.cfg.get("model", "")
        if not model:
            return
        try:
            subprocess.run(
                [self._matrixtools_path(), "--host", host,
                 "--blockname", model, "--enable", "0"],
                timeout=3, capture_output=True
            )
        except Exception as e:
            log.debug("Clear model failed: %s", e)

    def start(self, message: str, mode: str, song_key: str = ""):
        """Stop any existing process and start a new one with the given message."""
        with self._lock:
            if not self.cfg.get("enabled", True):
                return

            overrides = self._get_song_overrides(song_key) if mode == "media" else {}

            # Song override can disable this panel for a specific song
            if mode == "media" and overrides.get("enabled") is False:
                self._stop_proc()
                self._clear_model()
                self.current_message = ""
                self.current_mode = mode
                self.current_song_key = song_key
                return

            model = self.cfg.get("model", "")
            if not model:
                log.warning("Panel '%s' has no model set, skipping", self.cfg.get("name"))
                return
            if not message:
                log.debug("Panel '%s' empty message, clearing", self.cfg.get("name"))
                self._stop_proc()
                self._clear_model()
                self.current_message = ""
                self.current_mode = mode
                self.current_song_key = song_key
                return

            # matrixtools is one-shot: sends command to FPP and exits immediately.
            # Only resend when something actually changes.
            if (message == self.current_message and mode == self.current_mode
                    and song_key == self.current_song_key):
                return

            log.info("Panel '%s' [%s] song=%r: %s", self.cfg.get("name"), mode, song_key or "—", message)
            self._stop_proc()
            cmd = self._build_cmd(message, overrides)
            try:
                self._proc = subprocess.Popen(
                    cmd,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                self.current_message = message
                self.current_mode = mode
                self.current_song_key = song_key
            except Exception as e:
                log.error("Failed to start matrixtools for panel '%s': %s",
                          self.cfg.get("name"), e)

    def stop(self):
        with self._lock:
            self._stop_proc()
            self._clear_model()
            self.current_message = ""
            self.current_mode = ""
            self.current_song_key = ""

    def status(self) -> dict:
        with self._lock:
            running = bool(self._proc and self._proc.poll() is None)
        return {
            "id": self.cfg.get("id"),
            "name": self.cfg.get("name"),
            "enabled": self.cfg.get("enabled", True),
            "model": self.cfg.get("model", ""),
            "mode": self.current_mode,
            "message": self.current_message,
            "song_key": self.current_song_key,
            "running": running,
        }

    def update_cfg(self, panel_cfg: dict):
        with self._lock:
            self.cfg = panel_cfg
            # Force restart on next poll cycle by clearing cached state
            self.current_message = ""
            self.current_mode = ""
            self.current_song_key = ""


# ── Main daemon ───────────────────────────────────────────────────────────────

class MatrixScrollerDaemon:

    def __init__(self):
        self.config = load_config()
        self.panels: Dict[str, PanelController] = {}
        self._running = False
        self._lock = threading.Lock()
        self._no_media_since: Dict[str, Optional[float]] = {}
        self._message_overrides: Dict[str, Optional[str]] = {}
        self._current_song = ""
        self._rebuild_panels()

    def _global(self) -> dict:
        return self.config.get("global", {})

    def _rebuild_panels(self):
        """Sync panel controllers to current config."""
        with self._lock:
            cfg_panels = {p["id"]: p for p in self.config.get("panels", [])}

            # Remove panels no longer in config
            for pid in list(self.panels.keys()):
                if pid not in cfg_panels:
                    self.panels[pid].stop()
                    del self.panels[pid]

            # Add or update panels
            for pid, pcfg in cfg_panels.items():
                if pid in self.panels:
                    self.panels[pid].update_cfg(pcfg)
                else:
                    self.panels[pid] = PanelController(pcfg, self._global())
                    self._no_media_since[pid] = None
                    self._message_overrides[pid] = None

    def reload_config(self):
        self.config = load_config()
        self._rebuild_panels()
        log.info("Config reloaded")

    def set_override(self, panel_id: str, message: Optional[str]):
        """Set or clear a manual message override for a panel."""
        with self._lock:
            self._message_overrides[panel_id] = message
            if panel_id in self.panels:
                # Force restart
                self.panels[panel_id].current_message = ""

    def _get_current_song_key(self, status: dict) -> str:
        """Return the current media filename without extension for song_overrides lookup."""
        from urllib.parse import unquote
        for field in ("current_song", "current_sequence"):
            val = (status.get(field) or "").strip()
            if val:
                return os.path.splitext(os.path.basename(unquote(val)))[0]
        return ""

    def _get_metadata(self, status: dict) -> dict:
        """Extract and sanitize metadata fields from FPP status."""
        meta   = status.get("mediameta", {}) or {}
        artist = _sanitize_text((meta.get("artist") or "").strip())
        title  = _sanitize_text((meta.get("title")  or "").strip())
        album  = _sanitize_text((meta.get("album")  or "").strip())
        fallback = ""
        for field in ("current_song", "current_sequence"):
            val = (status.get(field) or "").strip()
            if val:
                fallback = _sanitize_text(os.path.splitext(os.path.basename(val))[0])
                break
        return {"artist": artist, "title": title, "album": album, "fallback": fallback}

    def _is_playing(self, status: dict) -> bool:
        return status.get("status", 0) == 1

    def poll_once(self):
        host = self._global().get("fpp_host", "localhost")
        no_media_timeout = float(self._global().get("no_media_timeout", 5.0))

        status = get_fpp_status(host)
        if status is None:
            return  # FPP unreachable, leave current state

        playing  = self._is_playing(status)
        metadata = self._get_metadata(status) if playing else {}
        song_key = self._get_current_song_key(status) if playing else ""
        has_content = playing and bool(
            metadata.get("artist") or metadata.get("title") or metadata.get("fallback")
        )

        if has_content:
            a, t = metadata.get("artist", ""), metadata.get("title", "")
            self._current_song = f"{a} - {t}" if a and t else t or a or metadata.get("fallback", "")
        else:
            self._current_song = ""

        now = time.monotonic()

        with self._lock:
            panels_snapshot = list(self.panels.items())
            overrides = dict(self._message_overrides)

        for pid, panel in panels_snapshot:
            # Manual override wins
            override = overrides.get(pid)
            if override is not None:
                panel.start(override, "override")
                continue

            media_enabled    = panel.cfg.get("media",    {}).get("enabled", True)
            no_media_enabled = panel.cfg.get("no_media", {}).get("enabled", True)

            if has_content:
                # Reset no-media timer
                self._no_media_since[pid] = None
                if media_enabled:
                    msg = build_message(panel.cfg, "media", metadata)
                    panel.start(msg, "media", song_key)
                else:
                    panel.stop()
            else:
                # Start no-media timer if not already started
                if self._no_media_since.get(pid) is None:
                    self._no_media_since[pid] = now

                elapsed = now - self._no_media_since[pid]
                if elapsed >= no_media_timeout:
                    if no_media_enabled:
                        msg = build_message(panel.cfg, "no_media")
                        panel.start(msg, "no_media")
                    else:
                        panel.stop()
                # else: still in grace period, leave media overlay running

    def run(self):
        self._running = True
        poll_interval = float(self._global().get("poll_interval", 1.0))
        log.info("matrixscroller daemon starting (poll=%.1fs)", poll_interval)

        while self._running:
            try:
                self.poll_once()
            except Exception as e:
                log.error("Poll error: %s", e)
            time.sleep(poll_interval)

        log.info("matrixscroller daemon stopped")

    def stop(self):
        self._running = False
        with self._lock:
            for panel in self.panels.values():
                panel.stop()

    def get_status(self) -> dict:
        with self._lock:
            panels_status = [p.status() for p in self.panels.values()]
        return {
            "running": self._running,
            "current_song": self._current_song,
            "panels": panels_status,
        }

    def get_config(self) -> dict:
        return self.config

    def update_config(self, new_cfg: dict):
        save_config(new_cfg)
        self.config = new_cfg
        self._rebuild_panels()

    def get_models(self) -> list:
        host = self._global().get("fpp_host", "localhost")
        return get_fpp_models(host)


# ── REST API ──────────────────────────────────────────────────────────────────

_daemon: Optional[MatrixScrollerDaemon] = None


class ApiHandler(BaseHTTPRequestHandler):

    def log_message(self, fmt, *args):
        log.debug("HTTP %s", fmt % args)

    def _send_json(self, code: int, data):
        body = json.dumps(data, indent=2).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self) -> Optional[dict]:
        length = int(self.headers.get("Content-Length", 0))
        if length == 0:
            return {}
        try:
            return json.loads(self.rfile.read(length))
        except Exception:
            return None

    def do_GET(self):
        path = self.path.split("?")[0].rstrip("/")

        if path == "/api/plugin/matrixscroller/status":
            self._send_json(200, _daemon.get_status())

        elif path == "/api/plugin/matrixscroller/config":
            self._send_json(200, _daemon.get_config())

        elif path == "/api/plugin/matrixscroller/models":
            self._send_json(200, _daemon.get_models())

        else:
            self._send_json(404, {"error": "Not found"})

    def do_POST(self):
        path = self.path.split("?")[0].rstrip("/")

        if path == "/api/plugin/matrixscroller/config":
            body = self._read_json()
            if body is None:
                self._send_json(400, {"error": "Invalid JSON"})
                return
            _daemon.update_config(body)
            self._send_json(200, {"status": "ok"})

        elif path == "/api/plugin/matrixscroller/message":
            # Body: {"panel_id": "panel_1", "message": "Hello!"} or message=null to clear
            body = self._read_json()
            if body is None:
                self._send_json(400, {"error": "Invalid JSON"})
                return
            panel_id = body.get("panel_id")
            message  = body.get("message")  # None clears override
            if not panel_id:
                self._send_json(400, {"error": "panel_id required"})
                return
            _daemon.set_override(panel_id, message)
            self._send_json(200, {"status": "ok", "panel_id": panel_id, "message": message})

        elif path == "/api/plugin/matrixscroller/reload":
            _daemon.reload_config()
            self._send_json(200, {"status": "reloaded"})

        else:
            self._send_json(404, {"error": "Not found"})


def run_api_server():
    server = HTTPServer(("0.0.0.0", API_PORT), ApiHandler)
    log.info("REST API listening on port %d", API_PORT)
    server.serve_forever()


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    global _daemon

    _daemon = MatrixScrollerDaemon()

    # Start REST API in background thread
    api_thread = threading.Thread(target=run_api_server, daemon=True)
    api_thread.start()

    # Handle SIGTERM / SIGINT gracefully
    def handle_signal(sig, frame):
        log.info("Received signal %d, shutting down", sig)
        _daemon.stop()
        sys.exit(0)

    signal.signal(signal.SIGTERM, handle_signal)
    signal.signal(signal.SIGINT, handle_signal)

    _daemon.run()


if __name__ == "__main__":
    main()
