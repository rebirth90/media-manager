import json
from PyQt6.QtWidgets import QWidget
from PyQt6.QtGui import QPainter, QColor, QPen, QPainterPath
from PyQt6.QtCore import Qt, QRectF
import re

def calculate_conversion_progress(telemetry_data: dict) -> tuple[str, int]:
    """
    Calculates the exact state and an overall 0-100 progress percentage 
    based on the 8 backend pipeline steps and FFmpeg telemetry.
    """
    db_status = telemetry_data.get("db_status", "NOT STARTED").upper()
    
    if db_status in ["NOT STARTED", "PENDING"]: return "Not Started", 0
    if db_status == "COMPLETED": return "Completed", 100
    if db_status in ["FAILED", "REJECTED"]: return "Failed", 0
        
    try:
        flags = json.loads(telemetry_data.get("stage_results", "{}"))
    except (json.JSONDecodeError, TypeError):
        flags = {}
        
    ff_prog = int(telemetry_data.get("prog", 0))

    if "p8-relocate" in flags or "p8-cleanup" in flags:
        return "Finalizing", 95
    elif "p7-tiers" in flags and "p7-outcome" not in flags:
        overall_prog = 10 + int(ff_prog * 0.80) 
        return "Encoding Video", overall_prog
    elif "p6-discovery" in flags:
        return "Extracting Subtitles", 8
    elif "p5-check" in flags:
        return "Validating Targets", 5
    elif "p3-router" in flags:
        return "Initializing Media", 3
    elif "p1-queue" in flags or "p2-dequeue" in flags:
        return "Queued", 1
        
    return "Starting", 0

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
            
            # If multiple are active, we just grab the first one we see
            if not active_ep_name: 
                active_ep_name = ep_id
                active_ep_status = status_text

    # Calculate true overall average percentage
    overall_percentage = int(total_progress_sum / total_eps)

    if completed_eps == total_eps:
        return "Completed", 100
    elif active_ep_name:
        # e.g., "Converting E04 (Encoding Video)"
        return f"Converting {active_ep_name} ({active_ep_status})", overall_percentage
    elif completed_eps > 0:
        return f"Processing ({completed_eps}/{total_eps} Done)", overall_percentage
    else:
        return "Starting Season...", overall_percentage

class ProgressPillWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._state_text = "Not Started"
        self._percentage = 0
        self.setFixedHeight(24)
        self.setMinimumWidth(100)
    
    def set_data(self, state_text: str, percentage: int):
        self._state_text = state_text
        self._percentage = percentage
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = self.rect()
        margin = 0
        pill_rect = QRectF(float(margin), float(margin), float(rect.width() - (margin * 2)), float(rect.height() - (margin * 2)))
        radius = pill_rect.height() / 2.0

        bg_color = QColor("#2D2D30")
        fill_color = QColor("#007ACC") 
        text_color = QColor("#FFFFFF")
        
        if self._state_text == "Completed": fill_color = QColor("#28A745")
        elif self._state_text == "Failed": fill_color = QColor("#DC3545")
        elif self._state_text == "Not Started": fill_color = QColor("#6C757D")

        # Draw Background
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(bg_color)
        painter.drawRoundedRect(pill_rect, radius, radius)

        # Draw Progress Fill
        if self._percentage > 0:
            fill_width = pill_rect.width() * (self._percentage / 100.0)
            progress_rect = QRectF(pill_rect.x(), pill_rect.y(), fill_width, pill_rect.height())
            painter.setBrush(fill_color)
            
            path = QPainterPath()
            path.addRoundedRect(pill_rect, radius, radius)
            painter.setClipPath(path)
            painter.drawRect(progress_rect)
            painter.setClipping(False)

        # Draw Text
        font = self.font()
        font.setPointSize(9)
        painter.setFont(font)
        painter.setPen(QPen(text_color))
        display_text = f"{self._state_text} {self._percentage}%" if self._percentage not in [0, 100] else self._state_text
        painter.drawText(pill_rect, Qt.AlignmentFlag.AlignCenter, display_text)

        painter.end()
