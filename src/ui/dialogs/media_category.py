from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog, QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QComboBox, QLineEdit
)

class MediaCategoryDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Construct path")
        self.setFixedSize(500, 310)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._is_movie = True

        root = QWidget(self)
        root.setGeometry(0, 0, 500, 310)
        root.setObjectName("card")
        root.setStyleSheet("""
            QWidget#card {
                background-color: #ffffff;
                border-radius: 22px;
                border: 1px solid #dde6ee;
            }
        """)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(root)

        layout = QVBoxLayout(root)
        layout.setSpacing(20)
        layout.setContentsMargins(32, 28, 32, 28)

        lbl_title = QLabel("Construct path")
        lbl_title.setStyleSheet(
            "font-size: 16pt; font-weight: 800; color: #0d1f35; letter-spacing: -0.5px;"
        )
        layout.addWidget(lbl_title)

        # Segmented pill control (grey track with blue fill for active)
        seg_track = QWidget()
        seg_track.setFixedHeight(52)
        seg_track.setStyleSheet("QWidget { background-color: #ebebed; border-radius: 26px; }")
        seg_layout = QHBoxLayout(seg_track)
        seg_layout.setContentsMargins(5, 5, 5, 5)
        seg_layout.setSpacing(4)

        self._ss_active = (
            "QPushButton { background-color: #2878e8; color: #ffffff; border: none;"
            " border-radius: 21px; font-weight: 700; font-size: 11pt; padding: 0 10px; }"
        )
        self._ss_inactive = (
            "QPushButton { background-color: transparent; color: #8a9aaa; border: none;"
            " border-radius: 21px; font-weight: 600; font-size: 11pt; padding: 0 10px; }"
        )

        self.btn_movie = QPushButton("🎬  Movie")
        self.btn_tv    = QPushButton("📺  TV-Series")
        for _b in (self.btn_movie, self.btn_tv):
            _b.setCursor(Qt.CursorShape.PointingHandCursor)
            _b.setFixedHeight(42)

        self.btn_movie.setStyleSheet(self._ss_active)
        self.btn_tv.setStyleSheet(self._ss_inactive)
        self.btn_movie.clicked.connect(lambda: self._select_type(True))
        self.btn_tv.clicked.connect(lambda: self._select_type(False))

        seg_layout.addWidget(self.btn_movie, 1)
        seg_layout.addWidget(self.btn_tv, 1)
        layout.addWidget(seg_track)

        _div = QWidget()
        _div.setFixedHeight(1)
        _div.setStyleSheet("background-color: #eaeff4;")
        layout.addWidget(_div)

        # ── Genre dropdown (movie mode) ────────────────────────────
        self.genre_container = QWidget()
        genre_row = QHBoxLayout(self.genre_container)
        genre_row.setContentsMargins(0, 0, 0, 0)
        genre_row.setSpacing(14)

        lbl_genre = QLabel("Genre")
        lbl_genre.setStyleSheet("""
            font-size: 10pt; font-weight: 600; color: #4a6070;
        """)
        lbl_genre.setFixedWidth(72)

        self.genre_dropdown = QComboBox()
        self.genre_dropdown.addItems([
            "action", "adventure", "anime", "comedy",
            "crime", "drama", "horror", "sf", "thriller"
        ])
        self.genre_dropdown.setFixedHeight(42)
        self.genre_dropdown.setStyleSheet("""
            QComboBox {
                background-color: #f4f8fb;
                border: 1.5px solid #c8d8e8;
                border-radius: 12px;
                padding-left: 14px;
                padding-right: 36px;
                font-size: 10pt;
                color: #1e293b;
            }
            QComboBox:focus {
                border-color: #7db8d5;
                background-color: #ffffff;
            }
            QComboBox::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: right center;
                width: 32px;
                border-left: 1px solid #dde8f0;
                border-top-right-radius: 12px;
                border-bottom-right-radius: 12px;
                background: transparent;
            }
            QComboBox::down-arrow {
                image: none;
                width: 0px;
                height: 0px;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 6px solid #5a7a8a;
                margin-top: 2px;
            }
            QComboBox QAbstractItemView {
                background-color: #ffffff;
                border: 1.5px solid #c8d8e8;
                border-radius: 10px;
                selection-background-color: #e8f4fb;
                selection-color: #0f2847;
                padding: 4px;
                outline: 0;
            }
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
        lbl_series.setStyleSheet("""
            font-size: 10pt; font-weight: 600; color: #4a6070;
        """)
        lbl_series.setFixedWidth(72)

        self.series_input = QLineEdit()
        self.series_input.setPlaceholderText("e.g. breaking bad")
        self.series_input.setFixedHeight(42)
        self.series_input.setStyleSheet("""
            QLineEdit {
                background-color: #f4f8fb;
                border: 1.5px solid #c8d8e8;
                border-radius: 12px;
                padding-left: 14px;
                font-size: 10pt;
                color: #1e293b;
            }
            QLineEdit:focus {
                border-color: #7db8d5;
                background-color: #ffffff;
            }
        """)

        series_row.addWidget(lbl_series)
        series_row.addWidget(self.series_input, 1)
        self.series_container.hide()
        layout.addWidget(self.series_container)

        layout.addStretch()

        # ── Action buttons ─────────────────────────────────────────
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)
        btn_row.addStretch()

        btn_cancel = QPushButton("Cancel")
        btn_cancel.setFixedHeight(40)
        btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_cancel.setStyleSheet("""
            QPushButton {
                background-color: #f0f6fa;
                color: #5a7a8a;
                border: 1.5px solid #c8d8e8;
                border-radius: 12px;
                padding: 0 22px;
                font-weight: 600;
                font-size: 10pt;
            }
            QPushButton:hover {
                background-color: #e0edf5;
            }
        """)
        btn_cancel.clicked.connect(self.reject)

        btn_ok = QPushButton("Confirm")
        btn_ok.setFixedHeight(40)
        btn_ok.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_ok.setStyleSheet("""
            QPushButton {
                background-color: #9dc9e0;
                color: #0f2847;
                border: none;
                border-radius: 12px;
                padding: 0 26px;
                font-weight: 700;
                font-size: 10pt;
            }
            QPushButton:hover {
                background-color: #7db8d5;
            }
            QPushButton:pressed {
                background-color: #6ba8c8;
            }
        """)
        btn_ok.clicked.connect(self.accept)

        btn_row.addWidget(btn_cancel)
        btn_row.addWidget(btn_ok)
        layout.addLayout(btn_row)

    def _select_type(self, is_movie: bool) -> None:
        self._is_movie = is_movie
        self.btn_movie.setStyleSheet(self._ss_active   if is_movie else self._ss_inactive)
        self.btn_tv.setStyleSheet(   self._ss_inactive if is_movie else self._ss_active)
        self.genre_container.setVisible(is_movie)
        self.series_container.setVisible(not is_movie)

    def get_relative_path(self) -> str:
        if self._is_movie:
            return f"movies/{self.genre_dropdown.currentText()}"
        else:
            name = self.series_input.text().strip().replace(" ", ".")
            return f"tv-series/{name if name else 'unknown_series'}"
