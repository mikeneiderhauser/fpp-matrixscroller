# fpp-matrixscroller

FPP plugin that scrolls the playing song's title and artist (from its MP3 tags), or your own text, across one or more pixel matrix panels using FPP's native Overlay Model Effect API. Between songs, and during sequences without audio, it shows a configurable idle message.

## Features

- **N matrix panels** — each with fully independent configuration
- **Two modes per panel** — Media Playing and Media Idle (with configurable timeout)
- **Sequences without audio** — animation-only FSEQs show the Media Idle message by default, detected from the FSEQ's xLights header; works on a multisync remote too
- **Configurable message fields** — Pre-Roll, Tune To, Song Info, Post-Roll, Gap separator; each independently enabled per mode
- **Song info order** — Title · Artist · Album, joined with ` - `; each field individually enabled
- **Song and sequence overrides** — override color, font, direction, speed, and artist/title/album text for a specific song or FSEQ sequence; or suppress the overlay entirely for one
- **Repeat delay** — configurable per-panel pause between scroll repetitions (default 0 s)
- **Immediate media transitions** — stops the current effect and restarts immediately when the song changes; switches to no-media as soon as the current effect finishes rather than leaving the matrix dark
- **Enable Output toggle** — suppress all overlay effects without stopping the daemon
- **Daemon controls** — Start, Stop, and Restart the daemon from the web UI
- **Config Snapshots** — save named snapshots (pre-filled with a timestamp), download/upload config as JSON, restore from any saved snapshot
- **FPP Commands** — turn all panels or one panel on/off, show or clear a message (optionally for a set time), restore a snapshot; from playlists, the scheduler, MQTT or another FPP
- **REST API** — get/set config, status, manual message overrides, version info (useful for Home Assistant automations)
- **Autostart** — starts automatically on install and on every FPP daemon start (`scripts/postStart.sh`), and stops with it (`scripts/preStop.sh`)
- **Web UI** — configure all panels from the FPP plugin page; honors FPP's dark/light mode setting; git commit shown in page footer
- **Log level integration** — respects FPP's **Settings → Logs → Plugin** log level; set to `Debug` for verbose output, `Info` for quiet operation

## Requirements

