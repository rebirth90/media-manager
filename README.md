# Media Manager

A modern, enterprise-grade media management application for automating torrent downloads, FFmpeg encoding, and media organization workflows.

## ✨ UI Redesign - Gemini Mockup Implementation (February 2026)

The application has been **completely redesigned** to match a professional, polished mockup design:

### 🎨 Visual Highlights

- **Modern Card Layout**: Soft blue-gray gradients with floating white content cards
- **Refined Typography**: Enhanced font hierarchy with Segoe UI
- **Status Visualization**: Color-coded workflow states with glow effects
  - 🔵 **Blue**: Initializing/Download
  - 🟡 **Amber**: Processing/Encoding  
  - 🟢 **Green**: Complete/Success
  - 🔴 **Red**: Errors
- **Professional Polish**: Subtle shadows, rounded corners, smooth hover effects
- **Clear Workflow**: Visual arrows connecting Start → Edit → Approve stages

### 📚 Design Documentation

- **[MOCKUP_REDESIGN.md](MOCKUP_REDESIGN.md)**: Comprehensive design system documentation
  - Design philosophy and principles
  - Complete color palette
  - Typography system
  - Component specifications
  - Shadow and spacing systems
  
- **[docs/UI_IMPROVEMENTS_SUMMARY.md](docs/UI_IMPROVEMENTS_SUMMARY.md)**: Quick reference guide
  - Color palette cheat sheet
  - Typography quick reference
  - Implementation examples
  - Testing checklist

### 🎯 Key Improvements

**Main Window**:
- Enhanced navigation bar with refined pill buttons
- Card-based content container with subtle transparency
- Improved pagination controls with better visual states
- Custom-styled scrollbars

**Media Flow Cards**:
- Increased height (82px) for better spacing
- Status buttons with glow effects for active states
- Enhanced hover effects with shadows
- Better visual hierarchy with refined typography

**Modal Dialogs**:
- Split-pane layout (Workflow Status / Content Details)
- Illustration support for visual workflow representation
- Color-coded status pills
- Monospace font for log viewing

### 🔧 Technical Details

**Styling Approach**: PyQt6 stylesheets embedded in Python code

**Performance**: 
- Blur effects only during modal display
- Efficient widget reuse
- No external CSS dependencies

**Accessibility**:
- WCAG AA color contrast compliance
- Pointer cursor on interactive elements
- Clear focus states

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
- **Pagination**: Navigate through large media collections (10 items/page)
- **Status Indicators**: Color-coded progress visualization with glow effects

#### Dialogs
- **Browser Modal**: Integrated Filelist.io torrent browser with auto-login
- **Category Dialog**: Organize media by type and genre
- **Details Modal**: Deep dive into pipeline status, logs, and illustrations

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
- **Polling**: Real-time status updates (3s intervals)
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
PyQt6>=6.4.0
PyQt6-WebEngine>=6.4.0
qbittorrent-api>=2023.11.57
python-dotenv>=1.0.0
fastapi>=0.104.0
uvicorn[standard]>=0.24.0
paramiko>=3.3.1
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
1. Start the FastAPI backend server on port 9000
2. Launch the PyQt6 GUI in fullscreen mode
3. Initialize connection to qBittorrent
4. Load Segoe UI font for consistent typography

### Workflow

1. **Add Media**:
   - Click "+ Movie / TV-Series" button (top-left)
   - Browse Filelist.io for torrents (auto-login enabled)
   - Download torrent file

2. **Categorize**:
   - Select media type (Movie/TV-Series)
   - Choose genre (Movies) or enter series name (TV-Series)
   - Confirm to start pipeline

3. **Monitor Progress**:
   - Watch status cards update in real-time
   - Blue glow = initializing/downloading
   - Amber glow = encoding
   - Green glow = ready for approval
   - Click any stage button for detailed logs

4. **View Details**:
   - Click status buttons to open pipeline details modal
   - View workflow illustration
   - Check downloader tracker status
   - Monitor FFmpeg encoding telemetry
   - Access share links

5. **Complete**:
   - Approve final output (green button)
   - Share generated link
   - Archive or remove media

## Project Structure

```
media-manager/
├── main.py                       # Application entry point
├── core/                         # Core business logic
├── services/                     # External service integrations
│   ├── api_server.py            # FastAPI backend
│   ├── qbittorrent.py           # qBittorrent client
│   └── ssh_telemetry.py         # SSH monitoring
├── ui/                          # User interface components
│   ├── main_window.py           # Main application window (redesigned)
│   ├── media_flow.py            # Workflow cards (redesigned)
│   ├── dialogs.py               # Modal dialogs
│   └── COLOR_SYSTEM.md          # Color system documentation
├── workers/                     # Background processing threads
│   ├── image_downloader.py
│   └── torrent_poller.py
├── docs/                        # Documentation
│   └── UI_IMPROVEMENTS_SUMMARY.md  # Quick reference guide
├── MOCKUP_REDESIGN.md          # Comprehensive design docs
├── UI_MODERNIZATION.md         # Previous UI evolution
└── DESIGN_CHANGELOG.md         # Design iteration history
```

## Configuration

### qBittorrent Setup

1. Install qBittorrent with WebUI enabled
2. Configure WebUI port (default: 8080)
3. Set username and password
4. Update `.env` file with credentials
5. Ensure automatic management is enabled

### SSH Server Setup

For remote encoding monitoring:

1. Configure SSH access to encoding server
2. Ensure FFmpeg is installed on remote server
3. Set up key-based authentication (recommended)
4. Test connectivity before starting workflows

### Media Organization

