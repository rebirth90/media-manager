import os
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QPushButton
from PyQt6.QtCore import Qt, pyqtSignal

from src.ui.components.animated_toggle import AnimatedToggle
from src.ui.components.search_bar import SearchBarWidget
from src.presentation.utils.ui_helpers import configure_window_control_button

class HeaderNavigationWidget(QWidget):
    add_clicked = pyqtSignal()
    toggle_changed = pyqtSignal(int)
    search_changed = pyqtSignal(str)
    
    minimize_clicked = pyqtSignal()
    maximize_clicked = pyqtSignal()
    close_clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("HeaderContainer")
        self.setFixedHeight(72)
        
        nav_layout = QHBoxLayout(self)
        nav_layout.setContentsMargins(30, 0, 30, 0)
        nav_layout.setSpacing(18)
        
        self.btn_add_torrent = QPushButton("Add item")
        self.btn_add_torrent.setFixedHeight(48)
        self.btn_add_torrent.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_add_torrent.setObjectName("PrimaryButton")
        self.btn_add_torrent.clicked.connect(self.add_clicked.emit)
        
        self.animated_toggle = AnimatedToggle("Movies", "TV Series")
        self.animated_toggle.setFixedHeight(48)
        self.animated_toggle.setMinimumWidth(216)
        self.animated_toggle.toggled.connect(self.toggle_changed.emit)
        
        self.search_bar = SearchBarWidget(self)
        self.search_bar.search_query_changed.connect(self.search_changed.emit)

        window_controls = QHBoxLayout()
        window_controls.setSpacing(8)

        self.btn_minimize = QPushButton()
        self.btn_maximize = QPushButton()
        self.btn_close = QPushButton()

        # Resolve path to assets
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        
        configure_window_control_button(self.btn_minimize, os.path.join(base_dir, "assets", "win_min.svg"))
        configure_window_control_button(self.btn_maximize, os.path.join(base_dir, "assets", "win_restore.svg"))
        configure_window_control_button(self.btn_close, os.path.join(base_dir, "assets", "win_close.svg"), "WindowCloseButton")

        self.btn_minimize.clicked.connect(self.minimize_clicked.emit)
        self.btn_maximize.clicked.connect(self.maximize_clicked.emit)
        self.btn_close.clicked.connect(self.close_clicked.emit)

        window_controls.addWidget(self.btn_minimize)
        window_controls.addWidget(self.btn_maximize)
        window_controls.addWidget(self.btn_close)

        nav_layout.addWidget(self.btn_add_torrent)
        nav_layout.addWidget(self.animated_toggle)
        nav_layout.addStretch(1)
        nav_layout.addWidget(self.search_bar)
        nav_layout.addStretch(1)
        nav_layout.addLayout(window_controls)
        
    def get_search_query(self) -> str:
        return self.search_bar.get_query()
        
    def update_maximize_icon(self, is_maximized: bool):
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        icon_path = os.path.join(base_dir, "assets", "win_restore.svg" if is_maximized else "win_max.svg")
        configure_window_control_button(self.btn_maximize, icon_path)
