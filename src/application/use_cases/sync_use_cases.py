from src.domain.repositories import IMediaRepository
from src.application.events import event_bus

class SyncTorrentStateUseCase:
    """Updates the internal datastore with external qBittorrent telemetry and notifies the UI."""
    def __init__(self, repo: IMediaRepository):
        self.repo = repo

    def execute(self, item_id: int, torrent_data: str):
        self.repo.update_torrent_data(item_id, torrent_data)
        event_bus.torrent_updated_signal.emit(item_id)

class SyncConversionStateUseCase:
    """Updates the internal datastore with external SSH conversion telemetry and notifies the UI."""
    def __init__(self, repo: IMediaRepository):
        self.repo = repo

    def execute(self, item_id: int, conversion_data: str):
        self.repo.update_conversion_data(item_id, conversion_data)
        event_bus.conversion_updated_signal.emit(item_id)
        
class UpdateMetadataUseCase:
    """Updates the metadata (TMDB scrape results, descriptions, genres) of a MediaItem."""
    def __init__(self, repo: IMediaRepository):
        self.repo = repo
        
    def execute(self, item_id: int, description: str, genre: str, rating: str):
        self.repo.update_metadata(item_id, description, genre, rating)
        event_bus.metadata_updated_signal.emit(item_id)
