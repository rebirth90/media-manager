GLOBAL_STYLESHEET = """
QMainWindow { 
    background-color: #0A0B0E;
    font-family: 'Segoe UI', 'San Francisco', 'Helvetica Neue', Arial, sans-serif; 
}

/* Base Types */
QLabel { 
    font-family: 'Segoe UI', 'San Francisco', 'Helvetica Neue', Arial, sans-serif; 
}

/* Containers */
QWidget#HeaderContainer {
    background-color: #0F1115;
    border-bottom: 1px solid rgba(255, 255, 255, 0.05);
}

QWidget#CanvasContainer {
    background-color: #0A0B0E;
}

QFrame#MediaCardWrapper { 
    background-color: #1A1D24; 
    border: 1px solid rgba(255, 255, 255, 0.05); 
    border-radius: 12px;
}

QWidget#TopRow { 
    background: transparent; 
    border: none; 
}

QWidget#FoldoutCard { 
    background: transparent; 
    border: none; 
}

/* Buttons */
QPushButton#PrimaryButton { 
    background-color: #3b82f6; 
    color: #ffffff; 
    border: none; 
    border-radius: 12px; 
    padding: 0 28px; 
    font-weight: 600; 
    font-size: 11.5pt;
}
QPushButton#PrimaryButton:hover { 
    background-color: #2563eb; 
}
QPushButton#PrimaryButton:pressed {
    background-color: #1d4ed8;
}

QPushButton#WindowControlButton {
    background-color: transparent;
    border: none;
    border-radius: 8px;
}
QPushButton#WindowControlButton:hover {
    background-color: rgba(255, 255, 255, 0.05);
}

QPushButton#WindowCloseButton {
    background-color: transparent;
    border: none;
    border-radius: 8px;
}
QPushButton#WindowCloseButton:hover {
    background-color: rgba(239, 68, 68, 0.2);
}

QPushButton#ActionIconButton { 
    background-color: transparent; 
    border: none; 
    border-radius: 8px; 
}
QPushButton#ActionIconButton:hover { 
    background-color: rgba(255, 255, 255, 0.05); 
}

QPushButton#DangerIconButton { 
    background-color: transparent; 
    border: none; 
    border-radius: 8px; 
}
QPushButton#DangerIconButton:hover { 
    background-color: rgba(239, 68, 68, 0.1); 
}

/* Scroll Area */
QScrollArea { 
    border: none; 
    background-color: transparent; 
}
QScrollBar:vertical {
    background: #0F1115;
    width: 14px;
    border-radius: 7px;
    margin: 2px;
}
QScrollBar::handle:vertical {
    background: #374151;
    border-radius: 7px;
    min-height: 40px;
}
QScrollBar::handle:vertical:hover {
    background: #4b5563;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

/* Card Header Labels */
QLabel#TitleText {
    font-size: 13pt; 
    font-weight: bold; 
    color: #F8FAFC;
}

QLabel#SubText {
    font-size: 9pt; 
    color: #9ca3af;
}

QLabel#DescText {
    font-size: 9pt; 
    color: #94A3B8;
}

/* Card Column Headers */
QLabel#PillHeader {
    color: #6b7280; 
    font-size: 8pt; 
    font-weight: 500;
}

QLabel#SizeText {
    color: #ffffff; 
    font-weight: 500; 
    font-size: 10pt;
}

QLabel#PosterImage {
    background-color: #0A0B0E; 
    border-radius: 6px; 
    border: 1px solid rgba(255, 255, 255, 0.05);
}

/* State Value Labels (Pills) */
QLabel.PillUnknown {
    background-color: rgba(107,114,128,0.1); 
    color: #9ca3af; 
    border: 1px solid rgba(107,114,128,0.3); 
    border-radius: 6px; 
    padding: 4px 10px; 
    font-weight: 600; 
    font-size: 11px;
}
QLabel.PillSuccess {
    background-color: rgba(34,197,94,0.1); 
    color: #4ade80; 
    border: 1px solid rgba(34,197,94,0.3); 
    border-radius: 6px; 
    padding: 4px 10px; 
    font-weight: 600; 
    font-size: 11px;
}
QLabel.PillActive {
    background-color: rgba(59,130,246,0.1); 
    color: #60a5fa; 
    border: 1px solid rgba(59,130,246,0.3); 
    border-radius: 6px; 
    padding: 4px 10px; 
    font-weight: 600; 
    font-size: 11px;
}
QLabel.PillWarning {
    background-color: rgba(168,85,247,0.1); 
    color: #c084fc; 
    border: 1px solid rgba(168,85,247,0.3); 
    border-radius: 6px; 
    padding: 4px 10px; 
    font-weight: 600; 
    font-size: 11px;
}
QLabel.PillDanger {
    background-color: rgba(239, 68, 68, 0.1); 
    color: #f87171; 
    border: 1px solid rgba(239, 68, 68, 0.3); 
    border-radius: 6px; 
    padding: 4px 10px; 
    font-weight: 600; 
    font-size: 11px;
}

/* Progress Bars */
QProgressBar.PbSuccess { 
    background-color: rgba(34,197,94,0.1); 
    color: #4ade80; 
    border: 1px solid rgba(34,197,94,0.3); 
    border-radius: 6px; 
    text-align: center; 
    font-weight: 600; 
    font-size: 11px; 
}
QProgressBar.PbSuccess::chunk { background-color: transparent; }

QProgressBar.PbActive { 
    background-color: rgba(59,130,246,0.1); 
    color: #60a5fa; 
    border: 1px solid rgba(59,130,246,0.3); 
    border-radius: 6px; 
    text-align: center; 
    font-weight: 600; 
    font-size: 11px; 
}
QProgressBar.PbActive::chunk { background-color: transparent; }

QProgressBar.PbUnknown { 
    background-color: rgba(107,114,128,0.1); 
    color: #9ca3af; 
    border: 1px solid rgba(107,114,128,0.3); 
    border-radius: 6px; 
    text-align: center; 
    font-weight: 600; 
    font-size: 11px; 
}
QProgressBar.PbUnknown::chunk { background-color: transparent; }

QProgressBar.PbWarning { 
    background-color: rgba(168,85,247,0.1); 
    color: #c084fc; 
    border: 1px solid rgba(168,85,247,0.3); 
    border-radius: 6px; 
    text-align: center; 
    font-weight: 600; 
    font-size: 11px; 
}
QProgressBar.PbWarning::chunk { background-color: transparent; }
"""
