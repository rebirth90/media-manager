import os
from typing import List
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
    QScrollArea, QLabel, QLineEdit, QGraphicsBlurEffect, QDialog
)

from ui.dialogs import BrowserModalDialog, MediaCategoryDialog
from ui.media_flow import MediaFlowWidget

class SecureServerWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Media Manager - Enterprise Dashboard")
        self.showFullScreen()
        
        # Modern gradient background inspired by mockup
        self.setStyleSheet("""
            QMainWindow { 
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #e8f4f8, stop:0.5 #f0f4f8, stop:1 #e0e8f0);
                font-family: 'Segoe UI', Arial, sans-serif; 
            }
        """)

        self.central_w = QWidget()
        self.main_layout = QVBoxLayout(self.central_w)
        self.main_layout.setContentsMargins(40, 30, 40, 20)
        self.main_layout.setSpacing(20)

        # Top navigation bar - cleaner design
        nav_layout = QHBoxLayout()
        nav_layout.setSpacing(15)
        
        # Add button with icon-like styling
        self.btn_add_torrent = QPushButton("+ Movie / TV-Series")
        self.btn_add_torrent.setFixedHeight(45)
        self.btn_add_torrent.setStyleSheet("""
            QPushButton { 
                background-color: #a8d5e8; 
                color: #1e3a5f; 
                border: none; 
                border-radius: 22px; 
                padding: 0 24px; 
                font-weight: 600; 
                font-size: 11pt;
                box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
            }
            QPushButton:hover { 
                background-color: #8ec5de; 
                color: #0f2847; 
            }
            QPushButton:pressed {
                background-color: #7ab8d4;
            }
        """)
        self.btn_add_torrent.clicked.connect(self._spawn_browser_modal_with_blur)
        
        # Modern search bar
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("🔍 Search")
        self.search_bar.setFixedHeight(45)
        self.search_bar.setMaximumWidth(450)
        self.search_bar.setStyleSheet("""
            QLineEdit { 
                background-color: #ffffff; 
                border: 2px solid #d0e4f0; 
                border-radius: 22px; 
                padding-left: 20px; 
                padding-right: 20px;
                font-size: 10pt; 
                color: #475569;
            }
            QLineEdit:focus {
                border: 2px solid #8ec5de;
            }
        """)
        
        # Bell notification button with modern styling
        self.btn_notif = QPushButton("🔔")
        self.btn_notif.setFixedSize(45, 45)
        self.btn_notif.setStyleSheet("""
            QPushButton { 
                background-color: #ffffff; 
                border: 2px solid #d0e4f0; 
                border-radius: 22px; 
                font-size: 16pt;
            } 
            QPushButton:hover { 
                background-color: #f0f8ff; 
                border-color: #8ec5de;
            }
        """)
        
        nav_layout.addWidget(self.btn_add_torrent)
        nav_layout.addStretch()
        nav_layout.addWidget(self.search_bar)
        nav_layout.addSpacing(10)
        nav_layout.addWidget(self.btn_notif)
        
        self.main_layout.addLayout(nav_layout)

        # Main content container with card-like appearance
        self.canvas_container = QWidget()
        self.canvas_container.setStyleSheet("""
            QWidget { 
                background-color: #ffffff; 
                border-radius: 20px;
                border: 1px solid #e0e8f0;
            }
        """)
        canvas_layout = QVBoxLayout(self.canvas_container)
        canvas_layout.setContentsMargins(25, 25, 25, 25)
        canvas_layout.setSpacing(15)

        # Scrollable content area
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("""
            QScrollArea { 
                border: none; 
                background-color: transparent; 
            }
            QScrollBar:vertical {
                background: #f0f4f8;
                width: 12px;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical {
                background: #c0d0e0;
                border-radius: 6px;
                min-height: 30px;
            }
            QScrollBar::handle:vertical:hover {
                background: #a0b8d0;
            }
        """)
        
        self.scroll_content = QWidget()
        self.scroll_content.setStyleSheet("background-color: transparent;")
        self.flows_layout = QVBoxLayout(self.scroll_content)
        self.flows_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.flows_layout.setSpacing(8)
        
        self.scroll_area.setWidget(self.scroll_content)
        canvas_layout.addWidget(self.scroll_area)
        
        # Modern pagination controls
        pagination_layout = QHBoxLayout()
        pagination_layout.setContentsMargins(10, 15, 10, 0)
        
        self.lbl_page = QLabel("Page 1 of 1 (Total: 0)")
        self.lbl_page.setStyleSheet("""
            font-size: 10pt; 
            color: #334155; 
            font-weight: 600;
        """)
        
        # Center navigation buttons
        center_nav_layout = QHBoxLayout()
        center_nav_layout.setSpacing(10)
        
        self.btn_prev = QPushButton("< Previous")
        self.btn_prev.setFixedSize(110, 38)
        self.btn_prev.setStyleSheet("""
            QPushButton { 
                font-size: 10pt; 
                color: #94a3b8; 
                background-color: transparent; 
                border: 2px solid #e0e8f0; 
                border-radius: 19px;
                font-weight: 600; 
            }
            QPushButton:hover {
                background-color: #f0f4f8;
                color: #64748b;
            }
        """)
        self.btn_prev.clicked.connect(self._prev_page)
        self.btn_prev.setEnabled(False)

        self.btn_next = QPushButton("Next >")
        self.btn_next.setFixedSize(110, 38)
        self.btn_next.setStyleSheet("""
            QPushButton { 
                font-size: 10pt; 
                background-color: #a8d5e8; 
                color: #1e3a5f; 
                border: none;
                border-radius: 19px; 
                font-weight: 600;
            } 
            QPushButton:hover { 
                background-color: #8ec5de; 
                color: #0f2847; 
            }
        """)
        self.btn_next.clicked.connect(self._next_page)
        self.btn_next.setEnabled(False)
        
        center_nav_layout.addWidget(self.btn_prev)
        center_nav_layout.addWidget(self.btn_next)

        self.lbl_items = QLabel("10 items per page")
        self.lbl_items.setStyleSheet("""
            font-size: 10pt; 
            color: #334155; 
            font-weight: 600;
        """)

        pagination_layout.addWidget(self.lbl_page)
        pagination_layout.addStretch()
        pagination_layout.addLayout(center_nav_layout)
        pagination_layout.addStretch()
        pagination_layout.addWidget(self.lbl_items)

        canvas_layout.addLayout(pagination_layout)
        self.main_layout.addWidget(self.canvas_container)
        
        # Subtle exit button
        bottom_layout = QHBoxLayout()
        bottom_layout.addStretch()
        self.btn_exit = QPushButton("Exit Fullscreen")
        self.btn_exit.setFixedSize(150, 30)
        self.btn_exit.setStyleSheet("""
            QPushButton { 
                background-color: transparent; 
                color: #64748b; 
                font-size: 9pt; 
                border: none; 
            } 
            QPushButton:hover { 
                color: #ef4444; 
                text-decoration: underline;
            }
        """)
        self.btn_exit.clicked.connect(self.close)
        bottom_layout.addWidget(self.btn_exit)
        self.main_layout.addLayout(bottom_layout)

        self.setCentralWidget(self.central_w)
        
        self.all_flows: List[MediaFlowWidget] = []
        self.current_page = 0
        self.items_per_page = 10

    def _render_page(self) -> None:
        # Clear current page
        while self.flows_layout.count():
            item = self.flows_layout.takeAt(0)
            widget = item.widget()
            if widget: 
                widget.setParent(None)

        total_items = len(self.all_flows)
        total_pages = 1 if total_items == 0 else (total_items + self.items_per_page - 1) // self.items_per_page

        if self.current_page >= total_pages:
            self.current_page = max(0, total_pages - 1)

        start_idx = self.current_page * self.items_per_page
        end_idx = min(start_idx + self.items_per_page, total_items)

        # Add flows for current page
        for i in range(start_idx, end_idx):
            self.flows_layout.addWidget(self.all_flows[i])

        # Update pagination info
        self.lbl_page.setText(f"Page {self.current_page + 1} of {total_pages} (Total: {total_items})")
        
        # Update button states
        self.btn_prev.setEnabled(self.current_page > 0)
        if self.current_page > 0:
            self.btn_prev.setStyleSheet("""
                QPushButton { 
                    font-size: 10pt; 
                    color: #1e3a5f; 
                    background-color: transparent; 
                    border: 2px solid #a8d5e8; 
                    border-radius: 19px;
                    font-weight: 600; 
                }
                QPushButton:hover {
                    background-color: #e8f4f8;
                    color: #0f2847;
                }
            """)
        else:
            self.btn_prev.setStyleSheet("""
                QPushButton { 
                    font-size: 10pt; 
                    color: #94a3b8; 
                    background-color: transparent; 
                    border: 2px solid #e0e8f0; 
                    border-radius: 19px;
                    font-weight: 600; 
                }
            """)
        
        self.btn_next.setEnabled(self.current_page < total_pages - 1)
        if self.current_page < total_pages - 1:
            self.btn_next.setStyleSheet("""
                QPushButton { 
                    font-size: 10pt; 
                    background-color: #a8d5e8; 
                    color: #1e3a5f; 
                    border: none;
                    border-radius: 19px; 
                    font-weight: 600;
                } 
                QPushButton:hover { 
                    background-color: #8ec5de; 
                    color: #0f2847; 
                }
            """)
        else:
            self.btn_next.setStyleSheet("""
                QPushButton { 
                    font-size: 10pt; 
                    background-color: #e0e8f0; 
                    color: #94a3b8; 
                    border: none;
                    border-radius: 19px; 
                    font-weight: 600;
                }
            """)

    def _next_page(self) -> None:
        self.current_page += 1
        self._render_page()

    def _prev_page(self) -> None:
        self.current_page -= 1
        self._render_page()

    def _spawn_browser_modal_with_blur(self) -> None:
        # Add blur effect to background
        blur_effect = QGraphicsBlurEffect()
        blur_effect.setBlurRadius(20)
        self.canvas_container.setGraphicsEffect(blur_effect)

        dialog = BrowserModalDialog(self)
        dialog.torrent_downloaded.connect(self._process_downloaded_torrent)
        dialog.exec()
        
        # Remove blur
        self.canvas_container.setGraphicsEffect(None)

    def _process_downloaded_torrent(self, file_path: str, img_url: str, title: str) -> None:
        try:
            blur_effect = QGraphicsBlurEffect()
            blur_effect.setBlurRadius(20)
            self.canvas_container.setGraphicsEffect(blur_effect)

            dialog = MediaCategoryDialog(self)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                relative_path = dialog.get_relative_path()
                with open(file_path, "rb") as f:
                    torrent_bytes = f.read()

                index = len(self.all_flows) + 1
                flow = MediaFlowWidget(index, relative_path, torrent_bytes, img_url, title, self.scroll_content)
                self.all_flows.append(flow)
                
                # Jump to last page
                total_items = len(self.all_flows)
                self.current_page = max(0, ((total_items - 1) // self.items_per_page))
                self._render_page()
                
        except Exception as e:
            print(f"Error instantiating pipeline: {e}")
        finally:
            self.canvas_container.setGraphicsEffect(None)
            if os.path.exists(file_path):
                os.remove(file_path)

    def closeEvent(self, event) -> None:
        for flow in self.all_flows:
            flow.close_flow()
        super().closeEvent(event)
