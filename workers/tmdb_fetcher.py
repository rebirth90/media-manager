import os
import requests
from PyQt6.QtCore import QThread, pyqtSignal

class TMDBFetcherThread(QThread):
    title_resolved = pyqtSignal(str)
    details_resolved = pyqtSignal(dict)
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
        
        # IMDB Fallback Resolution
        if self.tmdb_id.startswith("tt") or self.media_type == "imdb":
            find_url = f"https://api.themoviedb.org/3/find/{self.tmdb_id}?external_source=imdb_id"
            try:
                find_res = requests.get(find_url, headers=headers, timeout=10)
                if find_res.status_code == 200:
                    find_data = find_res.json()
                    if find_data.get("tv_results"):
                        self.tmdb_id = str(find_data["tv_results"][0]["id"])
                        self.media_type = "tv"
                    elif find_data.get("movie_results"):
                        self.tmdb_id = str(find_data["movie_results"][0]["id"])
                        self.media_type = "movie"
                    else:
                        self.error.emit("IMDB ID not found in TMDB.")
                        self.title_resolved.emit(self.tmdb_id)
                        return
                else:
                    self.error.emit(f"TMDB Find API Error: {find_res.status_code}")
                    self.title_resolved.emit(self.tmdb_id)
                    return
            except Exception as e:
                self.error.emit(str(e))
                self.title_resolved.emit(self.tmdb_id)
                return

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
                
                full_title = f"{title}{year}" if title else self.tmdb_id
                genres = [g.get("name") for g in data.get("genres", [])]
                genre_str = ", ".join(genres) if genres else "Unknown"
                rating = str(round(data.get("vote_average", 0), 1)) if data.get("vote_average") else "-"
                desc = data.get("overview", "No description available.")
                poster_path = data.get("poster_path")
                img_url = f"https://image.tmdb.org/t/p/w300_and_h450_bestv2{poster_path}" if poster_path else ""
                
                self.title_resolved.emit(full_title)
                self.details_resolved.emit({
                    "description": desc,
                    "genre": genre_str,
                    "rating": rating,
                    "image_url": img_url
                })
            else:
                self.error.emit(f"TMDB API Error: {response.status_code}")
                self.title_resolved.emit(self.tmdb_id)
        except Exception as e:
            self.error.emit(str(e))
            self.title_resolved.emit(self.tmdb_id)
