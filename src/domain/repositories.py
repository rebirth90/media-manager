from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from src.domain.entities import MediaItem

class IMediaRepository(ABC):
    """Abstract base class for Media Repositories to enforce DDD boundaries."""

    @abstractmethod
    def add_item(self, item: MediaItem) -> int:
        pass

    @abstractmethod
    def get_all_items(self) -> List[MediaItem]:
        pass

    @abstractmethod
    def get_item(self, item_id: int) -> Optional[MediaItem]:
        pass

    @abstractmethod
    def delete_item(self, item_id: int) -> bool:
        pass

    @abstractmethod
    def update_item_title(self, item_id: int, title: str) -> None:
        pass

    @abstractmethod
    def update_metadata(self, item_id: int, description: str, genre: str, rating: str) -> None:
        pass

    @abstractmethod
    def update_torrent_data(self, item_id: int, data: str) -> None:
        pass

    @abstractmethod
    def update_conversion_data(self, item_id: int, data: str) -> None:
        pass

    @abstractmethod
    def get_tmdb_cache(self, tmdb_id: str, media_type: str) -> str:
        pass

    @abstractmethod
    def set_tmdb_cache(self, tmdb_id: str, media_type: str, data: str) -> None:
        pass

    @abstractmethod
    def get_torrent_cache(self, hash_val: str) -> str:
        pass
    
    @abstractmethod
    def set_torrent_cache(self, hash_val: str, path: str, data: str) -> None:
        pass

    @abstractmethod
    def get_torrent_cache_by_path(self, path: str) -> str:
        pass

    @abstractmethod
    def get_conversion_cache(self, path: str) -> str:
        pass

    @abstractmethod
    def set_conversion_cache(self, path: str, data: str) -> None:
        pass
