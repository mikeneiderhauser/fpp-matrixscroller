# fpp-matrixscroller

FPP plugin that reads MP3 metadata from the currently playing sequence and scrolls it across one or more pixel matrix panels using FPP's native Overlay Model Effect API.

## Features

- **N matrix panels** — each with fully independent configuration
- **Two modes per panel** — Media Playing and Media Idle (with configurable timeout)
- **Configurable message fields** — Pre-Roll, Tune To, Song Info, Post-Roll, Gap separator; each independently enabled per mode
- **Song info order** — Title · Artist · Album, joined with ` - `; each field individually enabled
- **Per-song overrides** — override color, font, direction, speed, and artist/title/album text for specific songs; or suppress the overlay entirely for a song
- **Repeat delay** — configurable per-panel pause between scroll repetitions (default 0 s)
- **Immediate media transitions** — stops the current effect and restarts immediately when the song changes; switches to no-media as soon as the current effect finishes rather than leaving the matrix dark
- **Enable Output toggle** — suppress all overlay effects without stopping the daemon
- **Daemon controls** — Start, Stop, and Restart the daemon from the web UI
- **Config Snapshots** — save named snapshots (pre-filled with a timestamp), download/upload config as JSON, restore from any saved snapshot
- **REST API** — get/set config, status, manual message overrides, version info (useful for Home Assistant automations)
- **Autostart** — starts automatically on install and on every FPP daemon start via `plugin_event.sh`
- **Web UI** — configure all panels from the FPP plugin page; honors FPP's dark/light mode setting; git commit shown in page footer
- **Log level integration** — respects FPP's **Settings → Logs → Plugin** log level; set to `Debug` for verbose output, `Info` for quiet operation

## Requirements

- FPP 8.0+ (primarily tested on FPP 10)
- Python 3.7+
- One or more Pixel Overlay models configured in FPP

## Installation

### Option 1 — FPP Plugin Manager (once listed)

1. In the FPP web UI go to **Content Setup → Plugin Manager**
2. Find **fpp-matrixscroller** in the available plugins list and click **Install**

### Option 2 — FPP Plugin Manager (manual URL)

1. In the FPP web UI go to **Content Setup → Plugin Manager**
2. Click **Add Plugin from URL** and enter:
   ```
   https://raw.githubusercontent.com/mikeneiderhauser/fpp-matrixscroller/master/pluginInfo.json
   ```
3. Click **Install**

### Option 3 — Manual clone

```bash
cd /home/fpp/media/plugins
git clone https://github.com/mikeneiderhauser/fpp-matrixscroller
bash /home/fpp/media/plugins/fpp-matrixscroller/scripts/fpp_install.sh
```

---

In all cases, `fpp_install.sh` deploys the playlist scripts, creates the log and config directories, and starts the daemon. On subsequent boots FPP calls `plugin_event.sh fppd_start` to restart it automatically.

Config is stored at:
```
/home/fpp/media/config/plugin.fpp-matrixscroller.json
```
On first run the plugin falls back to the bundled `config.json` defaults.

## Web UI

Open the plugin page in FPP's web interface. The UI includes:

- **FPP Status Bar** — current song, progress bar, and embedded ID3 tags
- **Panel Status** — live mode badge, active message, and manual message override per panel
- **Panels** — full per-panel config including display settings, message fields, and per-song overrides
- **Global Settings** — FPP host, poll interval, media idle timeout, Enable Output toggle
- **Daemon Control** — Start / Restart / Stop with live Online/Offline badge
- **Config Snapshots** — save a named snapshot (timestamp pre-filled), download the current config as JSON, upload a JSON file to restore, or select a previous snapshot and restore it

The current git commit hash is shown in the page footer for version identification.

## REST API

All endpoints are proxied through FPP at:

```
http://<fpp-ip>/api/plugin/fpp-matrixscroller/<endpoint>
```

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `status` | Current state of all panels and running song |
| GET | `config` | Full configuration |
| POST | `config` | Update and save configuration (JSON body) |
| POST | `reload` | Reload config from disk without restart |
| GET | `models` | Available FPP pixel overlay models |
| GET | `fonts` | Available fonts detected on disk |
| GET | `music` | Music files available in FPP |
| GET | `version` | Current git commit hash of the deployed plugin |
| POST | `message` | Send a manual text override to a panel |
| POST | `message/all` | Send a manual text override to all panels |
| GET | `daemon/start` | Start the daemon (if not running) |
| POST | `daemon/restart` | Restart the daemon |
| POST | `daemon/stop` | Stop the daemon |
| GET | `backups` | List available config snapshots |
| POST | `backup` | Save a named config snapshot (JSON body: `{"name": "my-snapshot"}`) |
| POST | `restore` | Restore config from a snapshot (JSON body: `{"filename": "..."}`) |

### Manual Message Override

Send a custom message to a panel (bypasses media/no-media logic):

