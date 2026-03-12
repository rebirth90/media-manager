from PyQt6.QtCore import Qt, QSize
from PyQt6.QtWidgets import (
    QDialog, QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QComboBox, QLineEdit, QButtonGroup, QCheckBox, QStackedWidget
)
from PyQt6.QtGui import QIcon
import os

class MediaCategoryDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Construct path")
        self.setFixedSize(450, 240) # Further reduced height
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._is_movie = True

        root = QWidget(self)
        root.setGeometry(0, 0, 450, 240)
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
        layout.setSpacing(12) # Tighter spacing
        layout.setContentsMargins(32, 20, 32, 20)

        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

        # ── Title bar with Close button ────────────────────────────
        title_row = QHBoxLayout()
        lbl_title = QLabel("Construct path")
        lbl_title.setStyleSheet("font-size: 15pt; font-weight: 700; color: #F8FAFC;")
        title_row.addWidget(lbl_title)
        
        btn_close = QPushButton()
        close_icon_path = os.path.join(base_dir, "assets", "win_close.svg").replace("\\", "/")
        btn_close.setIcon(QIcon(close_icon_path))
        btn_close.setIconSize(QSize(14, 14))
        btn_close.setFixedSize(24, 24)
        btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_close.setStyleSheet("""
            QPushButton { background: transparent; border: none; }
            QPushButton:hover { background-color: rgba(255, 255, 255, 0.1); border-radius: 4px; }
        """)
        btn_close.clicked.connect(self.reject)
        title_row.addWidget(btn_close)
        layout.addLayout(title_row)

        # ── Toggle Container ───────────────────────────────────────
        from src.ui.components.animated_toggle import AnimatedToggle
        self.animated_toggle = AnimatedToggle("Movie", "TV-Series")
        self.animated_toggle.setFixedHeight(48)
        self.animated_toggle.toggled.connect(self._select_type)
        layout.addWidget(self.animated_toggle)

        # ── Stacked Input Area (Ensures identical vertical pos) ──
        self.input_stack = QStackedWidget()
        self.input_stack.setFixedHeight(44)
        
        # 1. Genre Page
        genre_page = QWidget()
        genre_row = QHBoxLayout(genre_page)
        genre_row.setContentsMargins(0, 0, 0, 0)
        genre_row.setSpacing(14)
        
        lbl_genre = QLabel("Genre")
        lbl_genre.setStyleSheet("font-size: 11pt; font-weight: 600; color: #F8FAFC;")
        lbl_genre.setFixedWidth(100)
        
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
                border: 2px solid rgba(255, 255, 255, 0.05);
                border-radius: 12px;
                padding-left: 13px;
                padding-right: 35px;
                font-size: 10.5pt;
                color: #8B949E;
            }}
            QComboBox:focus {{ border: 2px solid #3b82f6; }}
            QComboBox::drop-down {{ subcontrol-origin: padding; subcontrol-position: right center; width: 38px; border: none; background: transparent; }}
            QComboBox::down-arrow {{ image: url({chevron_down_path}); width: 20px; height: 20px; }}
            QComboBox QAbstractItemView {{ background-color: #1A1D24; color: #8B949E; selection-background-color: #3b82f6; outline: 0; }}
        """)
        genre_row.addWidget(lbl_genre)
        genre_row.addWidget(self.genre_dropdown, 1)
        self.input_stack.addWidget(genre_page)
        
        # 2. Series Page
        series_page = QWidget()
        series_row = QHBoxLayout(series_page)
        series_row.setContentsMargins(0, 0, 0, 0)
        series_row.setSpacing(14)
        
        lbl_series = QLabel("Series name")
        lbl_series.setStyleSheet("font-size: 11pt; font-weight: 600; color: #F8FAFC;")
        lbl_series.setFixedWidth(100)
        
        self.series_input = QLineEdit()
        self.series_input.setPlaceholderText("e.g. breaking bad")
        self.series_input.setFixedHeight(44)
        self.series_input.setStyleSheet("""
            QLineEdit {
                background-color: transparent;
                border: 2px solid rgba(255, 255, 255, 0.05);
                border-radius: 12px;
                padding-left: 13px;
                font-size: 10.5pt;
                color: #F8FAFC;
            }
            QLineEdit:focus { border: 2px solid #3b82f6; }
        """)
        series_row.addWidget(lbl_series)
        series_row.addWidget(self.series_input, 1)
        self.input_stack.addWidget(series_page)
        
        layout.addWidget(self.input_stack)
        layout.addStretch()

        # ── Footer: Action buttons & Is Season checkbox ────────────
        btn_row = QHBoxLayout()
        btn_row.setSpacing(12)

        self.cb_is_season = QCheckBox("Is season")
        self.cb_is_season.setVisible(False)
        self.cb_is_season.setStyleSheet("""
            QCheckBox { font-size: 10.5pt; color: #8B949E; spacing: 8px; }
            QCheckBox::indicator { width: 18px; height: 18px; background-color: transparent; border: 2px solid rgba(255, 255, 255, 0.1); border-radius: 4px; }
            QCheckBox::indicator:checked { background-color: #3b82f6; border: 2px solid #3b82f6; image: url(assets/check_icon.svg); }
        """)
        btn_row.addWidget(self.cb_is_season)
        btn_row.addStretch()

        btn_cancel = QPushButton("Cancel")
        btn_cancel.setFixedHeight(40)
        btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_cancel.setStyleSheet("""
            QPushButton { background-color: transparent; color: #8B949E; border: none; border-radius: 8px; padding: 0 20px; font-weight: 600; font-size: 10.5pt; }
            QPushButton:hover { background-color: rgba(255, 255, 255, 0.05); color: #F8FAFC; }
        """)
        btn_cancel.clicked.connect(self.reject)

        btn_ok = QPushButton("Confirm")
        btn_ok.setFixedHeight(40)
        btn_ok.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_ok.setStyleSheet("""
            QPushButton { background-color: #3b82f6; color: #ffffff; border: none; border-radius: 8px; padding: 0 24px; font-weight: 600; font-size: 10.5pt; }
            QPushButton:hover { background-color: #2563eb; }
        """)
        btn_ok.clicked.connect(self.accept)

        btn_row.addWidget(btn_cancel)
        btn_row.addWidget(btn_ok)
        layout.addLayout(btn_row)

    def _select_type(self, index: int) -> None:
        self._is_movie = (index == 0)
        if self._is_movie:
            self.input_stack.setCurrentIndex(0)
            self.cb_is_season.setVisible(False)
        else:
            self.input_stack.setCurrentIndex(1)
            self.cb_is_season.setVisible(True)

    def get_relative_path(self) -> str:
        if self._is_movie:
            return f"movies/{self.genre_dropdown.currentText()}"
        else:
            name = self.series_input.text().strip().replace(" ", ".")
            return f"tv-series/{name if name else 'unknown_series'}"

    def get_is_season(self) -> bool:
        return self.cb_is_season.isChecked() if not self._is_movie else False
