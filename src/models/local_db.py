import sqlite3
import os
from typing import List, Dict, Any

class LocalDBManager:
    def __init__(self, db_path: str = "local_data.db"):
        self.db_path = db_path
        self._init_db()

    def _get_connection(self):
        return sqlite3.connect(self.db_path)

    def _init_db(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS media_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    relative_path TEXT NOT NULL,
                    image_url TEXT,
                    title TEXT NOT NULL,
                    season TEXT
                )
            ''')
            
            # Dynamically inject new state columns into existing databases
            columns = [
                ("description", "TEXT"),
                ("genre", "TEXT"),
                ("rating", "TEXT"),
                ("torrent_data", "TEXT"),
                ("conversion_data", "TEXT"),
                ("is_season", "INTEGER DEFAULT 0"),
                ("media_type", "TEXT DEFAULT 'movie'") # 'movie' or 'tv-series'
            ]
            for col_name, col_type in columns:
                try:
                    cursor.execute(f'ALTER TABLE media_items ADD COLUMN {col_name} {col_type}')
                except sqlite3.OperationalError:
                    pass # Column already exists
                    
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS tmdb_cache (
                    id TEXT,
                    type TEXT,
                    data TEXT,
                    PRIMARY KEY (id, type)
                )
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS torrent_cache (
                    hash TEXT PRIMARY KEY,
                    path TEXT,
                    data TEXT
                )
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS conversion_cache (
                    path TEXT PRIMARY KEY,
                    data TEXT
                )
            ''')
            conn.commit()

    def add_item(self, relative_path: str, image_url: str, title: str, season: str = "", is_season: int = 0, media_type: str = 'movie') -> int:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO media_items (relative_path, image_url, title, season, is_season, media_type)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (relative_path, image_url, title, season, is_season, media_type))
            conn.commit()
            return cursor.lastrowid

    def get_all_items(self) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM media_items')
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def get_item(self, item_id: int) -> Dict[str, Any]:
        if item_id is None:
            return {}
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM media_items WHERE id = ?', (item_id,))
            row = cursor.fetchone()
            return dict(row) if row else {}

    def delete_item(self, item_id: int) -> bool:
        if item_id is None:
            return False
            
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM media_items WHERE id = ?', (item_id,))
            conn.commit()
            return cursor.rowcount > 0

    def update_item_title(self, item_id: int, title: str) -> None:
        if item_id is None:
            return
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('UPDATE media_items SET title = ? WHERE id = ?', (title, item_id))
            conn.commit()

    # --- APP STATE WRITING METHODS ---
    def update_metadata(self, item_id: int, description: str, genre: str, rating: str):
        if item_id is None: return
        with self._get_connection() as conn:
            conn.cursor().execute('UPDATE media_items SET description=?, genre=?, rating=? WHERE id=?', (description, genre, rating, item_id))
            conn.commit()

    def update_torrent_data(self, item_id: int, data: str):
        if item_id is None: return
        with self._get_connection() as conn:
            conn.cursor().execute('UPDATE media_items SET torrent_data=? WHERE id=?', (data, item_id))
            conn.commit()

    def update_conversion_data(self, item_id: int, data: str):
        if item_id is None: return
        with self._get_connection() as conn:
            conn.cursor().execute('UPDATE media_items SET conversion_data=? WHERE id=?', (data, item_id))
            conn.commit()

    # --- Caching Methods ---
    def get_tmdb_cache(self, tmdb_id: str, media_type: str) -> str:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT data FROM tmdb_cache WHERE id = ? AND type = ?', (tmdb_id, media_type))
            row = cursor.fetchone()
            return row[0] if row else ""

    def set_tmdb_cache(self, tmdb_id: str, media_type: str, data: str) -> None:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO tmdb_cache (id, type, data)
                VALUES (?, ?, ?)
            ''', (tmdb_id, media_type, data))
            conn.commit()

    def get_torrent_cache(self, hash_val: str) -> str:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT data FROM torrent_cache WHERE hash = ?', (hash_val,))
            row = cursor.fetchone()
            return row[0] if row else ""

    def set_torrent_cache(self, hash_val: str, path: str, data: str) -> None:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO torrent_cache (hash, path, data)
                VALUES (?, ?, ?)
            ''', (hash_val, path, data))
            conn.commit()

    def get_torrent_cache_by_path(self, path: str) -> str:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT data FROM torrent_cache WHERE path = ?', (path,))
            row = cursor.fetchone()
            return row[0] if row else ""

    def get_conversion_cache(self, path: str) -> str:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT data FROM conversion_cache WHERE path = ?', (path,))
            row = cursor.fetchone()
            return row[0] if row else ""

    def set_conversion_cache(self, path: str, data: str) -> None:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO conversion_cache (path, data)
                VALUES (?, ?)
            ''', (path, data))
            conn.commit()