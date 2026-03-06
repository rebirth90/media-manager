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
        from src.ui.components.animated_toggle import AnimatedToggle
        self.animated_toggle = AnimatedToggle("Movie", "TV-Series")
        self.animated_toggle.setFixedHeight(48)
        self.animated_toggle.toggled.connect(self._select_type)
        layout.addWidget(self.animated_toggle)

        # ── Genre dropdown (movie mode) ────────────────────────────
        self.genre_container = QWidget()
        genre_row = QHBoxLayout(self.genre_container)
        genre_row.setContentsMargins(4, 4, 4, 4)
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
                border: 2px solid rgba(255, 255, 255, 0.05);
                border-radius: 12px;
                padding-left: 13px;
                padding-right: 35px;
                font-size: 10.5pt;
                color: #8B949E;
            }}
            QComboBox:focus {{
                border: 2px solid #3b82f6;
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
        series_row.setContentsMargins(4, 4, 4, 4)
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
                border: 2px solid rgba(255, 255, 255, 0.05);
                border-radius: 12px;
                padding-left: 13px;
                font-size: 10.5pt;
                color: #F8FAFC;
            }
            QLineEdit:focus {
                border: 2px solid #3b82f6;
            }
        """)

        series_row.addWidget(lbl_series)
        series_row.addWidget(self.series_input, 1)
        self.series_container.setMaximumHeight(0)
        self.series_container.setVisible(True)
        self.series_container.setStyleSheet("border: none;")
        layout.addWidget(self.series_container)
        
        self.genre_container.setVisible(True)
        self.genre_container.setStyleSheet("border: none;")
        
        # ── Animations Setup ──
        from PyQt6.QtCore import QPropertyAnimation, QEasingCurve, QParallelAnimationGroup
        self._anim_group = QParallelAnimationGroup(self)
        self._genre_anim = QPropertyAnimation(self.genre_container, b"maximumHeight", self)
        self._genre_anim.setDuration(220)
        self._genre_anim.setEasingCurve(QEasingCurve.Type.InOutQuad)
        
        self._series_anim = QPropertyAnimation(self.series_container, b"maximumHeight", self)
        self._series_anim.setDuration(220)
        self._series_anim.setEasingCurve(QEasingCurve.Type.InOutQuad)
        
        self._anim_group.addAnimation(self._genre_anim)
        self._anim_group.addAnimation(self._series_anim)

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

    def _select_type(self, index: int) -> None:
        self._is_movie = (index == 0)
        
        self._anim_group.stop()

        # Unlock and measure dynamically
        self.genre_container.setMaximumHeight(16777215)
        g_target = self.genre_container.sizeHint().height()
        
        self.series_container.setMaximumHeight(16777215)
        s_target = self.series_container.sizeHint().height()

        if self._is_movie:
            self._genre_anim.setStartValue(self.genre_container.height())
            self._genre_anim.setEndValue(max(g_target, 44))
            
            self._series_anim.setStartValue(self.series_container.height())
            self._series_anim.setEndValue(0)
        else:
            self._genre_anim.setStartValue(self.genre_container.height())
            self._genre_anim.setEndValue(0)
            
            self._series_anim.setStartValue(self.series_container.height())
            self._series_anim.setEndValue(max(s_target, 44))
            
        def reset_max_heights():
            if self._is_movie:
                self.genre_container.setMaximumHeight(16777215)
            else:
                self.series_container.setMaximumHeight(16777215)

        try: self._anim_group.finished.disconnect()
        except TypeError: pass
        self._anim_group.finished.connect(reset_max_heights)

        self._anim_group.start()

    def get_relative_path(self) -> str:
        if self._is_movie:
            return f"movies/{self.genre_dropdown.currentText()}"
        else:
            name = self.series_input.text().strip().replace(" ", ".")
            return f"tv-series/{name if name else 'unknown_series'}"
