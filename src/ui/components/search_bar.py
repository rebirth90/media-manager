import os
from PyQt6.QtCore import Qt, QSize, pyqtSignal
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QLineEdit, QPushButton
)

class SearchBarWidget(QFrame):
    search_query_changed = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(48)
        self.setMaximumWidth(480)
        self.setMinimumWidth(280)
        
        self.setStyleSheet("""
            QFrame {
                background-color: #1A1D24;
                border: 1px solid rgba(255, 255, 255, 0.05);
                border-radius: 12px;
            }
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 0, 16, 0)
        layout.setSpacing(8)

        # Base dir relative to this file's deeper location in /src/ui/components 
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        
        # Search Icon
        self.lbl_icon = QLabel()
        self.lbl_icon.setPixmap(QIcon(os.path.join(base_dir, "assets", "search_icon.svg")).pixmap(20, 20))
        self.lbl_icon.setStyleSheet("border: none; background: transparent;")
        layout.addWidget(self.lbl_icon)

        # Input
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Search...")
        self.input_field.setStyleSheet("""
            QLineEdit {
                background: transparent;
                border: none;
                color: #f3f4f6;
                font-size: 11.5pt;
            }
            QLineEdit::placeholder {
                color: #6b7280;
            }
        """)
        layout.addWidget(self.input_field)

        # Clear Button
        self.clear_btn = QPushButton("✕")
        self.clear_btn.setFixedSize(24, 24)
        self.clear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.clear_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                border-radius: 12px;
                color: #6b7280;
                font-weight: bold;
                font-size: 13px;
                padding-bottom: 2px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.1);
                color: #f3f4f6;
            }
        """)
        self.clear_btn.hide()
        layout.addWidget(self.clear_btn)

        self.input_field.textChanged.connect(self._on_text_changed)
        self.clear_btn.clicked.connect(self.input_field.clear)

    def _on_text_changed(self, text: str):
        if text:
            self.clear_btn.show()
        else:
            self.clear_btn.hide()
        self.search_query_changed.emit(text)
