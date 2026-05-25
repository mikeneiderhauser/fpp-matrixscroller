# fpp-matrixscroller REST API

All endpoints are proxied through FPP at:

```
http://<fpp-ip>/api/plugin/fpp-matrixscroller/<endpoint>
```

The plugin daemon listens directly on port `32329` if you want to bypass the FPP proxy:

```
http://<fpp-ip>:32329/api/plugin/matrixscroller/<endpoint>
```

---

## Status

### `GET /status`

Returns the current running state of the daemon and all configured panels.

**Response**
```json
{
  "running": true,
  "current_song": "Artist - Title",
  "media_meta": {
    "title": "Title",
    "artist": "Artist",
    "album": "Album",
    "genre": "Genre",
    "date": "2024"
  },
  "panels": [
    {
      "id": "panel_1",
      "name": "Panel 1",
      "enabled": true,
      "model": "YardMatrix",
      "color": "#ff0000",
      "mode": "media",
      "message": "Title - Artist",
      "song_key": "MySong",
      "running": true,
      "scroll_sec": 12.4,
      "scroll_elapsed": 3.1,
      "scroll_measured": true
    }
  ]
}
```

**Panel `mode` values**

| Value | Meaning |
|-------|---------|
| `media` | Media is playing, song info is scrolling |
| `no_media` | No media for longer than `no_media_timeout` seconds |
| `override` | A manual message override is active |
| `""` | Panel stopped / daemon just started |

---

## Configuration

### `GET /config`

Returns the full active configuration.

**Response**
```json
{
  "global": {
    "enable_output": true,
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
      "model": "YardMatrix",
      "color": "#ff0000",
      "font": "DejaVuSans",
      "fontsize": 10,
      "position": "R2L",
      "pixelspersecond": 15,
      "media": {
        "enabled": true,
        "pre_roll":  { "enabled": false, "text": "" },
        "tune_to":   { "enabled": true,  "text": "Tune To:" },
        "artist":    { "enabled": true },
        "title":     { "enabled": true },
        "album":     { "enabled": false },
        "post_roll": { "enabled": false, "text": "" },
        "gap":       { "enabled": true,  "text": " | " }
      },
      "no_media": {
        "enabled": true,
        "pre_roll":  { "enabled": false, "text": "" },
        "tune_to":   { "enabled": true,  "text": "Tune To:" },
        "post_roll": { "enabled": false, "text": "" },
        "gap":       { "enabled": true,  "text": " | " }
      },
      "song_overrides": {
        "MySong": {
          "enabled": true,
          "color": "#00ff00",
          "font": "DejaVuSans",
          "fontsize": 12,
          "position": "L2R",
          "pixelspersecond": 20,
          "artist": "Override Artist",
          "title": "Override Title",
          "album": ""
        }
      }
    }
  ]
}
```

---

### `POST /config`

Replace and save the full configuration. Triggers an immediate panel rebuild.

**Request body:** same schema as the `GET /config` response.

**Response**
```json
{ "status": "ok" }
```

---

### `POST /reload`

Reload configuration from disk without restarting the daemon. Useful after editing the config file directly.

**Request body:** none required.

**Response**
```json
{ "status": "reloaded" }
```

---

## Output Toggle

### `POST /output`

Enable or disable all overlay output without a full config round-trip. Equivalent to toggling the **Enable Output** checkbox in the web UI.

**Request body**
```json
{ "enable": true }
```

**Response**
```json
{ "status": "ok", "enable_output": true }
```

> When disabled, all panel subprocesses are stopped and the matrix is cleared. Config is preserved — re-enabling resumes immediately on the next poll.

---

## Message Overrides

### `POST /message`

Send or clear a manual text override on a specific panel. While an override is active the panel ignores normal media/no-media logic.

**Request body**
```json
{
  "panel_id": "panel_1",
  "message": "Welcome to the show!"
}
```

Clear override (returns panel to normal song display):
```json
{
  "panel_id": "panel_1",
  "message": null
}
```

**Response**
```json
{
  "status": "ok",
  "panel_id": "panel_1",
  "message": "Welcome to the show!"
}
```

---

### `POST /message/all`

Send or clear the same manual override on **every configured panel** at once.

**Request body**
```json
{ "message": "Welcome to the show!" }
```

