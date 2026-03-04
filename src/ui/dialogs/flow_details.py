import os
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (
    QDialog, QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QTextEdit
)

class FlowDetailsModal(QDialog):
    def __init__(
        self, 
        title: str, 
        qbit_state: str, 
        ffmpeg_log: str, 
        illustration_path: str, 
        parent=None
    ):
        super().__init__(parent)
        self.setWindowTitle(f"Pipeline Details: {title}")
        
        # Modern card-based styling matching mockup
        self.setStyleSheet("""
            QDialog { 
                background-color: #f8fafc; 
                border-radius: 16px;
            }
            QLabel { 
                color: #1e293b; 
                font-family: 'Segoe UI', Arial; 
            }
            QTextEdit { 
                background-color: #ffffff; 
                color: #334155; 
                border: 2px solid #e0e8f0; 
                border-radius: 10px; 
                font-family: 'Consolas', 'Courier New', monospace; 
                font-size: 9pt;
                padding: 10px;
            }
        """)
        self.setFixedSize(650, 420)

        main_layout = QHBoxLayout(self)
        main_layout.setSpacing(25)
        main_layout.setContentsMargins(25, 25, 25, 25)

        # Left side: Workflow status with illustration
        left_layout = QVBoxLayout()
        left_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
        left_layout.setSpacing(15)
        
        title_lbl = QLabel("Workflow Status")
        title_lbl.setStyleSheet("""
            font-size: 14pt; 
            font-weight: bold; 
            color: #0f172a;
        """)
        
        # Illustration image
        img_lbl = QLabel()
        if os.path.exists(illustration_path):
            pixmap = QPixmap(illustration_path)
            scaled_pixmap = pixmap.scaled(
                220, 220, 
                Qt.AspectRatioMode.KeepAspectRatio, 
                Qt.TransformationMode.SmoothTransformation
            )
            img_lbl.setPixmap(scaled_pixmap)
        else:
            img_lbl.setText("📊\nWorkflow\nVisualization")
            img_lbl.setStyleSheet("""
                color: #94a3b8;
                font-size: 10pt;
                background-color: #f1f5f9;
                border: 2px dashed #cbd5e1;
                border-radius: 12px;
                padding: 40px;
            """)
            img_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Modify button with modern styling
        btn_modify = QPushButton("✎ Modify (Complete)")
        btn_modify.setFixedHeight(40)
        btn_modify.setStyleSheet("""
            QPushButton {
                background-color: #60a5fa;
                color: #ffffff;
                border: none;
                border-radius: 12px;
                padding: 10px 20px;
                font-weight: 600;
                font-size: 10pt;
            }
            QPushButton:hover {
                background-color: #3b82f6;
            }
            QPushButton:pressed {
                background-color: #2563eb;
            }
        """)
        
        # Add link button
        btn_link = QPushButton("🔗 VIEW & SHARE LINK")
        btn_link.setFixedHeight(40)
        btn_link.setStyleSheet("""
            QPushButton {
                background-color: #f1f5f9;
                color: #475569;
                border: 2px solid #cbd5e1;
                border-radius: 12px;
                padding: 10px 20px;
                font-weight: 600;
                font-size: 9pt;
            }
            QPushButton:hover {
                background-color: #e2e8f0;
                border-color: #94a3b8;
            }
        """)
        
        left_layout.addWidget(title_lbl)
        left_layout.addWidget(img_lbl)
        left_layout.addStretch()
        left_layout.addWidget(btn_modify)
        left_layout.addWidget(btn_link)

        # Right side: Content details
        right_layout = QVBoxLayout()
        right_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        right_layout.setSpacing(12)
        
        # Header
        det_lbl = QLabel("CONTENT DETAILS")
        det_lbl.setStyleSheet("""
            font-size: 9pt; 
            font-weight: bold; 
            color: #64748b;
            letter-spacing: 1px;
        """)
        
        # Project info card
        project_card = QWidget()
        project_card.setStyleSheet("""
            QWidget {
                background-color: #ffffff;
                border-radius: 12px;
                border: 1px solid #e0e8f0;
                padding: 12px;
            }
        """)
        project_layout = QVBoxLayout(project_card)
        project_layout.setSpacing(8)
        
        # Title
        lbl_title_header = QLabel("Active Target:")
        lbl_title_header.setStyleSheet("font-size: 9pt; color: #64748b; font-weight: 600;")
        lbl_title_val = QLabel(f"[{title}]")
        lbl_title_val.setStyleSheet("""
            background-color: #eff6ff; 
            color: #1e40af;
            border-radius: 6px; 
            padding: 6px 10px;
            font-weight: 600;
        """)
        lbl_title_val.setWordWrap(True)
        
        # Downloader status
        lbl_qbit_header = QLabel("Downloader Tracker:")
        lbl_qbit_header.setStyleSheet("font-size: 9pt; color: #64748b; font-weight: 600;")
        lbl_qbit_val = QLabel(f"[{qbit_state}]")
        lbl_qbit_val.setStyleSheet("""
            background-color: #f0fdf4; 
            color: #166534;
            border-radius: 6px; 
            padding: 6px 10px;
            font-weight: 600;
        """)
        lbl_qbit_val.setWordWrap(True)
        
        project_layout.addWidget(lbl_title_header)
        project_layout.addWidget(lbl_title_val)
        project_layout.addWidget(lbl_qbit_header)
        project_layout.addWidget(lbl_qbit_val)
        
        # FFmpeg log section
        lbl_log_header = QLabel("Recent Telemetry (FFmpeg):")
        lbl_log_header.setStyleSheet("""
            font-size: 9pt; 
            color: #64748b; 
            font-weight: 600;
            margin-top: 8px;
        """)
        
        txt_log = QTextEdit(ffmpeg_log)
        txt_log.setReadOnly(True)
        txt_log.setMinimumHeight(120)

        right_layout.addWidget(det_lbl)
        right_layout.addWidget(project_card)
        right_layout.addWidget(lbl_log_header)
        right_layout.addWidget(txt_log, stretch=1)

        main_layout.addLayout(left_layout, stretch=1)
        main_layout.addLayout(right_layout, stretch=2)
