from PyQt6.QtCore import Qt, QSize
from PyQt6.QtWidgets import (
    QDialog, QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QComboBox, QLineEdit, QButtonGroup
)
from PyQt6.QtGui import QIcon
import os

class MediaCategoryDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Construct path")
        self.setFixedSize(450, 300)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._is_movie = True

        root = QWidget(self)
        root.setGeometry(0, 0, 450, 300)
        root.setObjectName("card")
        root.setStyleSheet("""
            QWidget#card {
                background-color: #1A1D24;
                border-radius: 16px;
                border: 1px solid rgba(255, 255, 255, 0.05);
            }
        """)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(root)

        layout = QVBoxLayout(root)
        layout.setSpacing(24)
        layout.setContentsMargins(32, 28, 32, 28)

        # ── Title bar with Close button ────────────────────────────
        title_row = QHBoxLayout()
        lbl_title = QLabel("Construct path")
        lbl_title.setStyleSheet("font-size: 15pt; font-weight: 700; color: #F8FAFC;")
        title_row.addWidget(lbl_title)
        
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
        title_row.addWidget(btn_close)
        
        layout.addLayout(title_row)

        # ── Toggle Container ───────────────────────────────────────
        self.toggle_container = QWidget()
        self.toggle_container.setObjectName("ToggleContainer")
        self.toggle_container.setFixedHeight(40)
        
        toggle_layout = QHBoxLayout(self.toggle_container)
        toggle_layout.setContentsMargins(4, 4, 4, 4)
        toggle_layout.setSpacing(4)
        
        self.btn_movie = QPushButton("Movie")
        self.btn_movie.setObjectName("ToggleButton")
        self.btn_movie.setFixedHeight(32)
        self.btn_movie.setCheckable(True)
        self.btn_movie.setChecked(True)
        self.btn_movie.setCursor(Qt.CursorShape.PointingHandCursor)
        
        self.btn_tv = QPushButton("TV-Series")
        self.btn_tv.setObjectName("ToggleButton")
        self.btn_tv.setFixedHeight(32)
        self.btn_tv.setCheckable(True)
        self.btn_tv.setCursor(Qt.CursorShape.PointingHandCursor)
        
        self.toggle_group = QButtonGroup(self)
        self.toggle_group.setExclusive(True)
        self.toggle_group.addButton(self.btn_movie, 0)
        self.toggle_group.addButton(self.btn_tv, 1)
        self.toggle_group.buttonClicked.connect(self._select_type)
        
        toggle_layout.addWidget(self.btn_movie)
        toggle_layout.addWidget(self.btn_tv)
        layout.addWidget(self.toggle_container)

        # ── Genre dropdown (movie mode) ────────────────────────────
        self.genre_container = QWidget()
        genre_row = QHBoxLayout(self.genre_container)
        genre_row.setContentsMargins(0, 0, 0, 0)
        genre_row.setSpacing(14)

        lbl_genre = QLabel("Genre")
        lbl_genre.setStyleSheet("font-size: 11pt; font-weight: 600; color: #F8FAFC;")
        lbl_genre.setFixedWidth(64)

        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        chevron_down_path = os.path.join(base_dir, "assets", "chevron_down.svg").replace("\\", "/")

        self.genre_dropdown = QComboBox()
        self.genre_dropdown.addItems([
            "action", "adventure", "anime", "comedy",
            "crime", "drama", "horror", "sf", "thriller"
        ])
        self.genre_dropdown.setFixedHeight(44)
        self.genre_dropdown.setStyleSheet(f"""
            QComboBox {{
                background-color: transparent;
                border: 1px solid rgba(255, 255, 255, 0.05);
                border-radius: 12px;
                padding-left: 14px;
                padding-right: 36px;
                font-size: 10.5pt;
                color: #8B949E;
            }}
            QComboBox:focus {{
                border-color: #3b82f6;
            }}
            QComboBox::drop-down {{
                subcontrol-origin: padding;
                subcontrol-position: right center;
                width: 38px;
                border: none;
                background: transparent;
            }}
            QComboBox::down-arrow {{
                image: url({chevron_down_path});
                width: 20px;
                height: 20px;
            }}
            QComboBox QAbstractItemView {{
                background-color: #1A1D24;
                border: 1px solid rgba(255, 255, 255, 0.05);
                border-bottom-left-radius: 12px;
                border-bottom-right-radius: 12px;
                selection-background-color: #3b82f6;
                selection-color: #ffffff;
                color: #8B949E;
                padding: 4px;
                outline: 0;
            }}
        """)

        genre_row.addWidget(lbl_genre)
        genre_row.addWidget(self.genre_dropdown, 1)
        layout.addWidget(self.genre_container)

        # ── Series name input (TV mode, hidden by default) ─────────
        self.series_container = QWidget()
        series_row = QHBoxLayout(self.series_container)
        series_row.setContentsMargins(0, 0, 0, 0)
        series_row.setSpacing(14)

        lbl_series = QLabel("Series")
        lbl_series.setStyleSheet("font-size: 11pt; font-weight: 600; color: #F8FAFC;")
        lbl_series.setFixedWidth(64)

        self.series_input = QLineEdit()
        self.series_input.setPlaceholderText("e.g. breaking bad")
        self.series_input.setFixedHeight(44)
        self.series_input.setStyleSheet("""
            QLineEdit {
                background-color: transparent;
                border: 1px solid rgba(255, 255, 255, 0.05);
                border-radius: 12px;
                padding-left: 14px;
                font-size: 10.5pt;
                color: #F8FAFC;
            }
            QLineEdit:focus {
                border-color: #3b82f6;
            }
        """)

        series_row.addWidget(lbl_series)
        series_row.addWidget(self.series_input, 1)
        self.series_container.hide()
        layout.addWidget(self.series_container)

        layout.addStretch()

        # ── Action buttons ─────────────────────────────────────────
        btn_row = QHBoxLayout()
        btn_row.setSpacing(12)
        btn_row.addStretch()

        btn_cancel = QPushButton("Cancel")
        btn_cancel.setFixedHeight(40)
        btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_cancel.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #8B949E;
                border: none;
                border-radius: 8px;
                padding: 0 20px;
                font-weight: 600;
                font-size: 10.5pt;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.05);
                color: #F8FAFC;
            }
        """)
        btn_cancel.clicked.connect(self.reject)

        btn_ok = QPushButton("Confirm")
        btn_ok.setFixedHeight(40)
        btn_ok.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_ok.setStyleSheet("""
            QPushButton {
                background-color: #3b82f6;
                color: #ffffff;
                border: none;
                border-radius: 8px;
                padding: 0 24px;
                font-weight: 600;
                font-size: 10.5pt;
            }
            QPushButton:hover { background-color: #2563eb; }
        """)
        btn_ok.clicked.connect(self.accept)

        btn_row.addWidget(btn_cancel)
        btn_row.addWidget(btn_ok)
        layout.addLayout(btn_row)

    def _select_type(self, button) -> None:
        is_movie = (button == self.btn_movie)
        self._is_movie = is_movie
        self.genre_container.setVisible(is_movie)
        self.series_container.setVisible(not is_movie)

    def get_relative_path(self) -> str:
        if self._is_movie:
            return f"movies/{self.genre_dropdown.currentText()}"
        else:
            name = self.series_input.text().strip().replace(" ", ".")
            return f"tv-series/{name if name else 'unknown_series'}"
