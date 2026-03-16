from dataclasses import dataclass, field
from typing import Optional, Dict, Any

@dataclass
class TorrentState:
    """Domain entity representing the state of a torrent download."""
    hash: str
    name: str = ""
    progress: float = 0.0
    state: str = ""
    save_path: str = ""
    eta: int = 0
    download_speed: int = 0
    total_size: int = 0

@dataclass
class ConversionJob:
    """Domain entity representing a conversion pipeline job."""
    path: str
    db_status: str = "Pending"
    stage_results: Dict[str, str] = field(default_factory=dict)
    sub_status: str = "Pending"
    gen_log: str = ""
    ff_tail: str = ""
    prog: int = 0
    initial_size_bytes: int = 0
    final_size_bytes: int = 0
    size_diff_pct: float = 0.0
    conversion_total_minutes: float = 0.0
    gen_log_remote_path: str = ""
    ff_log_remote_path: str = ""
    gen_log_local_path: str = ""
    ff_log_local_path: str = ""

@dataclass
class MediaItem:
    """Domain entity representing a trackable media item."""
    id: Optional[int] = None
    relative_path: str = ""
    image_url: Optional[str] = None
    title: str = ""
    season: str = ""
    description: Optional[str] = None
    genre: Optional[str] = None
    rating: Optional[str] = None
    torrent_data: Optional[str] = None
    conversion_data: Optional[str] = None
    is_season: int = 0
    media_type: str = 'movie'
    tmdb_id: Optional[str] = None
