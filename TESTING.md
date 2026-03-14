# 🧪 Testing Strategy & Guidelines

This document outlines the testing standards for the Media Manager application. Because our architecture relies heavily on asynchronous operations, background `QThread` polling, FastAPI, and strict Domain-Driven Design (DDD) layers, testing requires specific patterns to ensure reliability without introducing flaky tests.

## 1. Test Environment Setup

We use `pytest` as our primary testing framework. 

**Install testing dependencies:**
```bash
pip install pytest pytest-qt pytest-asyncio pytest-mock httpx
```

**Directory Structure:**
All tests must reside in the `tests/` directory at the root of the project, mirroring the `src/` structure where possible:
```text
tests/
├── domain/         # Pure Python entity tests
├── application/    # Use case tests (mocked repos)
├── infrastructure/ # SQLite and API client tests
├── presentation/   # PyQt6 UI tests (pytest-qt)
└── api/            # FastAPI endpoint tests
```

**Running Tests:**
```bash
pytest                 # Run all tests
pytest -v              # Run with verbose output
pytest tests/domain/   # Run only domain tests
```

---

## 2. Testing the Domain Layer
The Domain layer contains pure Python dataclasses. These tests should be extremely fast and require **zero** external mocking.

**Example: `tests/domain/test_entities.py`**
```python
from src.domain.entities import MediaItem

def test_media_item_creation():
    """Test that a MediaItem initializes correctly with default and provided values."""
    item = MediaItem(
        title="Inception",
        relative_path="/movies/inception",
        media_type="movie"
    )
    
    assert item.title == "Inception"
    assert item.is_season == 0
    assert item.db_status == "Pending" # Assuming default state
```

---

## 3. Testing the Application Layer (Use Cases)
Use Cases contain business logic. They orchestrate data between the UI and the database. You must **mock the Infrastructure layer** (Repositories, APIs) when testing Use Cases.

**Example: `tests/application/test_add_media_use_case.py`**
```python
import pytest
from unittest.mock import MagicMock
from src.application.use_cases.media_use_cases import AddMediaUseCase

def test_add_media_use_case_success():
    # 1. Arrange: Create a mock repository
    mock_repo = MagicMock()
    mock_repo.insert_item.return_value = 1  # Mock the DB returning an ID
    
    use_case = AddMediaUseCase(repo=mock_repo)
    
    # 2. Act: Execute the use case
    item_id = use_case.execute(
        relative_path="/data/movies/matrix",
        image_url="[http://example.com/matrix.jpg](http://example.com/matrix.jpg)",
        title="The Matrix",
        media_type="movie"
    )
    
    # 3. Assert: Verify the use case interacted with the repo correctly
    assert item_id == 1
    mock_repo.insert_item.assert_called_once()
    
    # Verify the created entity passed to the repo has the correct data
    called_item = mock_repo.insert_item.call_args[0][0]
    assert called_item.title == "The Matrix"
```

---

## 4. Testing the Infrastructure Layer
This layer interacts with the outside world (Databases, External APIs).

### A. Testing the SQLite Repository
Never test against the production database. Use an **in-memory database** (`:memory:`) to ensure tests are isolated and fast.

**Example: `tests/infrastructure/test_sqlite_repository.py`**
```python
import pytest
from src.infrastructure.repositories.sqlite_media_repository import SqliteMediaRepository
from src.domain.entities import MediaItem

@pytest.fixture
def memory_repo():
    """Provides a fresh, isolated in-memory database for each test."""
    repo = SqliteMediaRepository(db_path=":memory:")
    repo.initialize_db() # Ensure tables are created
    return repo

def test_repository_insert_and_retrieve(memory_repo):
    item = MediaItem(title="Avatar", relative_path="/movies/avatar", media_type="movie")
    
    # Insert
    inserted_id = memory_repo.insert_item(item)
    assert inserted_id is not None
    
    # Retrieve
    fetched_item = memory_repo.get_item_by_id(inserted_id)
    assert fetched_item.title == "Avatar"
```

### B. Mocking External Services (TMDB / qBittorrent)
Do not make actual HTTP requests during tests. Use `pytest-mock` (`mocker`) to intercept requests.

**Example: `tests/infrastructure/test_tmdb_fetcher.py`**
```python
def test_tmdb_fetcher_success(mocker):
    # Mock the requests.get response
    mock_response = mocker.Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"title": "Interstellar", "overview": "Space stuff."}
    mocker.patch("requests.get", return_value=mock_response)
    
    # Run your TMDB service logic here and assert it parses the mock response correctly
```

---

## 5. Testing the Presentation Layer (PyQt6)
UI testing requires the `pytest-qt` plugin. Do **not** instantiate `QApplication` manually; use the `qtbot` fixture provided by `pytest-qt`.

### Key Rules for UI Tests:
1. **Never use `time.sleep()`**. Use `qtbot.waitUntil()` or `qtbot.waitSignal()`.
2. Do not show the window (`.show()`) during CI tests to avoid stealing focus.

**Example: `tests/presentation/test_main_dashboard.py`**
```python
import pytest
from PyQt6.QtCore import Qt
from src.presentation.windows.main_dashboard import MainDashboard

def test_search_input_filters_grid(qtbot, mocker):
    # Arrange: Mock dependencies
    mock_repo = mocker.Mock()
    mock_profile = mocker.Mock()
    mock_controller = mocker.Mock()
    
    # Initialize the dashboard
    dashboard = MainDashboard(mock_profile, mock_controller, mock_repo)
    qtbot.addWidget(dashboard) # Register widget with qtbot
    
    # Act: Simulate user typing into the search bar
    search_bar = dashboard.header_nav.search_input
    qtbot.keyClicks(search_bar, 'Inception')
    
    # Assert: Verify the search triggered the appropriate filter method
    assert search_bar.text() == 'Inception'
```

---

## 6. Testing the FastAPI Backend
Testing the asynchronous FastAPI backend requires `httpx.AsyncClient` or the built-in `TestClient`.

**Example: `tests/api/test_api_server.py`**
```python
import pytest
from fastapi.testclient import TestClient
from src.infrastructure.services.api_server import app

client = TestClient(app)

def test_health_check_endpoint():
    """Verify the API is running and responding."""
    response = client.get("/health")
    
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
```