Clear all overrides:
```json
{ "message": null }
```

**Response**
```json
{
  "status": "ok",
  "panels": ["panel_1", "panel_2"],
  "message": "Welcome to the show!"
}
```

---

## Models & Fonts

### `GET /models`

Returns the list of pixel overlay models available in FPP.

**Response**
```json
[
  { "Name": "YardMatrix", "Width": 64, "Height": 16, "ChannelCount": 3072 },
  { "Name": "SidePanel",  "Width": 32, "Height": 16, "ChannelCount": 1536 }
]
```

---

### `GET /fonts`

Returns the list of fonts available in fpp-matrixtools.

**Response**
```json
["DejaVuSans", "FreeSans", "NimbusSans-Regular"]
```

---

### `GET /music`

Returns the list of music files available in FPP.

**Response**
```json
{
  "files": [
    { "name": "MySong.mp3" },
    { "name": "AnotherSong.mp3" }
  ]
}
```

---

## Daemon Control

### `GET /daemon/start`

Start the daemon if it is not already running. No-op if already running.

**Response**
```json
{ "status": "running" }
```

| `status` value | Meaning |
|----------------|---------|
| `running` | Daemon was already running |
| `already_running` | Daemon responded before launch attempt |
| `starting` | Process launched but not yet responding |

---

### `POST /daemon/restart`

Restart the daemon in-place (`os.execv`). The HTTP response is sent before the process re-execs, so the connection will close — allow ~2 seconds before polling `/status`.

**Response** *(sent before restart)*
```json
{ "status": "restarting" }
```

---

### `POST /daemon/stop`

Stop the daemon gracefully (`SIGTERM`). The HTTP response is sent before shutdown.

**Response** *(sent before stop)*
```json
{ "status": "stopping" }
```

---

## Config Backup & Restore

Backup files are stored alongside the active config:
```
/home/fpp/media/config/plugin.fpp-matrixscroller.backup.YYYYMMDD-HHMMSS.json
```

### `GET /backups`

List all available backup files, newest first.

**Response**
```json
[
  "plugin.fpp-matrixscroller.backup.20260101-220000.json",
  "plugin.fpp-matrixscroller.backup.20251201-180000.json"
]
```

---

### `POST /backup`

Create a new timestamped backup of the current config.

**Request body:** none required.

**Response**
```json
{ "status": "ok", "filename": "plugin.fpp-matrixscroller.backup.20260101-220000.json" }
```

---

### `GET /backup/download?filename=<name>`

Return the contents of a specific backup file as JSON.

**Query parameter:** `filename` — the exact filename from `GET /backups`.

**Response:** the full config JSON of that backup.

**Error (404)**
```json
{ "error": "Backup not found or invalid filename" }
```

---

### `POST /restore`

Restore config from a backup file. Applies immediately and triggers a panel rebuild.

**Request body**
```json
{ "filename": "plugin.fpp-matrixscroller.backup.20260101-220000.json" }
```

**Response**
```json
{ "status": "ok", "filename": "plugin.fpp-matrixscroller.backup.20260101-220000.json" }
```

**Error (400)**
```json
{ "error": "Invalid or missing backup file" }
```

---

### `POST /backup/delete`

Delete a single backup file.

**Request body**
```json
{ "filename": "plugin.fpp-matrixscroller.backup.20260101-220000.json" }
```

**Response**
```json
{ "status": "ok", "filename": "plugin.fpp-matrixscroller.backup.20260101-220000.json" }
```

---

### `POST /backup/delete-all`

Delete all backup files.

**Request body:** none required.

**Response**
```json
{ "status": "ok", "deleted": 3 }
```

---

## Error Responses

All endpoints return JSON. Common error shapes:

```json
{ "error": "matrixscroller daemon not running" }   // 200 — daemon offline
{ "error": "Invalid JSON" }                         // 400
{ "error": "panel_id required" }                    // 400
{ "error": "enable field required" }                // 400
{ "error": "Invalid or missing backup file" }       // 400
{ "error": "Backup not found or invalid filename" } // 404
{ "error": "daemon not initialized" }               // 503
```

> **Note:** When the daemon is offline, the FPP PHP proxy returns `{ "error": "matrixscroller daemon not running" }` with HTTP 200 rather than a 5xx. Check for the `error` key in addition to HTTP status.
