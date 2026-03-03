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
            conn.commit()

    def add_item(self, relative_path: str, image_url: str, title: str, season: str = "") -> int:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO media_items (relative_path, image_url, title, season)
                VALUES (?, ?, ?, ?)
            ''', (relative_path, image_url, title, season))
            conn.commit()
            return cursor.lastrowid

    def get_all_items(self) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('SELECT id, relative_path, image_url, title, season FROM media_items')
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def delete_item(self, item_id: int) -> bool:
        if item_id is None:
            return False
            
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM media_items WHERE id = ?', (item_id,))
            conn.commit()
            return cursor.rowcount > 0
