# Home Assistant Integration

## Files

| File | Purpose |
|------|---------|
| `matrixscroller_secrets.yaml` | FPP URLs — **edit IP here only** |
| `matrixscroller_package.yaml` | Drop into HA `packages/` — all sensors, switches, scripts, helpers |
| `dashboard.yaml` | Lovelace view YAML |

All files live in the [`home-assistant/`](../home-assistant/) directory of the plugin repo.

---

## Setup

### 1. Add secrets

Copy the entries from `matrixscroller_secrets.yaml` into your HA `secrets.yaml`.
Change `192.168.250.20` to your FPP device IP — this is the **only** place you need
to update it.

### 2. Enable packages (once, if not already done)

In `configuration.yaml`:

```yaml
homeassistant:
  packages: !include_dir_named packages
```

Create the `packages/` directory under your HA config root if it doesn't exist.

### 3. Drop in the package

Copy `matrixscroller_package.yaml` into `config/packages/`.

### 4. Add the dashboard

1. Open any HA dashboard → **Edit** (pencil icon) → **Add View** → give it a name → **Save**
2. On the new empty view, click the **`< >`** (raw YAML) icon
3. Replace all existing content with the contents of `dashboard.yaml`
4. Before pasting, update the `weblink` URL to your FPP IP (the one `!secret` line that can't be resolved in the UI editor — it's marked with a `# ← change IP` comment)
5. **Save**

> The dashboard uses `type: masonry` layout — cards stack in a single column on mobile and two columns on wider screens. No custom cards or HACS components required.

### 5. Restart HA

Verify `sensor.matrixscroller_status` populates and the panel table appears.

---

## What it gives you

- **Daemon online/offline** badge
- **Output enable/disable** toggle switch → `POST /output`
- **Now Playing** — current song pulled from FPP
- **Panel table** — per-panel mode, running state, color swatch, and active message
- **Manual override** — type a message, send to all panels at once, or clear it
- **Link to plugin UI** — opens the full FPP plugin page for advanced config

---

## Entities created

| Entity | Type | Description |
|--------|------|-------------|
| `sensor.matrixscroller_status` | REST sensor | Full `/status` JSON; panels array as attribute |
| `sensor.matrixscroller_config` | REST sensor | Full `/config` JSON; global settings as attribute |
| `switch.matrixscroller_output` | Template switch | Enable/disable all panel output |
| `binary_sensor.matrixscroller_daemon` | Template binary sensor | Daemon running state |
| `input_text.matrixscroller_override` | Helper | Manual override message (all panels) |
| `input_text.matrixscroller_panel_override` | Helper | Manual override message (single panel) |
| `input_select.matrixscroller_panel_select` | Helper | Panel selector (populated from live status) |
| `script.matrixscroller_send_override` | Script | Send override to all panels |
| `script.matrixscroller_clear_override` | Script | Clear all overrides |
| `script.matrixscroller_send_panel_override` | Script | Send override to selected panel |
| `script.matrixscroller_clear_panel_override` | Script | Clear selected panel override |
