from src.domain.repositories import IMediaRepository
from src.domain.entities import MediaItem
from src.application.events import event_bus

class AddMediaUseCase:
    """Use Case for adding a newly scraped/requested MediaItem to the datastore."""
    def __init__(self, repo: IMediaRepository):
        self.repo = repo

    def execute(self, relative_path: str, image_url: str, title: str, season: str = "", is_season: int = 0, media_type: str = 'movie') -> int:
        item = MediaItem(
            relative_path=relative_path,
            image_url=image_url,
            title=title,
            season=season,
            is_season=is_season,
            media_type=media_type
        )
        item_id = self.repo.add_item(item)
        event_bus.media_added_signal.emit(item_id)
        return item_id

class DeleteMediaUseCase:
    """Use Case for deleting a MediaItem from the datastore."""
    def __init__(self, repo: IMediaRepository):
        self.repo = repo
        
    def execute(self, item_id: int) -> bool:
        success = self.repo.delete_item(item_id)
        if success:
            event_bus.media_deleted_signal.emit(item_id)
        return success
