import sys
import math
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QLabel, QFrame, QScrollArea, QLayout)
from PyQt6.QtGui import QPainter, QColor, QPen, QBrush, QPainterPath, QPolygonF
from PyQt6.QtCore import Qt, QPointF, QRectF, QTimer

# --- Color Palette (dark theme — standalone) ---
T = "#00d4c8"  # Teal
Y = "#f5c842"  # Yellow
Re = "#ff5564" # Red
Gr = "#3ddc84" # Green
Pu = "#b388ff" # Purple
Muted = "#4a6480"
Bg = "#07090f"
CardBg = "#0e1825"

# --- Light theme overrides (embedded in foldout) ---
_LIGHT_BG = "#f1f4f8"
_LIGHT_CARD_BG = "#ffffff"
_LIGHT_MUTED = "#64748b"
_LIGHT_BODY_COLOR = "#334155"

cards = {}
paths_to_draw = []

class FlowWidget(QWidget):
    """The main canvas where SVG-like arrows are drawn under the widgets."""
    def __init__(self, bg_color=None, spine_color=None, parent=None):
        super().__init__(parent)
        self._bg_color = bg_color or Bg
        self._spine_color = spine_color or T

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Background
        painter.fillRect(self.rect(), QColor(self._bg_color))
        
        # Draw spine timeline track
        painter.setPen(QPen(QColor(self._spine_color), 1, Qt.PenStyle.DashLine))
        painter.drawLine(100, 93, self.width() - 100, 93)
        
        # Draw paths
        for path, color_hex, dashed in paths_to_draw:
            pen = QPen(QColor(color_hex), 2)
            if dashed:
                pen.setStyle(Qt.PenStyle.DashLine)
                pen.setDashPattern([5, 4])
            painter.setPen(pen)
            painter.drawPath(path)
            
            # Arrowheads
            if path.elementCount() > 1:
                p2 = path.elementAt(path.elementCount() - 1)
                p1 = path.elementAt(path.elementCount() - 2)
                self.draw_arrowhead(painter, p1, p2, color_hex)
                
    def draw_arrowhead(self, painter, p1, p2, color_hex):
        if p1.x == p2.x and p1.y == p2.y:
            return
            
        dx = p2.x - p1.x
        dy = p2.y - p1.y
        angle = math.atan2(dy, dx)
        
        arrow_len = 8
        
        p_tip = QPointF(p2.x, p2.y)
        p_left = QPointF(p2.x - arrow_len * math.cos(angle - 0.5), p2.y - arrow_len * math.sin(angle - 0.5))
        p_right = QPointF(p2.x - arrow_len * math.cos(angle + 0.5), p2.y - arrow_len * math.sin(angle + 0.5))
        
        poly = QPolygonF([p_tip, p_left, p_right])
        painter.setBrush(QBrush(QColor(color_hex)))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawPolygon(poly)

# --- Routing Engine Helpers ---
def G(id_str):
    if id_str not in cards: return None
    widget = cards[id_str]
    rect = widget.geometry()
    pos = widget.mapTo(main_widget, rect.topLeft())
    return {
        'top': pos.y(),
        'bottom': pos.y() + rect.height(),
        'left': pos.x(),
        'right': pos.x() + rect.width(),
        'cx': pos.x() + rect.width() / 2,
        'cy': pos.y() + rect.height() / 2,
        'h': rect.height(),
    }

def colOf(id_str):
    w = cards[id_str]
    while w.parentWidget() != main_widget and w.parentWidget() is not None:
        w = w.parentWidget()
    return w

def gapCX(id_str):
    col = colOf(id_str)
    idx = main_layout.indexOf(col)
    if idx + 1 < main_layout.count():
        next_col = main_layout.itemAt(idx + 1).widget()
        return (col.geometry().right() + next_col.geometry().left()) / 2
    return col.geometry().right() + 40

def colRX(id_str):
    return colOf(id_str).geometry().right()

def colLX(id_str):
    return colOf(id_str).geometry().left()

