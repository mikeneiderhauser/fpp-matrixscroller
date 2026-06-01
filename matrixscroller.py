#!/usr/bin/env python3
"""
fpp-matrixscroller daemon
Watches FPP status and drives pixel overlay text effects on N matrix panels
using FPP's native Overlay Model Effect command API directly.
Exposes a REST API on port 32329 for config and status.
"""

import json
import logging
import os
import signal
import sys
import threading
import time
import unicodedata
import urllib.request
import urllib.error
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Dict, Optional
from urllib.parse import unquote, quote, parse_qs

# ── Paths ────────────────────────────────────────────────────────────────────
PLUGIN_DIR   = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH  = "/home/fpp/media/config/plugin.fpp-matrixscroller.json"
DEFAULT_CFG  = os.path.join(PLUGIN_DIR, "config.json")
LOG_PATH     = "/home/fpp/media/logs/fpp-matrixscroller.log"
API_PORT     = 32329

# ── Logging ──────────────────────────────────────────────────────────────────
os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.FileHandler(LOG_PATH)],
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


def fpp_post_command(host: str, payload: dict) -> Optional[dict]:
    """POST to FPP's /api/command endpoint. Returns parsed response or None on error."""
    url  = f"http://{host}/api/command"
    data = json.dumps(payload).encode()
    try:
        req = urllib.request.Request(
            url, data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=3.0) as resp:
            body = resp.read()
            try:
                return json.loads(body) or {}
            except Exception:
                return {}  # non-JSON response is still a success
    except Exception as e:
        log.debug("FPP command POST failed: %s", e)
        return None


def fpp_put(host: str, path: str, payload: dict) -> bool:
    """PUT JSON to a FPP API path. Returns True on success."""
    url  = f"http://{host}{path}"
    data = json.dumps(payload).encode()
    try:
        req = urllib.request.Request(
            url, data=data,
            headers={"Content-Type": "application/json"},
            method="PUT",
        )
        with urllib.request.urlopen(req, timeout=3.0):
            return True
    except Exception as e:
        log.debug("FPP PUT %s failed: %s", path, e)
        return False


def get_fpp_media_meta(host: str, filename: str) -> dict:
    """Return format.tags dict from FPP's ffprobe endpoint for a media file."""
    encoded = quote(filename, safe='')
    data = fpp_get(host, f"/api/media/{encoded}/meta", timeout=5.0)
    if isinstance(data, dict):
        return data.get("format", {}).get("tags", {})
    return {}


