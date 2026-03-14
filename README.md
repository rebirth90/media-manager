# Media Manager

A modern, enterprise-grade media management application for automating torrent downloads, FFmpeg encoding, and media organization workflows. 

## ✨ UI Redesign - Gemini Mockup Implementation (February 2026)

The application has been **completely redesigned** to match a professional, polished mockup design:

### 🎨 Visual Highlights
- **Modern Card Layout**: Soft blue-gray gradients with floating white content cards.
- **Refined Typography**: Enhanced font hierarchy with Segoe UI.
- **Status Visualization**: Color-coded workflow states with glow effects
  - 🔵 **Blue**: Initializing/Download
  - 🟡 **Amber**: Processing/Encoding
  - 🟢 **Green**: Complete/Success
  - 🔴 **Red**: Errors
- **Professional Polish**: Subtle shadows, rounded corners, smooth hover effects.
- **Clear Workflow**: Visual arrows connecting Start → Edit → Approve stages.

### 🎯 Key Improvements
**Main Window**:
- Frameless application window with custom drag-to-move interactions and custom title bar controls.
- Startup loading overlay with smooth alpha fade-out animations for a polished boot experience.
- Enhanced navigation bar with refined pill buttons and Movies/TV-Series toggle filtering.
- Card-based content container with subtle transparency.

**Modal Dialogs**:
- Split-pane layout (Workflow Status / Content Details).
- Dynamic background blur effects dynamically applied to the main grid when modals are open.

## Features

### Automated Workflow
1. **Download Stage** (▶ Start Project)
   - Torrent management via qBittorrent integration, treating the qBittorrent server as the source of truth for progress.
   - Background polling updates UI progress pills and download speeds in real-time.
   - Automatic categorization parsing (Movies/TV-Series) based on torrent title metadata.
2. **Encoding Stage** (✎ Edit Content)
   - FFmpeg-based video encoding.
   - SSH telemetry for remote processing.
3. **Approval Stage** (✔ Approve & Share)
   - Final review and approval.

### Rich Metadata Management
- **Automated Metadata Discovery**: Integrates with the TMDB API to fetch high-quality metadata based on media titles.
- **Robust Fallbacks**: Automatically queries the IMDB API if TMDB ID matching fails to resolve correctly.
- **Content Enrichment**: Pulls in localized titles, release years, genres, descriptions, user ratings, and downloads high-resolution posters.

### Advanced TV Series Support
- **Automatic Season Parsing**: Intelligent parsing of torrent titles to detect seasons and label media types.
- **Episode Tracking**: Fetches episode-level data (stills, overviews, individual air dates) for active TV seasons.
- **File Matching**: Queries qBittorrent for torrent file listings and intelligently maps video files to their corresponding TV episode rows.

### UI Components
- **Browser Modal**: Integrated web browser modal utilizing WebEngine for Filelist.io torrent browsing.
- **Details Modal**: Deep dive into pipeline status, logs, and illustrations.

## Technology Stack

### Core
- **Python 3.x**: Main application language.
- **PyQt6**: Modern Qt6 bindings for Python.
- **qBittorrent API**: Torrent management.
- **FFmpeg**: Video encoding and processing.

### Services
- **FastAPI**: Backend API server.
- **SSH**: Remote telemetry and monitoring.
- **WebEngine**: Embedded browser for torrent selection.

### Architecture
- **Domain-Driven Design (DDD)**: Clean separation of domains spanning `presentation`, `application` (use cases), `domain` (entities like TorrentState, MediaItem, ConversionJob), and `infrastructure` (repositories, API clients).
- **Event-driven**: Signal/slot communication pattern combined with an internal event bus.
- **Threading**: Async download, tmdb fetchers, and encoding workers.

## Installation

### Prerequisites
```bash
# Python 3.8 or higher
python --version

# Install dependencies
pip install -r requirements.txt