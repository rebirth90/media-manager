import os
import requests
import json
from PyQt6.QtCore import QThread, pyqtSignal

from src.domain.repositories import IMediaRepository

class TMDBFetcherThread(QThread):
    title_resolved = pyqtSignal(str)
    details_resolved = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, repo: IMediaRepository, tmdb_id: str, media_type: str, parent=None):
        super().__init__(parent)
        self.repo = repo
        self.tmdb_id = tmdb_id
        self.media_type = media_type

    def run(self) -> None:
        cached = self.repo.get_tmdb_cache(self.tmdb_id, self.media_type)
        if cached:
            try:
                data = json.loads(cached)
                self.title_resolved.emit(data.get("full_title", ""))
                self.details_resolved.emit(data.get("details", {}))
                return
            except json.JSONDecodeError:
                pass

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
            self.details_resolved.emit({})
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
                        self.details_resolved.emit({})
                        return
                else:
                    self.error.emit(f"TMDB Find API Error: {find_res.status_code}")
                    self.title_resolved.emit(self.tmdb_id)
                    self.details_resolved.emit({})
                    return
            except Exception as e:
                self.error.emit(str(e))
                self.title_resolved.emit(self.tmdb_id)
                self.details_resolved.emit({})
                return

        url = f"https://api.themoviedb.org/3/{self.media_type}/{self.tmdb_id}?append_to_response=external_ids"
        
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
                
                if not img_url:
                    imdb_id = data.get("imdb_id") or data.get("external_ids", {}).get("imdb_id")
                    if imdb_id:
                        import re
                        imdb_url = f"https://www.imdb.com/title/{imdb_id}/"
                        imdb_headers = {
                            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
                            "Accept-Language": "en-US,en;q=0.5"
                        }
                        try:
                            imdb_res = requests.get(imdb_url, headers=imdb_headers, timeout=10)
                            if imdb_res.status_code == 200:
                                match = re.search(r'<meta property="og:image" content="(.*?)"', imdb_res.text)
                                if match:
                                    img_url = match.group(1)
                        except Exception:
                            pass
                
                details_payload = {
                    "description": desc,
                    "genre": genre_str,
                    "rating": rating,
                    "image_url": img_url
                }
                
                # Cache the successful payload
                cache_payload = {
                    "full_title": full_title,
                    "details": details_payload
                }
                self.repo.set_tmdb_cache(self.tmdb_id, self.media_type, json.dumps(cache_payload))

                self.title_resolved.emit(full_title)
                self.details_resolved.emit(details_payload)
            else:
                self.error.emit(f"TMDB API Error: {response.status_code}")
                self.title_resolved.emit(self.tmdb_id)
                self.details_resolved.emit({})
        except Exception as e:
            self.error.emit(str(e))
            self.title_resolved.emit(self.tmdb_id)
            self.details_resolved.emit({})


class TMDBEpisodeFetcherThread(QThread):
    episodes_resolved = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, repo: IMediaRepository, tmdb_id: str, season_number: int, parent=None):
        super().__init__(parent)
        self.repo = repo
        self.tmdb_id = tmdb_id
        self.season_number = season_number

    def run(self) -> None:
        # Check cache first
        cache_key = f"eps_{self.tmdb_id}_{self.season_number}"
        cached = self.repo.get_tmdb_cache(cache_key, "tv_season")
        if cached:
            try:
                self.episodes_resolved.emit(json.loads(cached))
                return
            except:
                pass

        token = os.getenv("TMDB_READ_ACCESS_TOKEN")
        # Reuse fallback logic if needed, but assuming env is set for now
        if not token:
            env_path = r"c:\Users\Codrut\Documents\GitHub\movie-conversion\.env"
            if os.path.exists(env_path):
                with open(env_path, "r", encoding="utf-8") as f:
                    for line in f:
                        if line.startswith("TMDB_READ_ACCESS_TOKEN="):
                            token = line.split("=", 1)[1].strip().strip('"').strip("'")
                            break
        
        if not token:
            self.error.emit("No TMDB Token found.")
            return

        headers = {
            "accept": "application/json",
            "Authorization": f"Bearer {token}"
        }
        
        # External ID resolution for episodes
        if self.tmdb_id.startswith("tt"):
            find_url = f"https://api.themoviedb.org/3/find/{self.tmdb_id}?external_source=imdb_id"
            try:
                find_res = requests.get(find_url, headers=headers, timeout=10)
                if find_res.status_code == 200:
                    find_data = find_res.json()
                    if find_data.get("tv_results"):
                        self.tmdb_id = str(find_data["tv_results"][0]["id"])
                    else:
                        self.error.emit("IMDB ID not found in TMDB (TV).")
                        return
                else:
                    self.error.emit(f"TMDB Find API Error: {find_res.status_code}")
                    return
            except Exception as e:
                self.error.emit(str(e))
                return

        url = f"https://api.themoviedb.org/3/tv/{self.tmdb_id}/season/{self.season_number}"
        
        try:
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                ep_map = {}
                for ep in data.get("episodes", []):
                    ep_num = ep.get("episode_number")
                    still_path = ep.get("still_path")
                    still_url = f"https://image.tmdb.org/t/p/w300{still_path}" if still_path else ""
                    
                    ep_map[ep_num] = {
                        "name": ep.get("name"),
                        "overview": ep.get("overview"),
                        "air_date": ep.get("air_date"),
                        "still_url": still_url,
                        "vote_average": ep.get("vote_average", "-")
                    }
                self.repo.set_tmdb_cache(cache_key, "tv_season", json.dumps(ep_map))
                self.episodes_resolved.emit(ep_map)
            else:
                self.error.emit(f"TMDB Episode API Error: {response.status_code}")
        except Exception as e:
            self.error.emit(str(e))
