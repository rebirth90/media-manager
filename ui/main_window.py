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
        self.showMaximized()
        
        # Refined gradient background inspired by mockup - softer, more professional
        self.setStyleSheet("""
            QMainWindow { 
                background-color: #ffffff;
                font-family: 'Segoe UI', 'San Francisco', 'Helvetica Neue', Arial, sans-serif; 
            }
        """)

        self.central_w = QWidget()
        self.main_layout = QVBoxLayout(self.central_w)
        self.main_layout.setContentsMargins(50, 35, 50, 25)
        self.main_layout.setSpacing(25)

        # Top navigation bar - mockup-inspired clean design
        nav_layout = QHBoxLayout()
        nav_layout.setSpacing(18)
        
        # Add button with refined styling matching mockup
        self.btn_add_torrent = QPushButton("+ Movie / TV-Series")
        self.btn_add_torrent.setFixedHeight(48)
        self.btn_add_torrent.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_add_torrent.setStyleSheet("""
            QPushButton { 
                background-color: #9dc9e0; 
                color: #0f2847; 
                border: none; 
                border-radius: 24px; 
                padding: 0 28px; 
                font-weight: 600; 
                font-size: 11.5pt;
            }
            QPushButton:hover { 
                background-color: #7db8d5; 
                color: #081a2e; 
            }
            QPushButton:pressed {
                background-color: #6ba8c8;
            }
        """)
        self.btn_add_torrent.clicked.connect(self._spawn_browser_modal_with_blur)
        
        # Refined search bar matching mockup design
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("🔍 Search")
        self.search_bar.setFixedHeight(48)
        self.search_bar.setMaximumWidth(480)
        self.search_bar.setStyleSheet("""
            QLineEdit { 
                background-color: #ffffff; 
                border: 2px solid #c8d8e8; 
                border-radius: 24px; 
                padding-left: 24px; 
                padding-right: 24px;
                font-size: 10.5pt; 
                color: #3d4f60;
            }
            QLineEdit:focus {
                border: 2px solid #7db8d5;
                background-color: #fcfdff;
            }
            QLineEdit::placeholder {
                color: #a0b0c0;
            }
        """)
        
        nav_layout.addWidget(self.btn_add_torrent)
        nav_layout.addStretch()
        nav_layout.addWidget(self.search_bar)
        
        self.main_layout.addLayout(nav_layout)

        # Main content container with enhanced card styling
        self.canvas_container = QWidget()
        self.canvas_container.setStyleSheet("""
            QWidget { 
                background-color: #ffffff; 
                border: none;
            }
        """)
        canvas_layout = QVBoxLayout(self.canvas_container)
        canvas_layout.setContentsMargins(30, 28, 30, 28)
        canvas_layout.setSpacing(18)

        # Scrollable content area with custom scrollbar
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("""
            QScrollArea { 
                border: none; 
                background-color: transparent; 
            }
            QScrollBar:vertical {
                background: #f0f6fa;
                width: 14px;
                border-radius: 7px;
                margin: 2px;
            }
            QScrollBar::handle:vertical {
                background: #b0c8d8;
                border-radius: 7px;
                min-height: 40px;
            }
            QScrollBar::handle:vertical:hover {
                background: #90b0c8;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)
        
        self.scroll_content = QWidget()
        self.scroll_content.setStyleSheet("background-color: transparent;")
        self.flows_layout = QVBoxLayout(self.scroll_content)
        self.flows_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.flows_layout.setSpacing(10)
        
        self.scroll_area.setWidget(self.scroll_content)
        canvas_layout.addWidget(self.scroll_area)
        
        # Enhanced pagination controls matching mockup
        pagination_layout = QHBoxLayout()
        pagination_layout.setContentsMargins(12, 18, 12, 0)
        
        self.lbl_page = QLabel("Page 1 of 1 (Total: 0)")
        self.lbl_page.setStyleSheet("""
            font-size: 10.5pt; 
            color: #2d3e50; 
            font-weight: 600;
            letter-spacing: -0.3px;
        """)
        
        # Center navigation buttons with refined styling
        center_nav_layout = QHBoxLayout()
        center_nav_layout.setSpacing(12)
        
        self.btn_prev = QPushButton("< Previous")
        self.btn_prev.setFixedSize(120, 40)
        self.btn_prev.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_prev.setStyleSheet("""
            QPushButton { 
                font-size: 10pt; 
                color: #88a0b8; 
                background-color: transparent; 
                border: 2px solid #d8e4f0; 
                border-radius: 20px;
                font-weight: 600; 
            }
            QPushButton:hover {
                background-color: #f0f6fa;
                color: #5a7088;
                border-color: #b8cce0;
            }
        """)
        self.btn_prev.clicked.connect(self._prev_page)
        self.btn_prev.setEnabled(False)

        self.btn_next = QPushButton("Next >")
        self.btn_next.setFixedSize(120, 40)
        self.btn_next.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_next.setStyleSheet("""
            QPushButton { 
                font-size: 10pt; 
                background-color: #9dc9e0; 
                color: #0f2847; 
                border: none;
                border-radius: 20px; 
                font-weight: 600;
            } 
            QPushButton:hover { 
                background-color: #7db8d5; 
                color: #081a2e; 
            }
        """)
        self.btn_next.clicked.connect(self._next_page)
        self.btn_next.setEnabled(False)
        
        center_nav_layout.addWidget(self.btn_prev)
        center_nav_layout.addWidget(self.btn_next)

        self.lbl_items = QLabel("10 items per page")
        self.lbl_items.setStyleSheet("""
            font-size: 10.5pt; 
            color: #2d3e50; 
            font-weight: 600;
            letter-spacing: -0.3px;
        """)

        pagination_layout.addWidget(self.lbl_page)
        pagination_layout.addStretch()
        pagination_layout.addLayout(center_nav_layout)
        pagination_layout.addStretch()
        pagination_layout.addWidget(self.lbl_items)

        canvas_layout.addLayout(pagination_layout)
        self.main_layout.addWidget(self.canvas_container)
        
        # Removed exit fullscreen button
        
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
        
        # Update button states with refined styling
        self.btn_prev.setEnabled(self.current_page > 0)
        if self.current_page > 0:
            self.btn_prev.setStyleSheet("""
                QPushButton { 
                    font-size: 10pt; 
                    color: #0f2847; 
                    background-color: transparent; 
                    border: 2px solid #9dc9e0; 
                    border-radius: 20px;
                    font-weight: 600; 
                }
                QPushButton:hover {
                    background-color: #e8f4f8;
                    color: #081a2e;
                    border-color: #7db8d5;
                }
            """)
        else:
            self.btn_prev.setStyleSheet("""
                QPushButton { 
                    font-size: 10pt; 
                    color: #88a0b8; 
                    background-color: transparent; 
                    border: 2px solid #d8e4f0; 
                    border-radius: 20px;
                    font-weight: 600; 
                }
            """)
        
        self.btn_next.setEnabled(self.current_page < total_pages - 1)
        if self.current_page < total_pages - 1:
            self.btn_next.setStyleSheet("""
                QPushButton { 
                    font-size: 10pt; 
                    background-color: #9dc9e0; 
                    color: #0f2847; 
                    border: none;
                    border-radius: 20px; 
                    font-weight: 600;
                } 
                QPushButton:hover { 
                    background-color: #7db8d5; 
                    color: #081a2e; 
                }
            """)
        else:
            self.btn_next.setStyleSheet("""
                QPushButton { 
                    font-size: 10pt; 
                    background-color: #d8e4f0; 
                    color: #88a0b8; 
                    border: none;
                    border-radius: 20px; 
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
        # Enhanced blur effect
        blur_effect = QGraphicsBlurEffect()
        blur_effect.setBlurRadius(25)
        self.canvas_container.setGraphicsEffect(blur_effect)

        dialog = BrowserModalDialog(self)
        dialog.torrent_downloaded.connect(self._process_downloaded_torrent)
        dialog.exec()
        
        # Remove blur
        self.canvas_container.setGraphicsEffect(None)

    def _process_downloaded_torrent(self, file_path: str, img_url: str, title: str) -> None:
        try:
            blur_effect = QGraphicsBlurEffect()
            blur_effect.setBlurRadius(25)
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