def _parse_time_str(t) -> float:
    """Parse 'M:SS' or 'H:MM:SS' string to seconds. Returns 0.0 on failure."""
    try:
        parts = [int(x) for x in str(t).split(':')]
        if len(parts) == 3:
            return parts[0] * 3600 + parts[1] * 60 + parts[2]
        if len(parts) == 2:
            return parts[0] * 60 + parts[1]
    except Exception:
        pass
    return 0.0


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
        artist_en = fields.get("artist", {}).get("enabled", True)
        title_en  = fields.get("title",  {}).get("enabled", True)
        album_en  = fields.get("album",  {}).get("enabled", False)
        if title_en and metadata.get("title"):
            song_parts.append(metadata["title"])
        if artist_en and metadata.get("artist"):
            song_parts.append(metadata["artist"])
        if album_en and metadata.get("album"):
            song_parts.append(metadata["album"])
        # Use filename fallback only when a song-identity field is enabled but
        # the MP3 has no embedded ID3 tags for any of them.
        if not song_parts and (artist_en or title_en) and metadata.get("fallback"):
            song_parts.append(metadata["fallback"])
        if song_parts:
            parts.append(" - ".join(song_parts))

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
        self._lock = threading.Lock()
        self.current_message = ""
        self.current_mode = ""
        self.current_song_key = ""
        self._last_cmd_sig = ""
        self._last_sent_at: float = 0.0
        self._est_scroll_sec: float = 0.0
        self._measured_scroll_sec: float = 0.0
        self._effect_active: bool = False

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

    def _build_effect_payload(self, message: str, overrides: dict = None,
                              est_scroll_sec: float = 0.0) -> dict:
        """Build the FPP 'Overlay Model Effect' command payload.

        FPP's Text effect scrolls once and stops; it does not loop.
        duration is set to est_scroll_sec + 15s so FPP keeps the overlay
        active long enough for our timing loop to re-send before it expires.
        """
        cfg = self.cfg
        ov  = overrides or {}
        # Give FPP enough runway for one full pass plus a generous buffer so
        # the effect never expires before our daemon re-sends.
        duration = str(max(30, int(est_scroll_sec) + 15))
        return {
            "command": "Overlay Model Effect",
            "args": [
                cfg.get("model", ""),
                "true",   # autoenable
                "Text",
                ov.get("color")               or cfg.get("color",           "#ff0000"),
                ov.get("font")                or cfg.get("font",            "DejaVuSans"),
                str(ov.get("fontsize")        or cfg.get("fontsize",        10)),
                "false",  # anti-alias
                ov.get("position")            or cfg.get("position",        "R2L"),
                str(ov.get("pixelspersecond") or cfg.get("pixelspersecond", 15)),
                duration,
                # Only inject TextMode arg when non-default so this plugin remains
                # usable on unpatched FPP (which expects Text at args[7], not args[8]).
                # A patched FPP binary is required to use 90CW, 270CW, or Vert.
                *([ov.get("text_mode") or cfg.get("text_mode", "H"), message]
                  if (ov.get("text_mode") or cfg.get("text_mode", "H")) != "H"
                  else [message]),
            ]
        }

    def _stop_effect(self):
        """Stop any running effect and disable the overlay model."""
        host  = self.gcfg.get("fpp_host", "localhost")
        model = self.cfg.get("model", "")
        if not model:
            return
        # Stop the running effect so FPP destroys the TextMovementEffect object.
        # Without this, FPP reuses the effect and carries over stale x/y position
        # on the next send, causing text to start mid-scroll instead of from the edge.
        fpp_post_command(host, {
            "command": "Overlay Model Effect",
            "args": [model, "false", "Stop Effects"],
        })
        fpp_put(host, f"/api/overlays/model/{quote(model, safe='')}/state", {"State": 0})

    def _calc_scroll_sec(self, message: str, overrides: dict, model_widths: dict = None, model_heights: dict = None) -> float:
        """Estimate seconds for one full scroll pass of message across the matrix."""
        cfg        = self.cfg
        ov         = overrides or {}
        fontsize   = int(ov.get("fontsize") or cfg.get("fontsize", 10))
        pps        = max(1.0, float(ov.get("pixelspersecond") or cfg.get("pixelspersecond", 15)))
        position   = str(ov.get("position") or cfg.get("position", "R2L"))
        text_mode  = str(ov.get("text_mode") or cfg.get("text_mode", "H"))
        model_name = cfg.get("model", "")
        matrix_w   = float((model_widths  or {}).get(model_name) or 256)
        matrix_h   = float((model_heights or {}).get(model_name) or 256)

        if text_mode == "Vert":
            # Each character occupies its own line; travel distance is numChars *
            # line height + the panel height (scroll direction expected to be B2T).
            n = max(1, len(message))
            return (n * fontsize + matrix_h) / pps

        if text_mode in ("90CW", "270CW"):
            # After rotation the bitmap is transposed: its "rows" dimension equals
            # the original text width, its "cols" dimension equals the font height.
            if position in ("B2T", "T2B"):
                # Scroll vertically through the rotated text width.
                travel = len(message) * fontsize * 0.65 + matrix_h
            else:
                # Scroll horizontally through the rotated text height (≈ fontsize).
                travel = fontsize + matrix_w
            return travel / pps

        if position in ("B2T", "T2B"):
            return (fontsize + matrix_h) / pps
        msg_px = len(message) * fontsize * 0.65
        return (msg_px + matrix_w) / pps

    def start(self, message: str, mode: str, song_key: str = "", seconds_remaining: float = 0.0, model_widths: dict = None, model_heights: dict = None):
        """Send the scroll command, looping when the previous pass is estimated to have finished."""
        with self._lock:
            if not self.cfg.get("enabled", True):
                return

            overrides = self._get_song_overrides(song_key) if mode == "media" else {}

            # Song override can disable this panel for a specific song
            if mode == "media" and overrides.get("enabled") is False:
                self._stop_effect()
                self.current_message = ""
                self.current_mode = mode
                self.current_song_key = song_key
                self._last_sent_at = 0.0
                self._effect_active = False
                return

            model = self.cfg.get("model", "")
            if not model:
                log.warning("Panel '%s' has no model set, skipping", self.cfg.get("name"))
                return
            if not message:
                log.debug("Panel '%s' empty message, clearing", self.cfg.get("name"))
                self._stop_effect()
                self.current_message = ""
                self.current_mode = mode
                self.current_song_key = song_key
                self._last_sent_at = 0.0
                self._effect_active = False
                return

            cfg = self.cfg
            ov  = overrides or {}
            cmd_sig = "|".join(str(x) for x in [
                ov.get("color")           or cfg.get("color",           "#ff0000"),
                ov.get("font")            or cfg.get("font",            "DejaVuSans"),
                ov.get("fontsize")        or cfg.get("fontsize",        10),
                ov.get("position")        or cfg.get("position",        "R2L"),
                ov.get("pixelspersecond") or cfg.get("pixelspersecond", 15),
            ])

            now = time.monotonic()
            content_changed = (
                message  != self.current_message or
                mode     != self.current_mode    or
                song_key != self.current_song_key or
                cmd_sig  != self._last_cmd_sig
            )

            if content_changed:
                # New content: always resend; reset per-song scroll measurements
                self._measured_scroll_sec = 0.0
            else:
                # Same content: only resend when the previous scroll pass has finished.
                # Use the measured duration from the first loop if available, else the estimate.
                scroll_sec = self._measured_scroll_sec or self._est_scroll_sec
                if scroll_sec <= 0 or self._last_sent_at == 0:
                    return  # Still on first pass — nothing to loop yet

                elapsed = now - self._last_sent_at
                # 1-second gap after scroll completes before restarting
                if elapsed < scroll_sec + 1.0:
                    return

                # Don't start a pass that won't complete before the song ends
                if seconds_remaining > 0 and seconds_remaining < scroll_sec:
                    log.debug("Panel '%s' skipping loop — %.1fs remaining < %.1fs scroll",
                              cfg.get("name"), seconds_remaining, scroll_sec)
                    return

                # Measure actual scroll duration from the first completed loop
                if self._measured_scroll_sec == 0:
                    self._measured_scroll_sec = max(1.0, elapsed - 1.0)
                    log.info("Panel '%s' measured scroll: %.1fs per pass",
                             cfg.get("name"), self._measured_scroll_sec)

            self._est_scroll_sec = self._calc_scroll_sec(message, ov, model_widths, model_heights)
            log.info("Panel '%s' [%s] song=%r est=%.1fs: %s",
                     cfg.get("name"), mode, song_key or "—", self._est_scroll_sec, message)
            host    = self.gcfg.get("fpp_host", "localhost")
            # Always stop any running effect first so FPP creates a fresh
            # TextMovementEffect with correct starting position on the next send.
            self._stop_effect()
            payload = self._build_effect_payload(message, overrides, self._est_scroll_sec)
            if fpp_post_command(host, payload) is not None:
                self.current_message = message
                self.current_mode = mode
                self.current_song_key = song_key
                self._last_cmd_sig = cmd_sig
                self._last_sent_at = now
                self._effect_active = True
            else:
                log.error("Failed to send overlay command for panel '%s'", cfg.get("name"))

    def stop(self):
        with self._lock:
            self._stop_effect()
            self.current_message = ""
            self.current_mode = ""
            self.current_song_key = ""
            self._last_cmd_sig = ""
            self._last_sent_at = 0.0
            self._est_scroll_sec = 0.0
            self._measured_scroll_sec = 0.0
            self._effect_active = False

    def status(self) -> dict:
        with self._lock:
            running = self._effect_active
            raw_elapsed = (time.monotonic() - self._last_sent_at) if self._last_sent_at else 0.0
            scroll_sec = self._measured_scroll_sec or self._est_scroll_sec
            elapsed = min(raw_elapsed, scroll_sec) if scroll_sec > 0 else raw_elapsed
            overrides = self._get_song_overrides(self.current_song_key) if self.current_mode == "media" else {}
            active_color = overrides.get("color") or self.cfg.get("color", "#ff0000")
        return {
            "id": self.cfg.get("id"),
            "name": self.cfg.get("name"),
            "enabled": self.cfg.get("enabled", True),
            "model": self.cfg.get("model", ""),
            "color": active_color,
            "mode": self.current_mode,
            "message": self.current_message,
            "song_key": self.current_song_key,
            "running": running,
            "scroll_sec": round(scroll_sec, 1),
            "scroll_elapsed": round(elapsed, 1),
            "scroll_measured": self._measured_scroll_sec > 0,
        }

    def force_resend(self):
        """Thread-safe reset so the next poll triggers a fresh send."""
        with self._lock:
            self.current_message = ""

    def update_cfg(self, panel_cfg: dict, global_cfg: dict = None):
        with self._lock:
            self.cfg = panel_cfg
            if global_cfg is not None:
                self.gcfg = global_cfg
            self._stop_effect()
            self.current_message = ""
            self.current_mode = ""
            self.current_song_key = ""
            self._last_cmd_sig = ""
            self._last_sent_at = 0.0
            self._est_scroll_sec = 0.0
            self._measured_scroll_sec = 0.0
            self._effect_active = False


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
        self._model_widths: Dict[str, int] = {}   # model name → pixel width from FPP
        self._model_heights: Dict[str, int] = {}  # model name → pixel height from FPP
        self._model_widths_at: float = 0.0
        self._media_meta: dict = {}               # format.tags for current song
        self._media_meta_key: str = ""            # song_key for which meta was fetched
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
                    self.panels[pid].update_cfg(pcfg, self._global())
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
            self.panels[panel_id].force_resend()

    def _get_current_song_key(self, status: dict) -> str:
        """Return the current media filename without extension for song_overrides lookup."""
        for field in ("current_song", "current_sequence"):
            val = (status.get(field) or "").strip()
            if val:
                return os.path.splitext(os.path.basename(unquote(val)))[0]
        return ""

    def _get_metadata(self, status: dict, file_tags: dict = None) -> dict:
        """Extract and sanitize metadata, preferring file_tags over status.mediameta."""
        # file_tags come from /api/media/{file}/meta (ffprobe) and are more complete
        meta   = file_tags or status.get("mediameta", {}) or {}
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
        if not self._global().get("enable_output", True):
            for panel in self.panels.values():
                panel.stop()
            return

        host = self._global().get("fpp_host", "localhost")
        no_media_timeout = float(self._global().get("no_media_timeout", 5.0))

        # Refresh model widths from FPP every 60 s
        pre = time.monotonic()
        if pre - self._model_widths_at > 60:
            fpp_models = get_fpp_models(host)
            self._model_widths = {}
            self._model_heights = {}
            for m in fpp_models:
                if not isinstance(m, dict):
                    continue
                name = m.get("Name") or m.get("name", "")
                w = int(m.get("Width") or m.get("width") or 0)
                if not name or not w:
                    continue
                self._model_widths[name] = w
                cc  = int(m.get("ChannelCount") or m.get("channelCount") or 0)
                cpn = int(m.get("ChannelCountPerNode") or m.get("channelCountPerNode") or 3)
                h = int(cc / cpn / w) if (cc and cpn) else int(m.get("Height") or m.get("height") or 0)
                if h:
                    self._model_heights[name] = h
            self._model_widths_at = pre
            if self._model_widths:
                log.debug("Model widths: %s", self._model_widths)

        status = get_fpp_status(host)
        if status is None:
            return  # FPP unreachable, leave current state

        now = time.monotonic()  # captured after network calls to avoid overstating no-media elapsed

        playing  = self._is_playing(status)
        song_key = self._get_current_song_key(status) if playing else ""

        # When the song changes, fetch richer file-level tags from FPP's ffprobe endpoint.
        # status.mediameta is often empty; /api/media/{file}/meta has full ID3/vorbis tags.
        if playing and song_key and song_key != self._media_meta_key:
            filename = (status.get("current_song") or status.get("current_sequence") or "").strip()
            if filename:
                tags = get_fpp_media_meta(host, os.path.basename(unquote(filename)))
                self._media_meta = tags
                log.info("Fetched media meta for '%s': %s", song_key,
                         {k: v for k, v in tags.items() if k in ("title","artist","album","genre","date")})
            else:
                self._media_meta = {}
            self._media_meta_key = song_key
        elif not playing:
            self._media_meta = {}
            self._media_meta_key = ""

        metadata = self._get_metadata(status, self._media_meta) if playing else {}
        # Parse from the formatted string — seconds_remaining can be a playlist-level
        # counter that doesn't reflect the current song's remaining time.
        seconds_remaining = _parse_time_str(status.get("time_remaining", "")) or \
                            float(status.get("seconds_remaining", 0))
        has_content = playing and bool(
            metadata.get("artist") or metadata.get("title") or metadata.get("fallback")
        )

        if has_content:
            a, t = metadata.get("artist", ""), metadata.get("title", "")
            self._current_song = f"{a} - {t}" if a and t else t or a or metadata.get("fallback", "")
        else:
            self._current_song = ""

        with self._lock:
            panels_snapshot = list(self.panels.items())
            overrides = dict(self._message_overrides)

        for pid, panel in panels_snapshot:
            # Manual override wins
            override = overrides.get(pid)
            if override is not None:
                panel.start(override, "override", model_widths=self._model_widths, model_heights=self._model_heights)
                continue

            media_enabled    = panel.cfg.get("media",    {}).get("enabled", True)
            no_media_enabled = panel.cfg.get("no_media", {}).get("enabled", True)

            if has_content:
                # Reset no-media timer
                self._no_media_since[pid] = None
                if media_enabled:
                    meta_for_panel = dict(metadata)
                    so = panel._get_song_overrides(song_key) if song_key else {}
                    for field in ("artist", "title", "album"):
                        if so.get(field):
                            meta_for_panel[field] = _sanitize_text(so[field])
                    msg = build_message(panel.cfg, "media", meta_for_panel)
                    panel.start(msg, "media", song_key, seconds_remaining, self._model_widths, self._model_heights)
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
                        panel.start(msg, "no_media", model_widths=self._model_widths, model_heights=self._model_heights)
                    else:
                        panel.stop()
                # else: still in grace period, leave media overlay running

    def run(self):
        self._running = True
        log.info("matrixscroller daemon starting")

        while self._running:
            poll_interval = float(self._global().get("poll_interval", 1.0))
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
            "media_meta": self._media_meta,
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

    def list_backups(self) -> list:
        prefix = "plugin.fpp-matrixscroller.backup."
        d = os.path.dirname(CONFIG_PATH)
        try:
            files = [f for f in os.listdir(d)
                     if f.startswith(prefix) and f.endswith(".json")]
            return sorted(files, reverse=True)
        except Exception:
            return []

    def create_backup(self) -> str:
        ts = time.strftime("%Y%m%d-%H%M%S")
        filename = f"plugin.fpp-matrixscroller.backup.{ts}.json"
        path = os.path.join(os.path.dirname(CONFIG_PATH), filename)
        os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
        with open(path, "w") as f:
            json.dump(self.config, f, indent=4)
        log.info("Config backed up to %s", path)
        return filename

    def get_backup_content(self, filename: str) -> Optional[dict]:
        if (not filename.startswith("plugin.fpp-matrixscroller.backup.")
                or "/" in filename or ".." in filename
                or not filename.endswith(".json")):
            return None
        path = os.path.join(os.path.dirname(CONFIG_PATH), filename)
        if not os.path.exists(path):
            return None
        try:
            with open(path) as f:
                return json.load(f)
        except Exception:
            return None

    def delete_backup(self, filename: str) -> bool:
        if (not filename.startswith("plugin.fpp-matrixscroller.backup.")
                or "/" in filename or ".." in filename
                or not filename.endswith(".json")):
            return False
        path = os.path.join(os.path.dirname(CONFIG_PATH), filename)
        if not os.path.exists(path):
            return False
        try:
            os.remove(path)
            log.info("Backup deleted: %s", path)
            return True
        except Exception as e:
            log.error("Failed to delete backup %s: %s", filename, e)
            return False

    def set_output(self, enabled: bool):
        """Enable or disable overlay output without a full config round-trip."""
        self.config.setdefault("global", {})["enable_output"] = enabled
        save_config(self.config)
        log.info("Output %s", "enabled" if enabled else "disabled")

    def set_override_all(self, message: Optional[str]) -> list:
        """Set or clear a manual message override on every configured panel."""
        with self._lock:
            panel_ids = list(self.panels.keys())
            for panel_id in panel_ids:
                self._message_overrides[panel_id] = message
        for panel in self.panels.values():
            panel.force_resend()
        return panel_ids

    def delete_all_backups(self) -> int:
        count = sum(1 for f in self.list_backups() if self.delete_backup(f))
        log.info("Deleted %d backup(s)", count)
        return count

    def restore_backup(self, filename: str) -> bool:
        if (not filename.startswith("plugin.fpp-matrixscroller.backup.")
                or "/" in filename or ".." in filename
                or not filename.endswith(".json")):
            return False
        path = os.path.join(os.path.dirname(CONFIG_PATH), filename)
        if not os.path.exists(path):
            return False
        try:
            with open(path) as f:
                cfg = json.load(f)
            self.update_config(cfg)
            log.info("Config restored from %s", path)
            return True
        except Exception as e:
            log.error("Failed to restore backup %s: %s", filename, e)
            return False


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

        if _daemon is None:
            self._send_json(503, {"error": "daemon not initialized"})
            return

        if path == "/api/plugin/matrixscroller/status":
            self._send_json(200, _daemon.get_status())

        elif path == "/api/plugin/matrixscroller/config":
            self._send_json(200, _daemon.get_config())

        elif path == "/api/plugin/matrixscroller/models":
            self._send_json(200, _daemon.get_models())

        elif path == "/api/plugin/matrixscroller/backups":
            self._send_json(200, _daemon.list_backups())

        elif path == "/api/plugin/matrixscroller/backup/download":
            qs = parse_qs(self.path.split("?", 1)[1]) if "?" in self.path else {}
            filename = qs.get("filename", [""])[0]
            content = _daemon.get_backup_content(filename)
            if content is None:
                self._send_json(404, {"error": "Backup not found or invalid filename"})
            else:
                self._send_json(200, content)

        else:
            self._send_json(404, {"error": "Not found"})

    def do_POST(self):
        path = self.path.split("?")[0].rstrip("/")

        if _daemon is None:
            self._send_json(503, {"error": "daemon not initialized"})
            return

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

        elif path == "/api/plugin/matrixscroller/backup":
            filename = _daemon.create_backup()
            self._send_json(200, {"status": "ok", "filename": filename})

        elif path == "/api/plugin/matrixscroller/restore":
            body = self._read_json()
            if body is None:
                self._send_json(400, {"error": "Invalid JSON"})
                return
            filename = body.get("filename", "")
            if _daemon.restore_backup(filename):
                self._send_json(200, {"status": "ok", "filename": filename})
            else:
                self._send_json(400, {"error": "Invalid or missing backup file"})

        elif path == "/api/plugin/matrixscroller/backup/delete":
            body = self._read_json()
            if body is None:
                self._send_json(400, {"error": "Invalid JSON"})
                return
            filename = body.get("filename", "")
            if _daemon.delete_backup(filename):
                self._send_json(200, {"status": "ok", "filename": filename})
            else:
                self._send_json(400, {"error": "Invalid or missing backup file"})

        elif path == "/api/plugin/matrixscroller/backup/delete-all":
            count = _daemon.delete_all_backups()
            self._send_json(200, {"status": "ok", "deleted": count})

        elif path == "/api/plugin/matrixscroller/output":
            body = self._read_json()
            if body is None or "enable" not in body:
                self._send_json(400, {"error": "enable field required"})
                return
            _daemon.set_output(bool(body["enable"]))
            self._send_json(200, {"status": "ok", "enable_output": bool(body["enable"])})

        elif path == "/api/plugin/matrixscroller/message/all":
            body = self._read_json()
            if body is None:
                self._send_json(400, {"error": "Invalid JSON"})
                return
            message = body.get("message")  # None clears all overrides
            panels = _daemon.set_override_all(message)
            self._send_json(200, {"status": "ok", "panels": panels, "message": message})

        elif path == "/api/plugin/matrixscroller/daemon/stop":
            self._send_json(200, {"status": "stopping"})
            threading.Thread(
                target=lambda: (time.sleep(0.5), os.kill(os.getpid(), signal.SIGTERM)),
                daemon=True,
            ).start()

        elif path == "/api/plugin/matrixscroller/daemon/restart":
            self._send_json(200, {"status": "restarting"})
            threading.Thread(
                target=lambda: (time.sleep(0.5), os.execv(sys.executable, [sys.executable] + sys.argv)),
                daemon=True,
            ).start()

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
