import os
import requests
from PyQt6.QtCore import QThread, pyqtSignal

class TMDBFetcherThread(QThread):
    title_resolved = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, tmdb_id: str, media_type: str, parent=None):
        super().__init__(parent)
        self.tmdb_id = tmdb_id
        self.media_type = media_type

    def run(self) -> None:
        token = os.getenv("TMDB_READ_ACCESS_TOKEN")
        
        # Fallback to the movie-conversion environment file where the token is known to exist
        if not token:
            env_path = r"c:\Users\Codrut\Documents\GitHub\movie-conversion\.env"
            if os.path.exists(env_path):
                with open(env_path, "r", encoding="utf-8") as f:
                    for line in f:
                        if line.startswith("TMDB_READ_ACCESS_TOKEN="):
                            token = line.split("=", 1)[1].strip()
                            token = token.strip('"').strip("'")
                            break
        
        if not token:
            self.error.emit("No TMDB Token found.")
            self.title_resolved.emit(self.tmdb_id)
            return

        headers = {
            "accept": "application/json",
            "Authorization": f"Bearer {token}"
        }
        url = f"https://api.themoviedb.org/3/{self.media_type}/{self.tmdb_id}"
        
        try:
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                title = data.get("title") if self.media_type == "movie" else data.get("name")
                year = ""
                if self.media_type == "movie" and data.get("release_date"):
                    year = f" ({data['release_date'][:4]})"
                elif self.media_type == "tv" and data.get("first_air_date"):
                    year = f" ({data['first_air_date'][:4]})"
                
                if title:
                    self.title_resolved.emit(f"{title}{year}")
                else:
                    self.title_resolved.emit(self.tmdb_id)
            else:
                self.error.emit(f"TMDB API Error: {response.status_code}")
                self.title_resolved.emit(self.tmdb_id)
        except Exception as e:
            self.error.emit(str(e))
            self.title_resolved.emit(self.tmdb_id)
