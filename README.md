# fpp-matrixscroller

FPP plugin that reads MP3 metadata from the currently playing sequence and scrolls it across one or more pixel matrix panels using [fpp-matrixtools](https://github.com/FalconChristmas/fpp-matrixtools).

## Features

- **N matrix panels** — each with fully independent configuration
- **Two modes per panel** — media playing vs. no media (with configurable timeout)
- **Configurable message fields** — pre-roll, tune-to, post-roll, gap character (each with enabled checkbox, separate no-media variant)
- **REST API** — get/set config, get status, send manual message overrides (great for Home Assistant automations)
- **Autostart** — starts with FPP daemon, always shows no-media content even before a show begins
- **Web UI** — configure all panels from the FPP interface

## Requirements

- FPP 6.0+
- [fpp-matrixtools](https://github.com/FalconChristmas/fpp-matrixtools) installed
- Python 3.7+
- One or more Pixel Overlay models configured in FPP

## Installation

```bash
# Clone into FPP plugins directory
cd /home/fpp/media/plugins
git clone https://github.com/yourusername/fpp-matrixscroller

# Make scripts executable
chmod +x /home/fpp/media/plugins/fpp-matrixscroller/plugin_event.sh
chmod +x /home/fpp/media/plugins/fpp-matrixscroller/matrixscroller.py

# Create initial config (first run copies from plugin default)
# Config is auto-created at:
#   /home/fpp/media/config/plugin.matrixscroller.json
```

FPP will automatically call `plugin_event.sh fppd_start` when the daemon starts.

## REST API

All endpoints are available at `http://<fpp-ip>:32329/api/plugin/matrixscroller/` or proxied through FPP at `http://<fpp-ip>/api/plugin/matrixscroller/`.

| Method | Path | Description |
|--------|------|-------------|
| GET | `/status` | Current state of all panels |
| GET | `/config` | Full configuration |
| POST | `/config` | Update configuration (JSON body) |
| GET | `/models` | Available FPP pixel overlay models |
| POST | `/message` | Send manual text override to a panel |
| POST | `/reload` | Reload config from disk |

### Message Override (Home Assistant example)

```json
POST /api/plugin/matrixscroller/message
{
  "panel_id": "panel_1",
  "message": "Welcome to the show!"
}
```

Clear override (returns to metadata mode):
```json
{
  "panel_id": "panel_1",
  "message": null
}
```

## Message Assembly

When media is playing, the scroll message is built from enabled fields:

```
[pre_roll] [gap] [tune_to] [gap] <Artist - Title> [gap] [post_roll]
```

Only enabled fields are included. Gap is inserted between each present field.

When no media has been playing for longer than `no_media_timeout` seconds, the no-media variants of each field are used (with no song title injected).

## Config Structure

```json
{
  "global": {
    "fpp_host": "localhost",
    "poll_interval": 1.0,
    "no_media_timeout": 5.0,
    "matrixtools_path": "/home/fpp/media/plugins/fpp-matrixtools/scripts/matrixtools"
  },
  "panels": [
    {
      "id": "panel_1",
      "name": "Panel 1",
      "enabled": true,
      "model": "Matrix1",
      "color": "#ff0000",
      "font": "Helvetica",
      "fontsize": 10,
      "position": "R2L",
      "pixelspersecond": 15,
      "media": {
        "pre_roll": { "enabled": false, "text": "" },
        "tune_to":  { "enabled": true,  "text": "Tune To 107.9" },
        "post_roll": { "enabled": false, "text": "" },
        "gap":      { "enabled": true,  "text": " | " }
      },
      "no_media": {
        "pre_roll": { "enabled": false, "text": "" },
        "tune_to":  { "enabled": true,  "text": "Tune To 107.9" },
        "post_roll": { "enabled": false, "text": "" },
        "gap":      { "enabled": true,  "text": " | " }
      }
    }
  ]
}
```

## Logs

```bash
tail -f /home/fpp/media/logs/matrixscroller.log
```
