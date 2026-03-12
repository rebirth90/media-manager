from PyQt6.QtCore import Qt, QSize
from PyQt6.QtWidgets import (
    QDialog, QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QButtonGroup
)
from PyQt6.QtGui import QIcon
import os

class DeleteTorrentDialog(QDialog):
    def __init__(self, torrent_name: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Delete 1 torrent")
        self.setFixedSize(450, 260)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        root = QWidget(self)
        root.setGeometry(0, 0, 450, 260)
        root.setObjectName("card")
        root.setStyleSheet("""
            QWidget#card {
                background-color: #1A1D24;
                border-radius: 16px;
                border: 1px solid rgba(255, 255, 255, 0.05);
            }
        """)

        layout = QVBoxLayout(root)
        layout.setSpacing(20)
        layout.setContentsMargins(24, 24, 24, 24)

        # ── Title bar with Close button ────────────────
        title_row = QHBoxLayout()
        title_row.setSpacing(8)
        
        lbl_title = QLabel(f'<span style="font-size: 14pt; font-weight: 600; color: #E2E8F0;">Delete {torrent_name}</span>')
        title_row.addWidget(lbl_title)
        title_row.addStretch()
        
        btn_close = QPushButton()
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        close_icon_path = os.path.join(base_dir, "assets", "win_close.svg").replace("\\", "/")
        btn_close.setIcon(QIcon(close_icon_path))
        btn_close.setIconSize(QSize(14, 14))
        btn_close.setFixedSize(24, 24)
        btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_close.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
            }
            QPushButton:hover { background-color: rgba(255, 255, 255, 0.1); border-radius: 4px; }
        """)
        btn_close.clicked.connect(self.reject)
        
        # Align close button to top
        close_container = QVBoxLayout()
        close_container.addWidget(btn_close)
        close_container.addStretch()
        title_row.addLayout(close_container)
        
        layout.addLayout(title_row)
        layout.addSpacing(16)

        # ── Toggle Container ───────────────────────────────────────
        from src.ui.components.animated_toggle import AnimatedToggle
        self.animated_toggle = AnimatedToggle("App data", "App and torrent data")
        self.animated_toggle.setFixedHeight(48)
        layout.addWidget(self.animated_toggle)

        layout.addStretch()

        # ── Action buttons ─────────────────────────────────────────
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(16)
        btn_layout.addStretch()

        btn_delete = QPushButton("DELETE")
        btn_delete.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_delete.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #ef4444;
                border: none;
                font-weight: 700;
                font-size: 10.5pt;
                padding: 8px 12px;
                border-radius: 6px;
                letter-spacing: 1px;
            }
            QPushButton:hover { background-color: rgba(239, 68, 68, 0.1); }
        """)
        btn_delete.clicked.connect(self.accept)

        btn_cancel = QPushButton("CANCEL")
        btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_cancel.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #8B949E;
                border: none;
                font-weight: 700;
                font-size: 10.5pt;
                padding: 8px 12px;
                border-radius: 6px;
                letter-spacing: 1px;
            }
            QPushButton:hover { background-color: rgba(255, 255, 255, 0.05); color: #F8FAFC; }
        """)
        btn_cancel.clicked.connect(self.reject)

        # Notice order: Delete then Cancel according to screenshot "DELETE  CANCEL"
        btn_layout.addWidget(btn_delete)
        btn_layout.addWidget(btn_cancel)
        layout.addLayout(btn_layout)

    def should_delete_files(self) -> bool:
        # Index 0 is "App data"
        # Index 1 is "App and torrent data"
        return self.animated_toggle.index() == 1
