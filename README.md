# Media Manager

Media Manager is a PyQt6 desktop app for managing torrent-driven media workflows end to end:

- ingest and monitor torrents from qBittorrent
- enrich media with TMDB and IMDb-backed metadata
- track encoding/telemetry states
- inspect conversion pipeline visuals and logs per item

<img width="1920" height="1080" alt="{40AFD82D-C7E2-4467-959A-43392FC5F6FA}" src="https://github.com/user-attachments/assets/87997a3c-659d-4201-90e5-10c8799e2bde" />
<img width="1920" height="1080" alt="{D2F87C9A-859B-44A6-A9F1-3A5597622AE1}" src="https://github.com/user-attachments/assets/f6565e44-0af2-4193-a428-18050aa775fc" />


## Current Capabilities

### Torrent and Progress Pipeline
- qBittorrent integration for torrent state, speed, and size polling.
- qBittorrent is treated as source of truth for initial size values.
- Base-10 size formatting (B/KB/MB/GB/TB, divide by 1000) to match qBittorrent display.
- Separate progress handling for movie cards, season cards, and episode rows.

### Movie and TV Handling
- Automatic title parsing for Movie vs TV season content.
- Episode row generation from torrent file listings.
- Episode-to-file mapping so each episode can track its own qBittorrent size and telemetry.
- TMDB metadata enrichment and image loading for movies and episodes.
- IMDb fallback path when TMDB ID discovery cannot be resolved directly.

### Foldout Insights and Logs
- Expandable foldouts for conversion details.
- Inline summary metrics:
   - initial size
   - final size and percentage delta
   - total conversion minutes
- Quick-open buttons for general and FFmpeg logs when conversion is completed.
- Conversion flowchart per card with delayed reveal on expand to prevent half-size chart paint.

### UI and Interaction
- Custom card-based UI with movie and TV filtering.
- Foldout expand/collapse animations with adaptive height sync.
- Startup loading overlay.
- Blur-aware modal interactions that collapse open foldouts before dialog flows.
- Embedded browser modal for Filelist-style torrent browsing and metadata extraction.

### Architecture and Services
- DDD layering across `domain`, `application`, `infrastructure`, and `presentation`/`ui`.
- Signal-driven updates across worker threads and UI.
- Local FastAPI service bootstrapped with the desktop app runtime.
- SQLite-backed persistence for media and telemetry snapshots.
- SSH support for remote telemetry/log access scenarios.

## Project Layout

```text
media-manager/
   main.py
   requirements.txt
   start_app.bat
   src/
      application/
      domain/
      infrastructure/
      presentation/
      ui/
   docs/
      ARCHITECTURE.md
   tests/
```

## Requirements

- Python 3.8+
- qBittorrent Web UI/API reachable from this machine
- FFmpeg available in your processing environment
- Optional: SSH target for remote telemetry flows

Install dependencies:

```bash
pip install -r requirements.txt
```

## Environment Variables

Create a `.env` file in the project root and configure the values your setup needs.

### Core runtime
- `SERVER_HOST` (example: `127.0.0.1`)
- `LOCAL_PORT` (example: `9000`)

### qBittorrent
- `QBIT_HOST`
- `QBIT_PORT`
- `QBIT_USER`
- `QBIT_PASS`

### Metadata services
- `TMDB_READ_ACCESS_TOKEN`

### Optional provider auth
- `FILELIST_USER`
- `FILELIST_PASS`

### Optional remote telemetry
- `SSH_HOST`
- `SSH_USER`
- `SSH_PASS`
- `REMOTE_APP_DIR`

### Optional path config
- `BASE_SCRATCH_PATH`

## Run the App

Option 1 (recommended on Windows):

```bat
start_app.bat
```

Option 2:

```bash
python main.py
```

## Testing

Run all tests:

```bash
pytest
```

More test guidance is available in `TESTING.md`.

## Documentation

- Architecture: `docs/ARCHITECTURE.md`
- Testing strategy: `TESTING.md`

## Notes

- Size displays are intentionally base-10 to align with qBittorrent UI values.
- Foldout flowcharts use a brief inline loading state on expand when needed, then render at full computed size.
