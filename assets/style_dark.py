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
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #13151A, stop:1 #1A1C23); 
    border: 1px solid rgba(255, 255, 255, 0.05); 
    border-radius: 12px;
}
QFrame#MediaCardWrapper:hover {
    border: 1px solid rgba(255, 255, 255, 0.1); 
}



QWidget#FoldoutCard { 
    background-color: rgba(15, 17, 21, 0.5); /* #0F1115 at 50% opacity */
    border-top: 1px solid rgba(255, 255, 255, 0.05); 
}

/* Toggle Container */
QWidget#ToggleContainer {
    background-color: rgba(255, 255, 255, 0.05);
    border-radius: 12px;
}

QPushButton#ToggleButton {
    background-color: transparent;
    color: #8B949E;
    border: none;
    border-radius: 8px;
    font-weight: 600;
    font-size: 10.5pt;
}

QPushButton#ToggleButton:hover {
    color: #F8FAFC;
    background-color: rgba(255, 255, 255, 0.05);
}

QPushButton#ToggleButton:checked {
    background-color: #3b82f6; 
    color: #ffffff;
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
    color: #8B949E; /* Adding subtle color to the icons if they were text, but they are SVGs. Backgrounds for hover state: */
}
QPushButton#WindowControlButton:hover {
    background-color: rgba(255, 255, 255, 0.08);
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
    background-color: rgba(59, 130, 246, 0.08); 
    border: 1px solid rgba(59, 130, 246, 0.2); 
    border-radius: 8px; 
}
QPushButton#DangerIconButton:hover { 
    background-color: rgba(59, 130, 246, 0.15); 
    border: 1px solid rgba(59, 130, 246, 0.4); 
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
    color: #9CA3AF;
}

QLabel#DescText {
    font-size: 9pt; 
    color: #8B949E; /* Muted slate for description as seen in the mockup */
}

/* Card Column Headers */
QLabel#PillHeader {
    color: #6B7280; 
    font-size: 8pt; 
    font-weight: 500;
}

QLabel#SizeText {
    color: #F8FAFC; 
    font-weight: 600; 
    font-size: 10pt;
}

QLabel#PosterImage {
    background-color: #0A0B0E; 
    border-radius: 6px; 
    border: 1px solid rgba(255, 255, 255, 0.05);
}

/* State Value Labels (Pills) */
/* ── Pill labels (VueTorrent-aligned colour semantics) ── */
QLabel.PillDownloading {
    background-color: rgba(0, 123, 255, 0.15);
    color: #66b2ff;
    border: 1px solid rgba(0, 123, 255, 0.35);
    border-radius: 6px; padding: 0px 10px;
    font-weight: 600; font-size: 11px;
}
QLabel.PillSuccess {
    background-color: rgba(40, 167, 69, 0.15);
    color: #4ADE80;
    border: 1px solid rgba(40, 167, 69, 0.35);
    border-radius: 6px; padding: 0px 10px;
    font-weight: 600; font-size: 11px;
}
QLabel.PillPaused {
    background-color: rgba(255, 193, 7, 0.15);
    color: #ffd966;
    border: 1px solid rgba(255, 193, 7, 0.35);
    border-radius: 6px; padding: 0px 10px;
    font-weight: 600; font-size: 11px;
}
QLabel.PillChecking {
    background-color: rgba(23, 162, 184, 0.15);
    color: #5fd4e4;
    border: 1px solid rgba(23, 162, 184, 0.35);
    border-radius: 6px; padding: 0px 10px;
    font-weight: 600; font-size: 11px;
}
QLabel.PillQueued {
    background-color: rgba(108, 117, 125, 0.15);
    color: #9CA3AF;
    border: 1px solid rgba(108, 117, 125, 0.35);
    border-radius: 6px; padding: 0px 10px;
    font-weight: 600; font-size: 11px;
}
QLabel.PillDanger {
    background-color: rgba(220, 53, 69, 0.15);
    color: #F87171;
    border: 1px solid rgba(220, 53, 69, 0.35);
    border-radius: 6px; padding: 0px 10px;
    font-weight: 600; font-size: 11px;
}
QLabel.PillUnknown {
    background-color: rgba(108, 117, 125, 0.1);
    color: #9CA3AF;
    border: 1px solid rgba(108, 117, 125, 0.3);
    border-radius: 6px; padding: 0px 10px;
    font-weight: 600; font-size: 11px;
}
/* Legacy aliases kept for conversion status */
QLabel.PillActive {
    background-color: rgba(0, 123, 255, 0.15);
    color: #66b2ff;
    border: 1px solid rgba(0, 123, 255, 0.35);
    border-radius: 6px; padding: 0px 10px;
    font-weight: 600; font-size: 11px;
}
QLabel.PillWarning {
    background-color: rgba(255, 193, 7, 0.15);
    color: #ffd966;
    border: 1px solid rgba(255, 193, 7, 0.35);
    border-radius: 6px; padding: 0px 10px;
    font-weight: 600; font-size: 11px;
}

/* Progress Bars */
QProgressBar.PbSuccess { 
    background-color: rgba(34,197,94,0.1); 
    color: #4ADE80; 
    border: 1px solid rgba(34,197,94,0.3); 
    border-radius: 6px; 
    text-align: center; 
    font-weight: 600; 
    font-size: 11px; 
}
QProgressBar.PbSuccess::chunk { background-color: transparent; }

QProgressBar.PbActive { 
    background-color: rgba(59,130,246,0.1); 
    color: #60A5FA; 
    border: 1px solid rgba(59,130,246,0.3); 
    border-radius: 6px; 
    text-align: center; 
    font-weight: 600; 
    font-size: 11px; 
}
QProgressBar.PbActive::chunk { background-color: transparent; }

QProgressBar.PbUnknown { 
    background-color: rgba(107,114,128,0.1); 
    color: #9CA3AF; 
    border: 1px solid rgba(107,114,128,0.3); 
    border-radius: 6px; 
    text-align: center; 
    font-weight: 600; 
    font-size: 11px; 
}
QProgressBar.PbUnknown::chunk { background-color: transparent; }

QProgressBar.PbWarning { 
    background-color: rgba(168,85,247,0.1); 
    color: #C084FC; 
    border: 1px solid rgba(168,85,247,0.3); 
    border-radius: 6px; 
    text-align: center; 
    font-weight: 600; 
    font-size: 11px; 
}
QProgressBar.PbWarning::chunk { background-color: transparent; }

/* TV Series specific components */
QWidget#EpisodeRow {
    background-color: #12141A;
    border-radius: 8px;
    border: 1px solid rgba(255, 255, 255, 0.03);
}

QWidget#EpisodeTopBar {
    background-color: transparent;
}

QWidget#EpisodeTopBar:hover {
    background-color: rgba(255, 255, 255, 0.02);
    border-radius: 8px;
}

QLabel#EpisodeBadge {
    background-color: rgba(255, 255, 255, 0.05); /* very subtle backplate */
    color: #3b82f6; /* matching primary blue for E1, E2 */
    font-weight: bold;
    font-size: 11pt;
    border-radius: 6px;
}

QPushButton#CollapseButton {
    background-color: rgba(255, 255, 255, 0.05);
    color: #9CA3AF;
    border-radius: 12px;
    font-size: 9pt;
    font-weight: 500;
}

QPushButton#CollapseButton:hover {
    background-color: rgba(255, 255, 255, 0.1);
    color: #F8FAFC;
}
"""