def mp(path_str, color_hex, dashed=False):
    path = QPainterPath()
    parts = path_str.split()
    i = 0
    while i < len(parts):
        cmd = parts[i]
        x = float(parts[i+1])
        y = float(parts[i+2])
        if cmd == 'M':
            path.moveTo(x, y)
        elif cmd == 'L':
            path.lineTo(x, y)
        i += 3
    paths_to_draw.append((path, color_hex, dashed))

# --- SVG Recreations ---
def V(fromId, toId, c, x=None):
    f, t = G(fromId), G(toId)
    if not f or not t: return
    px = x if x is not None else f['cx']
    mp(f"M {px} {f['bottom']+4} L {px} {t['top']-7}", c)

def FWD(fromId, toId, c, gapOff=0, yFromOff=0, yToFrac=0.5):
    f, t = G(fromId), G(toId)
    if not f or not t: return
    gx = gapCX(fromId) + gapOff
    y1 = f['bottom'] + 4 + yFromOff
    yE = t['top'] + t['h'] * yToFrac
    mp(f"M {f['cx']} {y1} L {gx} {y1} L {gx} {yE} L {t['left']-2} {yE}", c)

def SKIP(fromId, toId, c, gOff=0):
    f, t = G(fromId), G(toId)
    if not f or not t: return
    gx = colRX(fromId) + 10 + gOff
    mp(f"M {f['right']+2} {f['cy']} L {gx} {f['cy']} L {gx} {t['top']-10} L {t['cx']} {t['top']-10} L {t['cx']} {t['top']-2}", c)

def LOOP_UP(fromId, toId, c):
    f, t = G(fromId), G(toId)
    if not f or not t: return
    gx = colRX(fromId) + 26
    mp(f"M {f['right']+2} {f['cy']} L {gx} {f['cy']} L {gx} {t['top']-10} L {t['cx']} {t['top']-10} L {t['cx']} {t['top']-2}", c, dashed=True)

def LOOP_BACK(fromId, toId, c, laneOff=0):
    f, t = G(fromId), G(toId)
    if not f or not t: return
    maxB = max((G(cid)['bottom'] for cid in cards), default=0)
    laneY = maxB + 32 + laneOff * 18
    rx = colRX(fromId) + 26
    lx = colLX(toId) - 18
    mp(f"M {f['right']+2} {f['cy']} L {rx} {f['cy']} L {rx} {laneY} L {lx} {laneY} L {lx} {t['top']-10} L {t['cx']} {t['top']-10} L {t['cx']} {t['top']-2}", c, dashed=True)

# --- Component Builders ---
def make_card(id_str, title, body, color_hex, body_color=None):
    _body_color = body_color or "#dde7f5"
    _card_bg = CardBg
    c = QFrame()
    c.setObjectName("card")
    c.setFixedWidth(210)
    c.setStyleSheet(f"""
        QFrame#card {{
            background-color: {_card_bg};
            border-radius: 8px;
            border-left: 3px solid {color_hex};
        }}
        QLabel#title {{ color: {color_hex}; font-size: 11px; font-weight: bold; background: transparent; }}
        QLabel#body {{ color: {_body_color}; font-size: 10px; background: transparent; }}
        QWidget#dot {{ background-color: {color_hex}; border-radius: 3px; }}
    """)
    lay = QVBoxLayout(c)
    lay.setContentsMargins(10, 10, 10, 10)
    lay.setSpacing(6)
    
    t_row = QWidget()
    t_row.setStyleSheet("background: transparent;")
    t_lay = QHBoxLayout(t_row)
    t_lay.setContentsMargins(0, 0, 0, 0)
    t_lay.setSpacing(6)
    
    dot = QWidget()
    dot.setObjectName("dot")
    dot.setFixedSize(6, 6)
    t_lay.addWidget(dot)
    
    lbl_t = QLabel(title)
    lbl_t.setObjectName("title")
    t_lay.addWidget(lbl_t)
    t_lay.addStretch()
    
    lay.addWidget(t_row)
    
    lbl_b = QLabel(body)
    lbl_b.setObjectName("body")
    lbl_b.setWordWrap(True)
    lay.addWidget(lbl_b)
    
    cards[id_str] = c
    return c

