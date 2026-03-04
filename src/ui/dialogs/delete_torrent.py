from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog, QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QDialogButtonBox, QCheckBox
)

class DeleteTorrentDialog(QDialog):
    def __init__(self, torrent_name: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Delete 1 torrent")
        self.setFixedSize(450, 210)
        
        self.setStyleSheet("""
            QDialog {
                background-color: #ffffff;
                border-radius: 12px;
            }
            QLabel {
                font-family: 'Segoe UI', Arial;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        # Name label acting like a readonly input
        self.lbl_name = QLabel(torrent_name)
        self.lbl_name.setStyleSheet("""
            background-color: #f8fafc;
            border: 1px solid #e2e8f0;
            border-radius: 6px;
            padding: 8px 12px;
            color: #334155;
            font-size: 10pt;
        """)
        self.lbl_name.setWordWrap(True)
        layout.addWidget(self.lbl_name)

        # Hard drive checkbox logic
        chk_layout = QHBoxLayout()
        chk_layout.setSpacing(10)
        
        lbl_disk = QLabel("💾")
        lbl_disk.setStyleSheet("font-size: 14pt; color: #10b981;")
        
        self.chk_delete_files = QCheckBox("Delete files with torrent")
        self.chk_delete_files.setStyleSheet("""
            QCheckBox {
                font-size: 10pt;
                color: #1e293b;
                font-weight: 600;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
            }
            QCheckBox::indicator:unchecked {
                border: 2px solid #cbd5e1;
                background: #ffffff;
                border-radius: 4px;
            }
            QCheckBox::indicator:checked {
                border: 2px solid #3b82f6;
                background: #60a5fa;
                border-radius: 4px;
            }
        """)
        chk_layout.addWidget(lbl_disk)
        chk_layout.addWidget(self.chk_delete_files)
        chk_layout.addStretch()
        layout.addLayout(chk_layout)

        # Warning
        lbl_warn = QLabel("⚠️ Ticking this checkbox will delete everything contained in those torrents")
        lbl_warn.setStyleSheet("color: #ef4444; font-size: 9pt;")
        lbl_warn.setWordWrap(True)
        layout.addWidget(lbl_warn)

        layout.addStretch()

        # Buttons
        self.button_box = QDialogButtonBox()
        btn_cancel = self.button_box.addButton("CANCEL", QDialogButtonBox.ButtonRole.RejectRole)
        btn_delete = self.button_box.addButton("DELETE", QDialogButtonBox.ButtonRole.AcceptRole)

        btn_cancel.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #64748b;
                border: none;
                font-weight: bold;
                font-size: 10pt;
                padding: 8px 16px;
                border-radius: 6px;
            }
            QPushButton:hover { background-color: #f1f5f9; }
        """)
        
        btn_delete.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #ef4444;
                border: none;
                font-weight: bold;
                font-size: 10pt;
                padding: 8px 16px;
                border-radius: 6px;
            }
            QPushButton:hover { background-color: #fee2e2; }
        """)

        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_layout.addWidget(self.button_box)
        layout.addLayout(btn_layout)

    def should_delete_files(self) -> bool:
        return self.chk_delete_files.isChecked()
