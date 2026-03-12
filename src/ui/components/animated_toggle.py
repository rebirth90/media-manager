import os
from PyQt6.QtCore import Qt, pyqtProperty, pyqtSignal, QPropertyAnimation, QEasingCurve, QRectF
from PyQt6.QtGui import QPainter, QColor, QFont, QPen, QPainterPath
from PyQt6.QtWidgets import QWidget

class AnimatedToggle(QWidget):
    """
    A custom animated sliding toggle switch (segmented control).
    Uses QPropertyAnimation and QPainter for a native non-blocking 60fps animation.
    """
    toggled = pyqtSignal(int)  # Emits 0 for option1, 1 for option2
    
    def __init__(self, option1: str, option2: str, parent=None):
        super().__init__(parent)
        self.option1 = option1
        self.option2 = option2
        self._current_index = 0
        
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumWidth(200)
        self.setMinimumHeight(24) 
        
        # Colors (Adhering to COLOR_SYSTEM.md and style_dark.py)
        self.bg_color = QColor(255, 255, 255, 8)       # rgba(255, 255, 255, 0.03)
        self.border_color = QColor(255, 255, 255, 13)  # rgba(255, 255, 255, 0.05)
        self.thumb_color = QColor("#3b82f6")           # Primary blue
        self.text_active_color = QColor("#ffffff")
        self.text_inactive_color = QColor("#8B949E")
        
        self._thumb_x = 4.0
        
        self._animation = QPropertyAnimation(self, b"thumb_x", self)
        self._animation.setDuration(180)
        self._animation.setEasingCurve(QEasingCurve.Type.InOutQuad)

    @pyqtProperty(float)
    def thumb_x(self):
        return self._thumb_x

    @thumb_x.setter
    def thumb_x(self, pos: float):
        self._thumb_x = pos
        self.update()

    def set_index(self, index: int, animate: bool = True):
        self._current_index = index
        self._animate_to_index(index, animate)

    def _animate_to_index(self, index: int, animate: bool):
        thumb_width = (self.width() - 8) / 2.0
        target_x = 4.0 if index == 0 else 4.0 + thumb_width
        
        if animate:
            self._animation.setEndValue(target_x)
            self._animation.start()
        else:
            self.thumb_x = target_x

    def index(self) -> int:
        return self._current_index

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            click_x = event.position().x()
            new_index = 0 if click_x < self.width() / 2 else 1
            if new_index != self._current_index:
                self.set_index(new_index, animate=True)
                self.toggled.emit(self._current_index)
        super().mousePressEvent(event)

    def resizeEvent(self, event):
        self._animate_to_index(self._current_index, animate=False)
        super().resizeEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Draw Background Pill
        rect = self.rect()
        path = QPainterPath()
        bg_radius = rect.height() / 2.0
        path.addRoundedRect(QRectF(rect), bg_radius, bg_radius)
        
        painter.fillPath(path, self.bg_color)
        pen = QPen(self.border_color)
        pen.setWidth(1)
        painter.setPen(pen)
        painter.drawPath(path)
        
        # Draw Thumb (Sliding indicator)
        thumb_width = (self.width() - 8) / 2.0
        thumb_rect = QRectF(self._thumb_x, 4.0, thumb_width, self.rect().height() - 8.0)
        thumb_path = QPainterPath()
        thumb_radius = thumb_rect.height() / 2.0
        thumb_path.addRoundedRect(thumb_rect, thumb_radius, thumb_radius)
        painter.fillPath(thumb_path, self.thumb_color)
        
        # Draw Text
        font = self.font()
        font.setPointSize(9 if self.height() < 30 else 10)
        font.setWeight(QFont.Weight.DemiBold)
        painter.setFont(font)
        
        opt1_rect = QRectF(4.0, 4.0, thumb_width, self.rect().height() - 8.0)
        opt2_rect = QRectF(4.0 + thumb_width, 4.0, thumb_width, self.rect().height() - 8.0)

        painter.setPen(self.text_active_color if self._current_index == 0 else self.text_inactive_color)
        painter.drawText(opt1_rect, Qt.AlignmentFlag.AlignCenter, self.option1)
        
        painter.setPen(self.text_active_color if self._current_index == 1 else self.text_inactive_color)
        painter.drawText(opt2_rect, Qt.AlignmentFlag.AlignCenter, self.option2)
        
        painter.end()