def make_phase_col(num, label, color_hex):
    w = QWidget()
    w.setFixedWidth(220)
    lay = QVBoxLayout(w)
    lay.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.setSpacing(25)
    
    header = QWidget()
    header.setFixedSize(86, 86)
    header.setStyleSheet(f"""
        QWidget {{
            background-color: {CardBg}; border-radius: 43px;
            border: 2px solid rgba({int(color_hex[1:3], 16)}, {int(color_hex[3:5], 16)}, {int(color_hex[5:7], 16)}, 0.4);
        }}
    """)
    h_lay = QVBoxLayout(header)
    h_lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
    
    l_num = QLabel(num)
    l_num.setStyleSheet(f"color: {color_hex}; font-size: 22px; font-weight: bold; background: transparent;")
    l_num.setAlignment(Qt.AlignmentFlag.AlignCenter)
    
    l_lbl = QLabel(label.upper())
    l_lbl.setStyleSheet(f"color: {Muted}; font-size: 10px; font-weight: bold; letter-spacing: 1px; background: transparent;")
    l_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    
    h_lay.addWidget(l_num)
    h_lay.addWidget(l_lbl)
    
    lay.addWidget(header, alignment=Qt.AlignmentFlag.AlignHCenter)
    return w

def make_branch(card1, card2):
    w = QWidget()
    w.setFixedWidth(210)
    lay = QHBoxLayout(w)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.setSpacing(6)
    card1.setFixedWidth(102)
    card2.setFixedWidth(102)
    lay.addWidget(card1)
    lay.addWidget(card2)
    return w

def make_tier_box(children, light=False):
    w = QFrame()
    w.setFixedWidth(210)
    border_color = "rgba(100,80,180,0.25)" if light else "rgba(179,136,255,0.3)"
    w.setStyleSheet(f"QFrame {{ border-left: 2px solid {border_color}; background: transparent; }}")
    lay = QVBoxLayout(w)
    lay.setContentsMargins(10, 0, 0, 0)
    lay.setSpacing(20)
    
    lbl_color = "#7c3aed" if light else Pu
    lbl = QLabel("TIERED FALLBACK LOOP")
    lbl.setStyleSheet(f"color: {lbl_color}; font-size: 10px; font-weight: bold; letter-spacing: 1px;")
    lay.addWidget(lbl)
    
    for c in children:
        c.setFixedWidth(190)
        lay.addWidget(c)
    return w