```json
POST /api/plugin/fpp-matrixscroller/message
{
  "panel_id": "panel_1",
  "message": "Welcome to the show!"
}
```

Clear override (returns panel to normal media/no-media mode):

```json
POST /api/plugin/fpp-matrixscroller/message
{
  "panel_id": "panel_1",
  "message": null
}
```

### Config Snapshots

Snapshots are saved to `/home/fpp/media/config/` alongside the active config, named:

```
plugin.fpp-matrixscroller.backup.<name>.json
```

Where `<name>` is the user-provided name (the UI pre-fills it with a timestamp like `20260101-120000`).

Save a snapshot via API:

```json
POST /api/plugin/fpp-matrixscroller/backup
{
  "name": "pre-show"
}
```

Restore from a snapshot via API:

```json
POST /api/plugin/fpp-matrixscroller/restore
{
  "filename": "plugin.fpp-matrixscroller.backup.pre-show.json"
}
```

## Message Assembly

When media is playing, the scroll message is built from enabled fields in this order:

```
[Pre-Roll] [gap] [Tune To] [gap] [Title - Artist - Album] [gap] [Post-Roll]
```

Only enabled fields are included. The Gap text is inserted between each present field.

When no media has been playing for longer than `no_media_timeout` seconds (or the current scroll effect finishes, whichever comes first), the no-media message fields are used.

## Config Structure

```json
{
  "global": {
    "schema_version": 1,
    "enable_output": true,
    "fpp_host": "localhost",
    "poll_interval": 1.0,
    "no_media_timeout": 5.0
  },
  "panels": [
    {
      "id": "panel_1",
      "name": "Panel 1",
      "enabled": true,
      "model": "Matrix1",
      "color": "#ff0000",
      "font": "C059-Bold",
      "fontsize": 10,
      "position": "R2L",
      "pixelspersecond": 15,
      "repeat_delay": 0,
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
          "font": "C059-Bold",
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

## Playlist Automation

Three shell scripts are installed to `/home/fpp/media/scripts/` and appear in the FPP playlist editor under **Run Script**. Use them to automate the plugin as your show changes phases.

### ms_enable_output.sh

Enable or disable all overlay output.

| Argument | Value |
|----------|-------|
| args | `1` to enable, `0` to disable |

**Playlist example:** Run Script → `ms_enable_output.sh` → args: `1`

### ms_restore_snapshot.sh

Restore a named config snapshot. The name is what you typed when saving the snapshot in the UI (without the `plugin.fpp-matrixscroller.backup.` prefix or `.json` suffix).

| Argument | Value |
|----------|-------|
| args | snapshot name, e.g. `pre-show` |

**Playlist example:** Run Script → `ms_restore_snapshot.sh` → args: `pre-show`

### ms_override_all.sh

Set or clear a manual message override on **all** panels simultaneously.

| Argument | Value |
|----------|-------|
| args | `[message]` — omit to clear all overrides |

**Playlist examples:**

```
# Set override on all panels
ms_override_all.sh Show starts in 5 minutes!

# Clear all overrides (returns all panels to normal mode)
ms_override_all.sh
```

### ms_reload_config.sh

Reload the config from disk without restarting the daemon. Useful if you have edited the config JSON on disk directly. Not needed after a snapshot restore — restores apply live automatically.

| Argument | Value |
|----------|-------|
| args | (none) |

**Playlist example:** Run Script → `ms_reload_config.sh`

---

### ms_override_panel.sh

Set or clear a manual message override on a specific panel, bypassing the normal media/no-media logic. Panel IDs are shown in the plugin UI (e.g. `panel_1`, `panel_2`).

| Argument | Value |
|----------|-------|
| args | `<panel_id> [message]` — omit message to clear the override |

**Playlist examples:**

```
# Set override on panel_1
ms_override_panel.sh panel_1 Show starts in 5 minutes!

# Clear override on panel_1 (returns to normal media/no-media mode)
ms_override_panel.sh panel_1
```

## Home Assistant Integration

A ready-to-use HA integration is included in the [`home-assistant/`](home-assistant/) directory:

| File | Purpose |
|------|---------|
| `matrixscroller_secrets.yaml` | FPP URLs — edit your IP here only |
| `matrixscroller_package.yaml` | Drop into HA `packages/` — sensors, switches, scripts, automations |
| `dashboard.yaml` | Lovelace dashboard view |

The dashboard provides daemon online/offline status, output enable/disable toggle, now-playing display, per-panel status table, and manual message override controls. No custom cards or HACS components required.

See [`home-assistant/README.md`](home-assistant/README.md) for setup instructions.

## Logs

```bash
tail -f /home/fpp/media/logs/fpp-matrixscroller.log
```

Log verbosity is controlled by FPP's built-in log level setting at **FPP → Settings → Logs → Plugin**. Set to `Debug` to see per-panel effect sends and config reloads; leave at `Info` (default) to log only startup, shutdown, and user-triggered actions.
