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
        self.setWindowTitle("Secure Enterprise Dashboard")
        self.showFullScreen()
        
        self.setStyleSheet("""
            QMainWindow { background-color: #eaf2f8; font-family: 'Segoe UI', Arial, sans-serif; }
        """)

        self.central_w = QWidget()
        self.main_layout = QVBoxLayout(self.central_w)
        self.main_layout.setContentsMargins(50, 40, 50, 20)
        self.main_layout.setSpacing(15)

        nav_layout = QHBoxLayout()
        
        self.btn_add_torrent = QPushButton("+ Movie / TV-Series")
        self.btn_add_torrent.setFixedHeight(40)
        self.btn_add_torrent.setStyleSheet("""
            QPushButton { background-color: #93c5fd; color: #1e3a8a; border: none; border-radius: 20px; padding: 0 20px; font-weight: bold; font-size: 11pt; }
            QPushButton:hover { background-color: #60a5fa; color: white; }
        """)
        self.btn_add_torrent.clicked.connect(self._spawn_browser_modal_with_blur)
        
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("🔍 Search")
        self.search_bar.setFixedHeight(40)
        self.search_bar.setMaximumWidth(400)
        self.search_bar.setStyleSheet("""
            QLineEdit { background-color: #ffffff; border: 1px solid #bfdbfe; border-radius: 20px; padding-left: 15px; font-size: 10pt; color: #475569; }
        """)
        
        self.btn_notif = QPushButton("🔔")
        self.btn_notif.setFixedSize(40, 40)
        self.btn_notif.setStyleSheet("QPushButton { background-color: transparent; border-radius: 20px; font-size: 14pt; } QPushButton:hover { background-color: #dbeafe; }")
        
        nav_layout.addWidget(self.btn_add_torrent)
        nav_layout.addStretch()
        nav_layout.addWidget(self.search_bar)
        nav_layout.addSpacing(10)
        nav_layout.addWidget(self.btn_notif)
        
        self.main_layout.addLayout(nav_layout)

        self.canvas_container = QWidget()
        self.canvas_container.setStyleSheet("QWidget { background-color: #ffffff; border-radius: 15px; }")
        canvas_layout = QVBoxLayout(self.canvas_container)
        canvas_layout.setContentsMargins(20, 20, 20, 20)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("QScrollArea { border: none; background-color: transparent; }")
        
        self.scroll_content = QWidget()
        self.scroll_content.setStyleSheet("background-color: transparent;")
        self.flows_layout = QVBoxLayout(self.scroll_content)
        self.flows_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.flows_layout.setSpacing(0)
        
        self.scroll_area.setWidget(self.scroll_content)
        canvas_layout.addWidget(self.scroll_area)
        
        pagination_layout = QHBoxLayout()
        pagination_layout.setContentsMargins(10, 10, 10, 0)
        
        self.lbl_page = QLabel("Page 1 of 1 (Total: 0)")
        self.lbl_page.setStyleSheet("font-size: 10pt; color: #1e293b; font-weight: bold;")
        
        center_nav_layout = QHBoxLayout()
        self.btn_prev = QPushButton("< Previous")
        self.btn_prev.setFixedSize(100, 35)
        self.btn_prev.setStyleSheet("QPushButton { font-size: 10pt; color: #94a3b8; background-color: transparent; border: none; font-weight: bold; }")
        self.btn_prev.clicked.connect(self._prev_page)
        self.btn_prev.setEnabled(False)

        self.btn_next = QPushButton("Next >")
        self.btn_next.setFixedSize(100, 35)
        self.btn_next.setStyleSheet("QPushButton { font-size: 10pt; background-color: #93c5fd; color: #1e3a8a; border-radius: 17px; font-weight: bold; } QPushButton:hover { background-color: #60a5fa; color: white; }")
        self.btn_next.clicked.connect(self._next_page)
        self.btn_next.setEnabled(False)
        center_nav_layout.addWidget(self.btn_prev)
        center_nav_layout.addWidget(self.btn_next)

        self.lbl_items = QLabel("10 items per page")
        self.lbl_items.setStyleSheet("font-size: 10pt; color: #1e293b; font-weight: bold;")

        pagination_layout.addWidget(self.lbl_page)
        pagination_layout.addStretch()
        pagination_layout.addLayout(center_nav_layout)
        pagination_layout.addStretch()
        pagination_layout.addWidget(self.lbl_items)

        canvas_layout.addLayout(pagination_layout)
        self.main_layout.addWidget(self.canvas_container)
        
        bottom_layout = QHBoxLayout()
        bottom_layout.addStretch()
        self.btn_exit = QPushButton("Exit Fullscreen")
        self.btn_exit.setFixedSize(150, 30)
        self.btn_exit.setStyleSheet("QPushButton { background-color: transparent; color: #64748b; font-size: 9pt; border: none; } QPushButton:hover { color: #ef4444; }")
        self.btn_exit.clicked.connect(self.close)
        bottom_layout.addWidget(self.btn_exit)
        self.main_layout.addLayout(bottom_layout)

        self.setCentralWidget(self.central_w)
        
        self.all_flows: List[MediaFlowWidget] = []
        self.current_page = 0
        self.items_per_page = 10

    def _render_page(self) -> None:
        while self.flows_layout.count():
            item = self.flows_layout.takeAt(0)
            widget = item.widget()
            if widget: widget.setParent(None)

        total_items = len(self.all_flows)
        total_pages = 1 if total_items == 0 else (total_items + self.items_per_page - 1) // self.items_per_page

        if self.current_page >= total_pages:
            self.current_page = max(0, total_pages - 1)

        start_idx = self.current_page * self.items_per_page
        end_idx = min(start_idx + self.items_per_page, total_items)

        for i in range(start_idx, end_idx):
            self.flows_layout.addWidget(self.all_flows[i])

        self.lbl_page.setText(f"Page {self.current_page + 1} of {total_pages} (Total: {total_items})")
        
        self.btn_prev.setEnabled(self.current_page > 0)
        self.btn_prev.setStyleSheet("QPushButton { font-size: 10pt; color: #1e3a8a; background-color: transparent; border: none; font-weight: bold; QPushButton:hover { color: #3b82f6; } }" if self.current_page > 0 else "QPushButton { font-size: 10pt; color: #94a3b8; background-color: transparent; border: none; font-weight: bold; }")
        
        self.btn_next.setEnabled(self.current_page < total_pages - 1)
        self.btn_next.setStyleSheet("QPushButton { font-size: 10pt; background-color: #93c5fd; color: #1e3a8a; border-radius: 17px; font-weight: bold; } QPushButton:hover { background-color: #60a5fa; color: white; }" if self.current_page < total_pages - 1 else "QPushButton { font-size: 10pt; background-color: #e2e8f0; color: #94a3b8; border-radius: 17px; font-weight: bold; }")

    def _next_page(self) -> None:
        self.current_page += 1
        self._render_page()

    def _prev_page(self) -> None:
        self.current_page -= 1
        self._render_page()

    def _spawn_browser_modal_with_blur(self) -> None:
        blur_effect = QGraphicsBlurEffect()
        blur_effect.setBlurRadius(15)
        self.canvas_container.setGraphicsEffect(blur_effect)

        dialog = BrowserModalDialog(self)
        dialog.torrent_downloaded.connect(self._process_downloaded_torrent)
        dialog.exec()
        
        self.canvas_container.setGraphicsEffect(None)

    def _process_downloaded_torrent(self, file_path: str, img_url: str, title: str) -> None:
        try:
            blur_effect = QGraphicsBlurEffect()
            blur_effect.setBlurRadius(15)
            self.canvas_container.setGraphicsEffect(blur_effect)

            dialog = MediaCategoryDialog(self)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                relative_path = dialog.get_relative_path()
                with open(file_path, "rb") as f:
                    torrent_bytes = f.read()

                index = len(self.all_flows) + 1
                flow = MediaFlowWidget(index, relative_path, torrent_bytes, img_url, title, self.scroll_content)
                self.all_flows.append(flow)
                
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