class ConversionFlowViewer(QScrollArea):
    """Embeddable flowchart widget (light theme) for use inside other layouts."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setStyleSheet(
            "QScrollArea { border: none; background-color: #f1f4f8; }"
            "QScrollBar:horizontal { height: 8px; background: #e2e8f0; border-radius: 4px; }"
            "QScrollBar::handle:horizontal { background: #94a3b8; border-radius: 4px; min-width: 30px; }"
            "QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }"
        )
        self.setFixedHeight(300)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        # Switch to light palette before building
        self._apply_light_palette()

        global main_widget, main_layout
        main_widget = FlowWidget(bg_color=_LIGHT_BG, spine_color="#94a3b8")
        main_layout = QHBoxLayout(main_widget)
        main_layout.setSpacing(60)
        main_layout.setContentsMargins(30, 40, 30, 60)
        main_layout.setSizeConstraint(QLayout.SizeConstraint.SetMinAndMaxSize)

        self.build_ui()
        self.setWidget(main_widget)

    def _apply_light_palette(self):
        """Temporarily override module-level palette globals for light theme."""
        global CardBg, Muted
        CardBg = _LIGHT_CARD_BG
        Muted  = _LIGHT_MUTED

    def build_ui(self):
        _build_pipeline_ui(light=True)

    def showEvent(self, event):
        super().showEvent(event)
        QTimer.singleShot(120, self.build_arrows)

    def build_arrows(self):
        _build_pipeline_arrows()


class TimelineApp(QMainWindow):
    """Standalone window for running the flowchart independently."""
    def __init__(self):
        super().__init__()
        self.setWindowTitle("🎬 Media Manager Conversion Pipeline")
        self.resize(1500, 800)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; }")
        
        global main_widget, main_layout
        main_widget = FlowWidget()
        main_layout = QHBoxLayout(main_widget)
        main_layout.setSpacing(80)
        main_layout.setContentsMargins(50, 50, 50, 300)
        main_layout.setSizeConstraint(QLayout.SizeConstraint.SetMinAndMaxSize)
        
        _build_pipeline_ui()
        scroll.setWidget(main_widget)
        self.setCentralWidget(scroll)

    def showEvent(self, event):
        super().showEvent(event)
        QTimer.singleShot(100, lambda: _build_pipeline_arrows())


# --- Shared Pipeline Construction ---
def _build_pipeline_ui(light=False):
    """Builds all phase columns and cards into main_layout."""
    bc = _LIGHT_BODY_COLOR if light else None

    # Phase 1
    p1 = make_phase_col("01", "Ingest", T)
    p1.layout().addWidget(make_card("p1-input", "User Input", "Add media path to conversion.txt", T, bc))
    p1.layout().addWidget(make_card("p1-queue", "Queue Management", "DatabaseManager reads file\nAdds to SQLite as PENDING", T, bc))
    main_layout.addWidget(p1)
    
    # Phase 2
    p2 = make_phase_col("02", "Worker", T)
    p2.layout().addWidget(make_card("p2-dequeue", "Job Dequeue", "PENDING → PROCESSING", T, bc))
    p2.layout().addWidget(make_card("p2-fail", "Path Validation — FAIL", "Rejects /share/seeding\nMarks FAILED", Re, bc))
    p2.layout().addWidget(make_card("p2-pass", "Path Validation — PASS", "Path accepted, proceed", T, bc))
    main_layout.addWidget(p2)
    
    # Phase 3
    p3 = make_phase_col("03", "Type", Y)
    p3.layout().addWidget(make_card("p3-router", "Media Type Router", "Analyse base path", Y, bc))
    b3 = make_branch(make_card("p3-movie", "MOVIE", "movies_root", Gr, bc), make_card("p3-tv", "TV", "tv_root", Y, bc))
    p3.layout().addWidget(b3)
    main_layout.addWidget(p3)
    
    # Phase 4
    p4 = make_phase_col("04", "Factory", Pu)
    p4.layout().addWidget(make_card("p4-movie", "Movie Processing", "Dir → largest file → Movie\nFile → single Movie", Gr, bc))
    p4.layout().addWidget(make_card("p4-tv", "TV Series Processing", "Dir → scan .mkv .mp4\n→ TVEpisode objects", Y, bc))
    main_layout.addWidget(p4)
    
    # Phase 5
    p5 = make_phase_col("05", "Check", Y)
    p5.layout().addWidget(make_card("p5-check", "MP4 Existence Check", "Does target .mp4 exist?", Y, bc))
    p5.layout().addWidget(make_card("p5-fail", "EXISTS → Fast Fail", "Skip encode · clean source\nMark COMPLETE", Re, bc))
    p5.layout().addWidget(make_card("p5-pass", "NOT EXISTS → Continue", "Proceed to pipeline", T, bc))
    main_layout.addWidget(p5)
    
    # Phase 6
    p6 = make_phase_col("06", "Subs", Pu)
    p6.layout().addWidget(make_card("p6-discovery", "Subtitle Discovery", "Find external OR extract embedded", Pu, bc))
    p6.layout().addWidget(make_card("p6-vobsub", "Binary VobSub", ".idx / MPEG-PS header\nKeep .sub/.idx", Pu, bc))
    p6.layout().addWidget(make_card("p6-text", "Text Subtitles", ".srt .ass MicroDVD\nForce UTF-8 · RO char rules", Pu, bc))
    main_layout.addWidget(p6)
    
    # Phase 7
    p7 = make_phase_col("07", "Encode", T)
    p7.layout().addWidget(make_card("p7-heuristics", "Heuristics Check", "Query DB for last successful params", T, bc))
    p7.layout().addWidget(make_card("p7-audio", "Audio Processing", "5.1/7.1 → 256k · Stereo → 192k", Pu, bc))
    tier_children = [
        make_card("p7-t1", "Tier 1 — Max Quality", "bf=7 lad=40 async=8", Pu, bc),
        make_card("p7-t2", "Tier 2 — Balanced ⭐", "bf=4 lad=20 async=4", T, bc),
        make_card("p7-t3", "Tier 3 — Safe Mode", "bf=0 lad=10 async=2", Pu, bc)
    ]
    p7.layout().addWidget(make_tier_box(tier_children, light=light))
    p7.layout().addWidget(make_card("p7-outcome", "Outcome Handler", "Success → save to DB\nFailure → del temp · next tier", Y, bc))
    main_layout.addWidget(p7)
    
    # Phase 8
    p8 = make_phase_col("08", "Final", Gr)
    p8.layout().addWidget(make_card("p8-relocate", "File Relocation", "Move encoded .mp4 + subtitles", T, bc))
    b8 = make_branch(make_card("p8-movie", "Movies", "/archive/movies/", Gr, bc), make_card("p8-tv", "TV", "/archive/tv/", Y, bc))
    p8.layout().addWidget(b8)
    p8.layout().addWidget(make_card("p8-cleanup", "Source Cleanup", "Delete original · remove empty dirs", T, bc))
    p8.layout().addWidget(make_card("p8-complete", "✓ Job Complete", "Status: COMPLETED\nLog metrics", Gr, bc))
    main_layout.addWidget(p8)


def _build_pipeline_arrows():
    """Computes and draws all arrow paths between cards."""
    paths_to_draw.clear()
    
    # Phase 1
    V('p1-input', 'p1-queue', T)
    FWD('p1-queue', 'p2-dequeue', T)

    # Phase 2
    V('p2-dequeue', 'p2-fail', Re)
    SKIP('p2-dequeue', 'p2-pass', T)
    LOOP_UP('p2-fail', 'p2-dequeue', Re)
    FWD('p2-pass', 'p3-router', T)

    # Phase 3
    m3, tv3 = G('p3-movie'), G('p3-tv')
    V('p3-router', 'p3-movie', Gr, x=m3['cx'])
    V('p3-router', 'p3-tv', Y, x=tv3['cx'])
    FWD('p3-movie', 'p4-movie', Gr, -8, 0, 0.35)
    FWD('p3-tv', 'p4-tv', Y, 8, 12, 0.65)

    # Phase 4
    FWD('p4-movie', 'p5-check', Gr, -8, 0, 0.32)
    FWD('p4-tv', 'p5-check', Y, 8, 0, 0.68)

    # Phase 5
    V('p5-check', 'p5-fail', Re)
    SKIP('p5-check', 'p5-pass', T)
    LOOP_BACK('p5-fail', 'p2-dequeue', Re, 0)
    FWD('p5-pass', 'p6-discovery', T)

    # Phase 6
    V('p6-discovery', 'p6-vobsub', Pu)
    SKIP('p6-discovery', 'p6-text', Pu)
    FWD('p6-vobsub', 'p7-heuristics', Pu, -8, 0, 0.32)
    FWD('p6-text', 'p7-heuristics', Pu, 8, 0, 0.68)

    # Phase 7
    V('p7-heuristics', 'p7-audio', T)
    SKIP('p7-audio', 'p7-t1', Pu)
    V('p7-t1', 'p7-t2', Pu)
    V('p7-t2', 'p7-t3', Pu)
    SKIP('p7-t3', 'p7-outcome', Y, 16)
    FWD('p7-outcome', 'p8-relocate', T)

    # Phase 8
    m8, tv8 = G('p8-movie'), G('p8-tv')
    V('p8-relocate', 'p8-movie', Gr, x=m8['cx'])
    V('p8-relocate', 'p8-tv', Y, x=tv8['cx'])
    V('p8-movie', 'p8-cleanup', Gr, x=m8['cx'])
    V('p8-tv', 'p8-cleanup', Y, x=tv8['cx'])
    V('p8-cleanup', 'p8-complete', Gr)
    
    main_widget.update()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = TimelineApp()
    window.show()
    sys.exit(app.exec())

