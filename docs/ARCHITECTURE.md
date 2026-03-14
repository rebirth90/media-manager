# 🏛️ System Architecture

This document outlines the technical architecture of the Media Manager application. The system strictly adheres to **Domain-Driven Design (DDD)** principles, separating business logic from infrastructure and UI concerns.

## 1. Domain-Driven Design (DDD) Layers

The codebase is split into four primary layers, with dependencies strictly pointing inward (Presentation -> Application -> Domain).

### 🟢 Domain Layer (`src/domain/`)
The absolute core of the application. Contains pure Python `@dataclass` models. 
* **Rules:** No imports from PyQt6, FastAPI, or third-party APIs. 
* **Key Entities:** `MediaItem`, `TorrentState`, `ConversionJob`.

### 🟡 Application Layer (`src/application/`)
Orchestrates business rules and acts as the bridge between the UI and Infrastructure.
* **Use Cases:** Classes like `SyncTorrentStateUseCase` or `AddMediaUseCase`. They receive data from the UI, apply business logic, and call repositories.
* **Event Bus:** `src/application/events.py` manages application-wide pub/sub events (e.g., `metadata_updated_signal`) to decouple components.

### 🔵 Infrastructure Layer (`src/infrastructure/`)
Handles all external I/O, APIs, and databases.
* **Repositories:** Implementations of domain interfaces (e.g., `SqliteMediaRepository`).
* **Services:** Third-party integrations like `QBittorrentClient`, `TMDBFetcherThread`, and the FastAPI backend (`api_server.py`).
* **Workers:** PyQt `QThread` classes that run background polling without blocking the UI.

### 🟣 Presentation Layer (`src/presentation/` & `src/ui/`)
The PyQt6 graphical user interface.
* **Rules:** Widgets manage their own state. Complex logic is passed down to the Application layer.
* **Components:** Custom frameless windows, media grid, dialogs, and dynamic styling components.

## 2. Concurrency & Threading Model

To maintain a 60FPS, non-blocking UI, we use a strict threading model:
1. **Main GUI Thread:** Renders PyQt6 widgets. NEVER runs network requests or disk I/O.
2. **QThread Workers:** Background tasks (e.g., `TorrentPoller`, `TMDBFetcherThread`) run here.
3. **Signals & Slots:** Workers communicate with the Main Thread exclusively by emitting `pyqtSignal` events. The Main Thread catches these to update the UI safely.

## 3. Data Flow Example: Adding a Torrent
1. **UI:** User drops a torrent in `BrowserModal`.
2. **Controller:** Triggers `AddMediaUseCase.execute()`.
3. **Infrastructure (DB):** Repository saves the `MediaItem` to SQLite.
4. **Infrastructure (API):** `QBittorrentClient` pushes the torrent to the qBittorrent server.
5. **Infrastructure (Worker):** `TMDBFetcherThread` queries the TMDB API for posters.
6. **Event Bus:** Emits `metadata_updated_signal`.
7. **UI:** `MediaGrid` catches the signal and redraws the card.