from PyQt6.QtCore import QObject, pyqtSignal

class EventBus(QObject):
    """Global EventBus to decouple Infrastructure/Application layer state changes from the Presentation layer UI."""
    # Database level signals (payload is media_id)
    torrent_updated_signal = pyqtSignal(int)
    conversion_updated_signal = pyqtSignal(int)
    media_added_signal = pyqtSignal(int)
    media_deleted_signal = pyqtSignal(int)
    metadata_updated_signal = pyqtSignal(int)

# Global singleton instance for the application
event_bus = EventBus()