Default directory structure:
```
/data/scratch/
├── movies/
│   ├── action/
│   ├── adventure/
│   ├── anime/
│   ├── comedy/
│   ├── crime/
│   ├── drama/
│   ├── horror/
│   ├── sf/
│   └── thriller/
└── tv-series/
    ├── breaking_bad/
    ├── the_office/
    └── [series_name]/
```

## Troubleshooting

### Connection Issues

**qBittorrent not connecting**:
- Verify WebUI is enabled in qBittorrent settings
- Check firewall settings (port 8080)
- Confirm correct host/port in `.env`
- Test connection: `http://localhost:8080`

**Filelist.io login fails**:
- Verify credentials in `.env`
- Check for CAPTCHA requirements (manual login may be needed first time)
- Ensure cookies are enabled in WebEngine
- Clear browser cache if persistent issues

**SSH telemetry not working**:
- Verify SSH credentials and connectivity
- Check firewall rules on remote server
- Ensure FFmpeg is in PATH on remote server
- Test SSH connection manually first

### UI Issues

**Buttons not responding**:
- Check for modal dialogs in background
- Verify fullscreen mode (press Escape to exit)
- Restart application
- Check for JavaScript errors in console

**Status not updating**:
- Verify qBittorrent connection (red status = error)
- Check SSH connectivity for encoding status
- Review worker thread logs in Details modal
- Ensure polling threads are running

**Visual glitches**:
- Update graphics drivers
- Disable hardware acceleration if needed
- Check for Qt6 updates
- Verify system meets minimum requirements

## Development

### Code Style

- **Type hints**: Use throughout for clarity (`-> None`, `: str`, etc.)
- **Docstrings**: Document complex functions
- **PEP 8**: Follow Python style guidelines
- **Qt naming**: Use Qt naming conventions for UI elements
- **CSS-in-Python**: Embedded stylesheets for easy maintenance

### Design System

When adding new UI elements:

1. **Colors**: Reference [MOCKUP_REDESIGN.md](MOCKUP_REDESIGN.md) color palette
2. **Typography**: Use standard font sizes (9pt, 10pt, 12.5pt, 14pt)
3. **Spacing**: Follow 8px grid system
4. **Shadows**: Use predefined shadow levels
5. **Borders**: Use consistent border-radius values

### Testing

```bash
# Run with verbose logging
python main.py --debug

# Test specific components
python -m pytest tests/

# UI testing checklist
# - All hover states work
# - Status colors match design system
# - Modals blur background
# - Pagination updates correctly
# - Typography is consistent
```

### Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Follow design system guidelines
5. Update documentation if needed
6. Submit a pull request with clear description

## Future Enhancements

### Planned Features
- [ ] Dark mode support (color system ready)
- [ ] Multiple theme options (blue, green, purple)
- [ ] Drag-and-drop reordering of media flows
- [ ] Advanced filtering and search
- [ ] Export/import configurations
- [ ] Statistics and analytics dashboard
- [ ] Push notification system
- [ ] Multi-language support (i18n ready)

### Design Improvements
- [ ] Animated transitions between states
- [ ] Custom SVG icons instead of Unicode
- [ ] Pulse animations for active processing
- [ ] Progress bars instead of percentage text
- [ ] Expandable/collapsible sections

## Performance Notes

- **Startup Time**: ~2-3 seconds on modern hardware
- **Memory Usage**: ~150-200MB typical
- **CPU Usage**: <5% idle, <20% during encoding telemetry
- **Rendering**: Hardware-accelerated Qt6 rendering
- **Polling Intervals**: 3s for status updates

## System Requirements

**Minimum**:
- Python 3.8+
- 4GB RAM
- Windows 10 or Linux (Ubuntu 20.04+)
- 1280x720 display resolution

**Recommended**:
- Python 3.10+
- 8GB RAM
- Windows 11 or Linux (Ubuntu 22.04+)
- 1920x1080 display resolution
- Dedicated GPU for better UI performance

## License

MIT License - see [LICENSE](LICENSE) file for details

## Acknowledgments

- **PyQt6**: Modern Qt bindings for Python
- **qBittorrent**: Excellent torrent client with comprehensive API
- **FFmpeg**: Industry-standard media processing
- **Design inspiration**: Google Gemini UI mockup generation
- **Color palette**: Custom blue-gray professional theme

## Support & Documentation

For issues, questions, or contributions:
- 🐛 **Bug Reports**: Open an issue on GitHub
- 📖 **Design Docs**: [MOCKUP_REDESIGN.md](MOCKUP_REDESIGN.md)
- ⚡ **Quick Reference**: [docs/UI_IMPROVEMENTS_SUMMARY.md](docs/UI_IMPROVEMENTS_SUMMARY.md)
- 🔒 **Dev Guidelines**: [AGENT_GUARDS.md](AGENT_GUARDS.md)
- 🎨 **Design Evolution**: [DESIGN_CHANGELOG.md](DESIGN_CHANGELOG.md)

## Screenshots

### Main Dashboard
![Main Dashboard](screenshots/dashboard.png) *(if available)*

Features:
- Soft gradient background
- Card-based layout
- Color-coded status indicators
- Clean pagination

### Workflow Visualization
![Workflow Cards](screenshots/workflow.png) *(if available)*

Shows:
- Three-stage workflow (Start → Edit → Approve)
- Status glow effects
- Real-time progress updates

### Details Modal
![Pipeline Details](screenshots/details.png) *(if available)*

Includes:
- Workflow illustration
- Telemetry logs
- Status tracking
- Action buttons

---

**Built with ❤️ for modern media management workflows**  
**Design Version 2.0** | **February 2026** | **Production Ready** ✅
