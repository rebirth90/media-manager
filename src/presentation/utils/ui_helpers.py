from PyQt6.QtWidgets import QPushButton, QGraphicsBlurEffect
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import Qt, QSize, QPoint, QEasingCurve, QPropertyAnimation, QParallelAnimationGroup
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


def animate_dialog_open(dialog, y_offset: int = 16, duration: int = 220) -> None:
    """Applies a fluid fade + subtle slide-in entrance animation to a dialog."""
    try:
        end_pos = dialog.pos()
        start_pos = QPoint(end_pos.x(), end_pos.y() + y_offset)

        dialog.setWindowOpacity(0.0)
        dialog.move(start_pos)

        opacity_anim = QPropertyAnimation(dialog, b"windowOpacity", dialog)
        opacity_anim.setDuration(duration)
        opacity_anim.setStartValue(0.0)
        opacity_anim.setEndValue(1.0)
        opacity_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        pos_anim = QPropertyAnimation(dialog, b"pos", dialog)
        pos_anim.setDuration(duration)
        pos_anim.setStartValue(start_pos)
        pos_anim.setEndValue(end_pos)
        pos_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        group = QParallelAnimationGroup(dialog)
        group.addAnimation(opacity_anim)
        group.addAnimation(pos_anim)
        dialog._open_anim_group = group
        group.start()
    except Exception:
        pass
