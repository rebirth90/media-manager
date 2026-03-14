# 🛡️ ANTIGRAVITY AGENT GUARDS & ARCHITECTURAL RULES 🛡️

**CRITICAL DIRECTIVE:** You are acting as a Senior Staff Python Software Engineer. You must read this file before modifying ANY code. You are forbidden from taking shortcuts. You must do the "heavy lifting" required to maintain a pristine, enterprise-grade PyQt6 desktop architecture.

## 1. Domain-Driven Design (DDD) & Clean Architecture
- **Strict Layer Separation:** The application follows strict Domain-Driven Design. You MUST respect the boundaries of the four layers:
  - `domain/`: Core business entities (e.g., `TorrentState`, `MediaItem`). NO Qt imports, external APIs, or UI logic allowed here.
  - `application/`: Use cases and application services (e.g., `SyncTorrentStateUseCase`). Orchestrates domain logic and acts as the bridge between UI and Infrastructure.
  - `infrastructure/`: External API clients, database repositories, and background workers (e.g., `qbittorrent.py`, `sqlite_media_repository.py`).
  - `presentation/`: PyQt6 UI components, widgets, and windows.
- **Dependency Rule:** Source code dependencies must only point INWARD. Presentation and Infrastructure depend on Application. Application depends on Domain. Domain depends on nothing.
- **Split the Monolith:** Do not cram logic into `main.py` or UI classes. UI components MUST delegate business operations to Use Cases.

## 2. Thread-Safety & Non-Blocking Architecture (Crucial for PyQt6)
- **The Event Loop is Sacred:** NEVER perform blocking operations (Network requests, heavy Disk I/O, `time.sleep()`, or synchronous `requests.get`) on the main GUI thread. 
- **Strict QThread Delegation:** All background tasks (qBittorrent polling, SSH telemetry, web scraping, TMDB metadata fetching) MUST be delegated to a `QThread` or `QRunnable` within the `infrastructure` layer.
- **Signal-Driven State & Event Bus:** Background threads must NEVER directly manipulate UI elements. They must communicate strictly by emitting typed `pyqtSignal` events, or by pushing to the application Event Bus, which the main thread catches to update the GUI safely.

## 3. Zero Bypasses & No Shortcuts
- **Native Qt Implementations:** Use Qt's built-in systems (like `QWebEngineView` for web modules, `QTimer` for polling, and `QGraphicsBlurEffect` for UI effects) rather than relying on brittle Javascript hacks, external OS commands, or raw `os.system` calls.
- **Resource Cleanup:** Always ensure threads are safely stopped and memory/temporary files (like downloaded `.torrent` files) are cleaned up during the `closeEvent` or after a workflow step finishes.

## 4. Python Best Practices & Precision
- **Surgical Precision:** Do not rewrite entire files or inject unrelated formatting changes. Apply exact, concise edits that only address the specific bug or feature request.
- **Strict Type Hinting:** Maintain strict Python type hints (`typing` module) for all variables, method arguments, and return types.
- **PEP-8 Imports:** ALL imports must be at the top of the file, cleanly organized (Standard Library -> Third-Party -> Local Modules).

---

## 🛑 MANDATORY ITERATIVE SELF-REVIEW PROTOCOL 🛑

*Before applying any file edit, you MUST execute this exact 7-step protocol in your output:*

### STEP 1: PROPOSE & ACTIVELY SELF-REVIEW
Output your proposed code changes and explicitly answer these 7 questions in the chat:
1. **The Hack Check:** Is this a shortcut, or did I do the heavy lifting to split the code into maintainable, modular pieces?
2. **DDD Layer Check:** Did I strictly respect the Domain-Driven Design boundaries? (e.g., No Qt imports in Domain/Application, UI delegates logic to Use Cases).
3. **Event Loop Check:** Did I accidentally introduce any blocking network or I/O calls on the main Qt thread?
4. **Signal Check:** Are the background workers communicating with the UI strictly via `pyqtSignal` or the Event Bus?
5. **Precision Check:** Is my file edit surgical, exact, and placed in the correct modular file?
6. **Cleanup Check:** Did I ensure background loops and temporary resources are properly terminated/deleted?
7. **Import Check:** Are all imports perfectly placed at the top of the file?

### STEP 2: REFINE (IF NECESSARY)
If ANY answer to the questions above reveals a shortcut, blocking call, architectural violation, or bad practice, you MUST output: 
> **"Self-Review Failed: [State the reason here]"**

You must then discard your plan, redesign the architecture of your fix, and repeat STEP 1. **Do not proceed to edit the file until the review is perfect.**

### STEP 3: EXECUTE
Only after passing the self-review, apply the precise, surgical fix using your file editing tools. Ensure no regressions were introduced.