- FPP 9.0+ (primarily tested on FPP 10)
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
sudo bash /home/fpp/media/plugins/fpp-matrixscroller/scripts/fpp_install.sh
```

Run the install script as root, as FPP does. Run as `fpp` it can't restart a daemon FPP already started, so it stops with an error rather than start a second one.

---

In all cases, `fpp_install.sh` deploys the playlist scripts, creates the log and config directories, and starts the daemon. FPP then starts it on every fppd start (`scripts/postStart.sh`) and stops it before fppd stops (`scripts/preStop.sh`).

### Uninstalling

Uninstalling stops the daemon and removes the playlist scripts. Your settings and snapshots are kept, so a Reinstall (or FPP's **Reinstall All** after an OS upgrade) picks them up again. To remove them too, delete them after uninstalling:

```bash
rm -f /home/fpp/media/config/plugin.fpp-matrixscroller.json
rm -rf /home/fpp/media/plugindata/fpp-matrixscroller
```

Config is stored at:
```
/home/fpp/media/config/plugin.fpp-matrixscroller.json
```
On first run the plugin falls back to the bundled `config.json` defaults.

## Web UI

Open the plugin page in FPP's web interface. The UI includes:

- **FPP Status Bar** — current song, progress bar, and embedded ID3 tags
- **Panel Status** — live mode badge, active message, and manual message override per panel
- **Panels** — full per-panel config including display settings, message fields, and song/sequence overrides
- **Global Settings** — FPP host, poll interval, media idle timeout, Sequence Without Audio, Enable Output toggle
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
| GET | `sequences` | Sequence (FSEQ) files available in FPP |
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

Snapshots are saved to `/home/fpp/media/plugindata/fpp-matrixscroller/backups/` (older versions kept them beside the config; they are moved there on the next start), named:

```
plugin.fpp-matrixscroller.backup.<name>.json
```

Where `<name>` is the user-provided name (the UI pre-fills it with a timestamp like `20260101-120000`).

Snapshots are kept when the plugin is uninstalled (see [Uninstalling](#uninstalling)).

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

### Sequences without audio

A sequence counts as having audio when FPP reports a media file for it, or when the FSEQ's xLights header (`mf`) names the audio it was built against. Animation-only sequences have neither.

The global `sequence_only` setting (**Sequence Without Audio** in the UI) decides what those show:

| Value | Animation-only sequence shows |
|-------|-------------------------------|
| `idle` (default) | The Media Idle message, after `no_media_timeout` |
| `media` | The media message, using the sequence name as the title |

> **Behaviour change:** before this setting existed, every sequence was treated as media, so an animation scrolled its FSEQ filename as if it were a song. Set `sequence_only` to `media` to keep that.

A playlist's Global Pause between items always shows the Media Idle message. To show something during a particular animation instead, give it a sequence override (below).

### Running on a multisync remote

A remote only knows a song's media file when that file is on the remote as well. Without it the plugin still detects the song from the FSEQ header, but has no ID3 tags to read, so the title falls back to the audio file's name from the FSEQ header (e.g. `Winter Wonderland - Selena Gomez`). If that name isn't what you want on the matrix, either:

- **Upload the MP3s to the remote too** (same filenames as the master), so the artist and title come from their tags, the same as on the master. Note the remote will then play that audio in sync as well; set its volume however suits your show.
- **Add an override** with the artist and title to show. An override keyed by the MP3 applies on the remote too, matched through the FSEQ header, so the same config works on master and remotes.

### Song and sequence overrides

Each panel's `song_overrides` is keyed by a filename: a media file (`Jingle Bell Rock - Glee.mp3`) or a sequence (`TuneToPixel2.fseq`). The UI lists both. When something plays, the plugin looks for an override in this order and uses the first it finds:

1. The sequence (FSEQ) name
2. The media file FPP reports
3. The audio name from the FSEQ's `mf` header

Each step tries the exact filename first, then the name without its extension, case-insensitive. So a sequence override wins over a media override for the same song, and an override keyed by the MP3 still applies on a remote that only has the FSEQ.

A sequence override also makes a sequence without audio display as media on that panel, even with `sequence_only` set to `idle`. It shows the override's artist/title (or the sequence name) with its colour, font and direction; unchecking **Play overlay** blanks the panel for that sequence instead. Animations without an override keep showing the Media Idle message.

## Config Structure

```json
{
  "global": {
    "schema_version": 1,
    "enable_output": true,
    "fpp_host": "localhost",
    "poll_interval": 1.0,
    "no_media_timeout": 5.0,
    "sequence_only": "idle"
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

## FPP Commands

The plugin adds these FPP commands. Use them anywhere FPP runs a command: a playlist's **FPP Command** entry, the scheduler, command presets, MQTT, button plugins, or another FPP's remote command.

| Command | Options | Does |
|---------|---------|------|
| **Matrix Scroller - All Panels State** | On / Off / Toggle | The global on/off for every panel at once (the **Enable Output** switch). Each panel keeps its own setting, so turning all panels back on restores them as they were |
| **Matrix Scroller - Panel State** | Panel, On / Off / Toggle | Turns one panel on or off and saves it (its **Enabled** checkbox). A panel that is on still shows nothing while All Panels State is Off |
| **Matrix Scroller - Show Message** | Panel (or All panels), Message, Duration | Shows your text instead of song info. With a duration (seconds) it clears itself afterwards; `0` keeps it until cleared |
| **Matrix Scroller - Clear Message** | Panel (or All panels) | Returns to normal song / idle display |
| **Matrix Scroller - Restore Snapshot** | Snapshot | Applies a saved config snapshot |

Panels and snapshots are picked from dropdowns. Each command and option has a description in FPP's command editor.

## Playlist Automation

The FPP commands above are the simplest way to automate the plugin. The older shell scripts below still work: they are installed to `/home/fpp/media/scripts/` and appear in the FPP playlist editor under **Run Script**.

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
tail -f /home/fpp/media/logs/plugin-fpp-matrixscroller.log
```

Log verbosity is controlled by FPP's built-in log level setting at **FPP → Settings → Logs → Plugin**. Set to `Debug` to see per-panel effect sends and config reloads; leave at `Info` (default) to log only startup, shutdown, and user-triggered actions.
