# Media Manager

A modern, enterprise-grade media management application for automating torrent downloads, FFmpeg encoding, and media organization workflows.

## ✨ UI Modernization (February 2026)

The application has been completely redesigned with a **modern, professional interface** inspired by contemporary SaaS dashboards:

### Key Features
- 🎨 **Modern Design**: Card-based layout with soft gradients and rounded corners
- 🌈 **Color-Coded Status**: Visual workflow tracking with blue, amber, and green states
- ⚡ **Interactive Elements**: Hover effects, focus states, and smooth transitions
- 📱 **Responsive Layout**: Clean pagination and scrollable content areas
- ♻️ **Accessibility**: High contrast ratios and clear visual hierarchy

### Design System
- **Primary Colors**: Soft blues (`#60a5fa`, `#a8d5e8`)
- **Status Colors**: Amber for progress, green for success, red for errors
- **Typography**: Segoe UI with clear size hierarchy
- **Components**: Cards, pills, modern buttons with shadows

See [UI_MODERNIZATION.md](UI_MODERNIZATION.md) for complete design documentation.

## Features

### Automated Workflow
1. **Download Stage** (▶ Start Project)
   - Torrent management via qBittorrent integration
   - Real-time progress tracking with speed monitoring
   - Automatic categorization (Movies/TV-Series)

2. **Encoding Stage** (✎ Edit Content)
   - FFmpeg-based video encoding
   - SSH telemetry for remote processing
   - Progress tracking and log viewing

3. **Approval Stage** (✔ Approve & Share)
   - Final review and approval
   - Share link generation
   - Complete workflow visualization

### UI Components

#### Main Dashboard
- **Navigation Bar**: Add content, search, and notifications
- **Media Flow Cards**: Track each item through the workflow
- **Pagination**: Navigate through large media collections
- **Status Indicators**: Color-coded progress visualization

#### Dialogs
- **Browser Modal**: Integrated Filelist.io torrent browser
- **Category Dialog**: Organize media by type and genre
- **Details Modal**: Deep dive into pipeline status and logs

## Technology Stack

### Core
- **Python 3.x**: Main application language
- **PyQt6**: Modern Qt6 bindings for Python
- **qBittorrent API**: Torrent management
- **FFmpeg**: Video encoding and processing

### Services
- **FastAPI**: Backend API server
- **SSH**: Remote telemetry and monitoring
- **WebEngine**: Embedded browser for torrent selection

### Architecture
- **Threading**: Async download and encoding workers
- **Polling**: Real-time status updates
- **Event-driven**: Signal/slot communication pattern

## Installation

### Prerequisites
```bash
# Python 3.8 or higher
python --version

# Install dependencies
pip install -r requirements.txt
```

### Required Dependencies
```
PyQt6
PyQt6-WebEngine
qbittorrent-api
python-dotenv
fastapi
uvicorn
paramiko  # For SSH connectivity
```

### Environment Configuration

Create a `.env` file in the project root:

```env
# Server Configuration
SERVER_HOST=127.0.0.1
LOCAL_PORT=9000

# qBittorrent
QBIT_HOST=127.0.0.1
QBIT_PORT=8080
QBIT_USER=admin
QBIT_PASS=adminadmin

# Filelist.io Credentials
FILELIST_USER=your_username
FILELIST_PASS=your_password

# Storage Paths
BASE_SCRATCH_PATH=/data/scratch
```

## Usage

### Starting the Application

```bash
python main.py
```

The application will:
1. Start the FastAPI backend server
2. Launch the PyQt6 GUI in fullscreen mode
3. Initialize connection to qBittorrent

### Workflow

1. **Add Media**:
   - Click "+ Movie / TV-Series" button
   - Browse Filelist.io for torrents
   - Download torrent file

2. **Categorize**:
   - Select media type (Movie/TV-Series)
   - Choose genre or enter series name
   - Confirm to start pipeline

3. **Monitor Progress**:
   - Watch status cards update in real-time
   - Click any stage for detailed logs
   - View download speeds and encoding progress

4. **Complete**:
   - Approve final output
   - Share generated link
   - Archive or remove media

## Project Structure

```
media-manager/
├── main.py              # Application entry point
├── core/                # Core business logic
├── services/            # External service integrations
│   ├── api_server.py    # FastAPI backend
│   ├── qbittorrent.py   # qBittorrent client
│   └── ssh_telemetry.py # SSH monitoring
├── ui/                  # User interface components
│   ├── main_window.py   # Main application window
│   ├── media_flow.py    # Workflow cards
│   └── dialogs.py       # Modal dialogs
├── workers/             # Background processing threads
│   ├── image_downloader.py
│   └── torrent_poller.py
└── UI_MODERNIZATION.md # UI design documentation
```

## Configuration

### qBittorrent Setup

1. Install qBittorrent with WebUI enabled
2. Configure WebUI port (default: 8080)
3. Set username and password
4. Update `.env` file with credentials

### SSH Server Setup

For remote encoding monitoring:

1. Configure SSH access to encoding server
2. Ensure FFmpeg is installed on remote server
3. Set up key-based authentication

### Media Organization

Default directory structure:
```
/data/scratch/
├── movies/
│   ├── action/
│   ├── comedy/
│   ├── drama/
│   └── ...
└── tv-series/
    ├── breaking_bad/
    ├── the_office/
    └── ...
```

## Troubleshooting

### Connection Issues

**qBittorrent not connecting**:
- Verify WebUI is enabled
- Check firewall settings
- Confirm correct host/port in `.env`

**Filelist.io login fails**:
- Verify credentials in `.env`
- Check for CAPTCHA requirements
- Ensure cookies are enabled

### UI Issues

**Buttons not responding**:
- Check for modal dialogs in background
- Verify fullscreen mode
- Restart application

**Status not updating**:
- Verify qBittorrent connection
- Check SSH connectivity
- Review worker thread logs

## Development

### Code Style

- **Type hints**: Use throughout for clarity
- **Docstrings**: Document complex functions
- **PEP 8**: Follow Python style guidelines
- **Qt naming**: Use Qt naming conventions for UI elements

### Testing

```bash
# Run with verbose logging
python main.py --debug

# Test specific components
python -m pytest tests/
```

### Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Update documentation
5. Submit a pull request

## Future Enhancements

- [ ] Dark mode support
- [ ] Multiple theme options
- [ ] Drag-and-drop reordering
- [ ] Advanced filtering and search
- [ ] Export/import configurations
- [ ] Statistics and analytics dashboard
- [ ] Notification system
- [ ] Multi-language support

## License

MIT License - see [LICENSE](LICENSE) file for details

## Acknowledgments

- **PyQt6**: Modern Qt bindings
- **qBittorrent**: Excellent torrent client with API
- **FFmpeg**: Powerful media processing
- **Design inspiration**: Google Gemini UI mockup

## Support

For issues, questions, or contributions:
- Open an issue on GitHub
- Review [UI_MODERNIZATION.md](UI_MODERNIZATION.md) for design details
- Check [AGENT_GUARDS.md](AGENT_GUARDS.md) for development guidelines

---

**Built with ❤️ for modern media management workflows**
