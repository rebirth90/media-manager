Please apply the following architectural, functional, and structural modifications to the codebase. These changes enhance the browser downloading logic, introduce background authentication, add a custom frameless window, integrate TMDB enhancements, and add torrent deletion features.

**Please DO NOT modify the visual styling of the `MediaFlowWidget`'s middle row or its foldout page (keep the legacy look), but do integrate the backend/functional endpoints into it.**

### 1. FileList Authentication & Native Downloading (`ui/dialogs.py` & `ui/main_window.py`)
- **Background Authentication Profile**:
  - In `SecureServerWindow.__init__` (`main_window.py`), initialize a persistent `QWebEngineProfile("filelist_auth")` saving cache to `.qt_cache`.
  - Instantiate `FilelistAuthenticator` using this profile, and trigger `.login()` in the background on app startup.
- **BrowserModalDialog Revamp**:
  - Modify `BrowserModalDialog` to accept the persistent `profile` in its constructor and apply it to a new `QWebEnginePage`.
  - Navigate directly to `https://filelist.io/browse.php`. If it hits `/login.php`, disable the web view, route authentication to the `parent_win.auth_manager`, await success, and reload the browse page. Remove the old JS-based form injection.
  - **Native Downloads**: Override `_on_download_requested` to use native PyQt web engine downloading to a `temp_torrents` folder instead of reading blobs into memory via JS. Use `request.stateChanged` to wait for completion.
  - **JS Payload Extraction**: Update the JS scraper to extract the `tmdbId` (or fallback to an `imdb` `tt` regex match from `a[href*='imdb.com/title/']`). Also, extract the `season` string by regex parsing `document.title` or `h1` for `SXX` or `Season XX`. The callback will now return `imageUrl`, `title`, and `season`.

### 2. Custom Frameless Main Window (`ui/main_window.py`)
- Apply `self.setWindowFlags(Qt.WindowType.FramelessWindowHint)` to `SecureServerWindow`.
- Build a custom White Header Container (height 72) encapsulating:
  - The `+ Movie / TV-Series` button
  - Centered Search Bar
  - Window control buttons (Minimize, Maximize/Restore, Close). Implement native logic for these custom buttons (e.g., `showMinimized`, `showNormal`/`showMaximized` toggle, and `QApplication.quit()` + `os._exit(0)` on close to kill Uvicorn threads).
- Implement `mousePressEvent`, `mouseMoveEvent`, and `mouseReleaseEvent` for native window drag-and-drop within the Y < 72 pixel header boundary.
- Eradicate the 10-item pagination logic for `QScrollArea`. Change it to continuously append new flows directly to the vertical layout without pagination buttons.

### 3. TMDB API Enhancements (`workers/tmdb_fetcher.py`)
- **IMDB Fallback**: In `TMDBFetcherThread.run`, if the ID starts with `tt` or `media_type == "imdb"`, use the `/find/{id}?external_source=imdb_id` endpoint first to resolve the proper TMDB ID before continuing.
- Have the thread extract `overview` (description), `genres`, `vote_average` (rating), and build the `poster_path` into a full TMDB image URL.
- Emit a new `details_resolved(dict)` signal alongside `title_resolved`, passing all these attributes safely back to the UI.

### 4. Torrent Deletion Mechanics (`services/qbittorrent.py` & UI)
- Create a `QBittorrentDeleteWorker` thread extending `QThread` inside `services/qbittorrent.py` that accepts a hash list and a `delete_files` boolean, natively mapping to `client.torrents_delete(...)`.
- Add a new dialog class `DeleteTorrentDialog` in `ui/dialogs.py` featuring the torrent name and a "Delete files with torrent" `QCheckBox`.
- Wire up a `_prompt_delete` method in `MediaFlowWidget` that instantiates this dialog, calls the `QBittorrentDeleteWorker`, and upon success, removes the widget from the layout (`self.close_flow()` + `self.setParent(None)`).

### 5. Media Flow Widget Hooks (`ui/media_flow.py`)
- **Constructor Changes**: `__init__` should now accept a `season: str = ""` argument. Construct the `self.title` string as `"{base_title} - {season}"` when present.
- **TMDB Connections**: Integrate the new `details_resolved` signal from `TMDBFetcherThread` out to a slot that updates appropriate metadata labels on the UI. Start an `ImageDownloaderThread` within this slot if the TMDB payload returned an `image_url`.
- Change `MediaCategoryDialog`'s TV-Series category directory builder to replace spaces with dots instead of underscores (e.g., `replace(" ", ".")`).
