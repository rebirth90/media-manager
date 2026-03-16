import json
import os
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel
from PyQt6.QtGui import QMovie
from PyQt6.QtCore import Qt
import re

def calculate_conversion_progress(telemetry_data: dict) -> tuple[str, int]:
    """
    Calculates the exact state and an overall 0-100 progress percentage 
    based on the backend pipeline steps and FFmpeg telemetry.
    """
    db_status = telemetry_data.get("db_status", telemetry_data.get("status", "NOT STARTED")).upper()
    
    # Safe Dictionary/String Parsing Fallback
    raw_flags = telemetry_data.get("stage_results", {})
    if isinstance(raw_flags, str):
        try:
            flags = json.loads(raw_flags) if raw_flags else {}
        except (json.JSONDecodeError, TypeError):
            flags = {}
    else:
        flags = raw_flags or {}
        
    # Safely parse FFmpeg progress (handles empty strings and nulls safely)
    try:
        raw_prog = telemetry_data.get("prog", 0)
        ff_prog = int(float(raw_prog)) if raw_prog else 0
    except (ValueError, TypeError):
        ff_prog = 0

    # Explicit DB Status Overrides
    if db_status == "COMPLETED" or "p8-complete" in flags: 
        return "Completed", 100
    if db_status in ["FAILED", "REJECTED"]: 
        return "Failed", 0
        
    # Expanded Elif Chain
    if "p8-relocate" in flags or "p8-cleanup" in flags:
        return "Finalizing", 95
    elif "p7-tiers" in flags or "p7-t1" in flags or "p7-t2" in flags or "p7-t3" in flags:
        overall_prog = 10 + int(ff_prog * 0.80) 
        return "Encoding Video", overall_prog
    elif "p7-audio" in flags or "p7-heuristics" in flags: 
        return "Processing Audio", 9
    elif "p6-discovery" in flags or "p6-vobsub" in flags or "p6-text" in flags:
        return "Extracting Subtitles", 8
    elif "p5-check" in flags or "p5-pass" in flags:
        return "Validating Targets", 5
    elif "p4-movie" in flags or "p4-tv" in flags:
        return "Processing Metadata", 4
    elif "p3-router" in flags:
        return "Initializing Media", 3
    elif "p1-queue" in flags or "p2-dequeue" in flags or db_status == "PENDING":
        return "Queued", 1
        
    if db_status == "PROCESSING":
        return "Processing", 2

    return "Not Started", 0

def calculate_season_progress(episodes_telemetry: list[dict]) -> tuple[str, int]:
    """
    Calculates the combined progress of a full season and identifies the active episode.
    """
    if not episodes_telemetry:
        return "Not Started", 0

    total_eps = len(episodes_telemetry)
    completed_eps = 0
    active_ep_name = ""
    active_ep_status = ""
    total_progress_sum = 0

    for ep in episodes_telemetry:
        status_text, prog = calculate_conversion_progress(ep)
        total_progress_sum += prog

        if status_text == "Completed":
            completed_eps += 1
        elif status_text not in ["Not Started", "Failed", "Queued"]:
            # Extract Episode identifier from the path (e.g., E01, E02)
            path = ep.get("path", "")
            match = re.search(r'(?i)E\d{2}', path)
            ep_id = match.group().upper() if match else "EP"
            
            if not active_ep_name: 
                active_ep_name = ep_id
                active_ep_status = status_text

    overall_percentage = int(total_progress_sum / total_eps)

    if completed_eps == total_eps:
        return "Completed", 100
    elif active_ep_name:
        return f"Converting {active_ep_name} ({active_ep_status})", overall_percentage
    elif completed_eps > 0:
        return f"Processing ({completed_eps}/{total_eps} Done)", overall_percentage
    else:
        return "Not Started", overall_percentage

class ProgressPillWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._state_text = "Not Started"
        self._percentage = 0
        self.setFixedHeight(24)
        self.setMinimumWidth(80)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(4, 0, 4, 0)
        lay.setSpacing(6)

        self._icon_label = QLabel(self)
        self._icon_label.setFixedSize(16, 16)
        self._icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._text_label = QLabel("0%", self)
        self._text_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._text_label.setObjectName("SubText")

        lay.addWidget(self._icon_label)
        lay.addWidget(self._text_label)
        lay.addStretch(1)

        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        gif_path = os.path.join(base_dir, "assets", "icons8-loading-48.gif")
        self._movie = QMovie(gif_path)
        self._movie.setScaledSize(self._icon_label.size())
        self._icon_label.setMovie(self._movie)
        self._movie.start()
    
    def set_data(self, state_text: str, percentage: int):
        # Anti-Flicker check: Don't trigger repaints if nothing actually changed
        if self._state_text != state_text or self._percentage != percentage:
            self._state_text = state_text
            self._percentage = percentage
            self._text_label.setText(f"{self._percentage}%")

            is_terminal = self._state_text == "Completed" or "Failed" in self._state_text or self._state_text == "Not Started"
            if is_terminal:
                self._movie.stop()
            else:
                if self._movie.state() != QMovie.MovieState.Running:
                    self._movie.start()

    def setValue(self, value: int):
        self.set_data(self._state_text, int(value))