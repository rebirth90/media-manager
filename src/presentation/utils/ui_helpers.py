from PyQt6.QtWidgets import QPushButton, QGraphicsBlurEffect
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import Qt, QSize
import os

def apply_blur_effect(widget, radius=25):
    """Applies a standard blur effect to a given widget (typically main content behind a modal)."""
    blur_effect = QGraphicsBlurEffect()
    blur_effect.setBlurRadius(radius)
    widget.setGraphicsEffect(blur_effect)

def remove_blur_effect(widget):
    """Removes the blur effect from a widget."""
    widget.setGraphicsEffect(None)

def configure_window_control_button(btn: QPushButton, icon_path: str, obj_name: str = "WindowControlButton") -> None:
    """Configures common styling for window control buttons (minimize, maximize, close)."""
    if os.path.exists(icon_path):
        btn.setIcon(QIcon(icon_path))
    btn.setIconSize(QSize(20, 20))
    btn.setFixedSize(36, 36)
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    btn.setObjectName(obj_name)
