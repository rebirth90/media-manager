import sys
import math
import json
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QLabel, QFrame, QScrollArea, QLayout, QSizePolicy, QGraphicsOpacityEffect)
from PyQt6.QtGui import QPainter, QColor, QPen, QBrush, QPainterPath, QPolygonF
from PyQt6.QtCore import Qt, QPointF, QTimer, QUrl, QPropertyAnimation, QEasingCurve, QSize, pyqtSignal
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEngineSettings

# --- Color Palette ---
T = "#00d4c8"  # Teal
Y = "#f5c842"  # Yellow
Re = "#ff5564" # Red
B = "#3b82f6"  # Blue 
Pu = "#b388ff" # Purple
Muted = "#4a6480"
Bg = "#07090f"
CardBg = "#0e1825"

# Global tracking for standalone painter
cards = {}
paths_to_draw = []

class FlowWidget(QWidget):
    def __init__(self, bg_color=None, spine_color=None, parent=None):
        super().__init__(parent)
        self._bg_color = bg_color or Bg
        self._spine_color = spine_color or T

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor(self._bg_color))
        painter.setPen(QPen(QColor(self._spine_color), 1, Qt.PenStyle.DashLine))
        painter.drawLine(100, 93, self.width() - 100, 93)
        for path, color_hex, dashed in paths_to_draw:
            pen = QPen(QColor(color_hex), 2)
            if dashed:
                pen.setStyle(Qt.PenStyle.DashLine)
                pen.setDashPattern([5, 4])
            painter.setPen(pen)
            painter.drawPath(path)
            if path.elementCount() > 1:
                p2 = path.elementAt(path.elementCount() - 1)
                p1 = path.elementAt(path.elementCount() - 2)
                self.draw_arrowhead(painter, p1, p2, color_hex)
                
    def draw_arrowhead(self, painter, p1, p2, color_hex):
        if p1.x == p2.x and p1.y == p2.y: return
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

def G(id_str):
    if id_str not in cards: return None
    widget = cards[id_str]
    rect = widget.geometry()
    pos = widget.mapTo(main_widget, rect.topLeft())
    return {'top': pos.y(), 'bottom': pos.y() + rect.height(), 'left': pos.x(), 'right': pos.x() + rect.width(), 'cx': pos.x() + rect.width() / 2, 'cy': pos.y() + rect.height() / 2, 'h': rect.height()}

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

def colRX(id_str): return colOf(id_str).geometry().right()
def colLX(id_str): return colOf(id_str).geometry().left()

def mp(path_str, color_hex, dashed=False):
    path = QPainterPath()
    parts = path_str.split()
    i = 0
    while i < len(parts):
        cmd = parts[i]
        x = float(parts[i+1])
        y = float(parts[i+2])
        if cmd == 'M': path.moveTo(x, y)
        elif cmd == 'L': path.lineTo(x, y)
        i += 3
    paths_to_draw.append((path, color_hex, dashed))

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

def make_card(id_str, title, body, color_hex, body_color=None):
    _body_color = body_color or "#dde7f5"
    _card_bg = CardBg
    c = QFrame()
    c.setObjectName("card")
    c.setFixedWidth(210)
    c.setStyleSheet(f"""
        QFrame#card {{ background-color: {_card_bg}; border-radius: 8px; border-left: 3px solid {color_hex}; }}
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
        QWidget {{ background-color: {CardBg}; border-radius: 43px; border: 2px solid rgba({int(color_hex[1:3], 16)}, {int(color_hex[3:5], 16)}, {int(color_hex[5:7], 16)}, 0.4); }}
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

class ConversionFlowViewer(QWidget):
    height_calculated = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._page_loaded = False
        self._is_revealed = False
        self._pending_json = None
        self._forced_h = 500
        self._foldout_reveal_attempts = 0

        self.lay = QVBoxLayout(self)
        self.lay.setContentsMargins(0, 0, 0, 0)

        # --- 1. Loading Container ---
        self.loading_container = QWidget()
        self.loading_container.setFixedHeight(150)
        self.loading_container.setStyleSheet("background-color: transparent;")
        l_lay = QVBoxLayout(self.loading_container)
        l_lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.lbl_loading = QLabel("Loading Pipeline Engine...")
        self.lbl_loading.setStyleSheet("color: #00d4c8; font-size: 14px; font-weight: bold; letter-spacing: 1px;")
        l_lay.addWidget(self.lbl_loading)
        
        self.lay.addWidget(self.loading_container)
        
        # Pulse Animation for Loading Text
        self.pulse_effect = QGraphicsOpacityEffect(self.lbl_loading)
        self.lbl_loading.setGraphicsEffect(self.pulse_effect)
        self.pulse_anim = QPropertyAnimation(self.pulse_effect, b"opacity")
        self.pulse_anim.setDuration(800)
        self.pulse_anim.setStartValue(0.3)
        self.pulse_anim.setEndValue(1.0)
        self.pulse_anim.setEasingCurve(QEasingCurve.Type.InOutSine)
        self.pulse_anim.setLoopCount(-1) # Infinite pulsing
        self.pulse_anim.start()

        # --- 2. Web View ---
        self._view = QWebEngineView()
        self._view.hide() # Hidden during load to prevent visual jumping
        self._view.page().setBackgroundColor(Qt.GlobalColor.transparent)
        
        settings = self._view.settings()
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.ScrollAnimatorEnabled, False)
        settings.setAttribute(QWebEngineSettings.WebAttribute.ShowScrollBars, False)

        self._view.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._view.loadFinished.connect(self._on_load_finished)

        from src.presentation.widgets.pipeline_asset_builder import PipelineAssetBuilder
        builder = PipelineAssetBuilder()
        html_content = builder.build_html("{}")
        from PyQt6.QtCore import QUrl
        self._view.setHtml(html_content, QUrl("about:blank"))
        self.lay.addWidget(self._view)

        self.opacity_effect = QGraphicsOpacityEffect(self._view)
        self._view.setGraphicsEffect(self.opacity_effect)
        self.opacity_effect.setOpacity(0.0)

        # Lock initial container height to the loading screen size
        self.setMinimumHeight(150)
        self.setMaximumHeight(150)
        
        # Failsafe reveal in case loadFinished is dropped during rapid WebEngine initialization
        QTimer.singleShot(3000, self._failsafe_reveal)

    def show_foldout_loading(self, text: str = "Loading conversion chart...") -> None:
        """Show an inline loading placeholder while the foldout settles its final size."""
        self.lbl_loading.setText(text)
        self.loading_container.show()
        self._view.hide()
        self.setMinimumHeight(150)
        self.setMaximumHeight(150)
        self._foldout_reveal_attempts = 0
        self.pulse_anim.start()

    def reveal_after_foldout_expand(self, delay_ms: int = 160) -> None:
        """Reveal the chart only after foldout expansion to prevent half-size first paint."""
        if not self._page_loaded:
            self.show_foldout_loading()
            return
        QTimer.singleShot(max(0, int(delay_ms)), self._reveal_after_foldout_expand)

    def _reveal_after_foldout_expand(self) -> None:
        host_w = self.width()
        if host_w < 500:
            parent = self.parentWidget()
            if parent:
                host_w = max(host_w, parent.width())

        if host_w < 500 and self._foldout_reveal_attempts < 8:
            self._foldout_reveal_attempts += 1
            QTimer.singleShot(100, self._reveal_after_foldout_expand)
            return

        self._is_revealed = True
        self.pulse_anim.stop()

        w = host_w if host_w > 100 else 1000
        zoom = w / 2440.0 if w < 2440.0 else 1.0
        target_h = int(620.0 * zoom)
        self._forced_h = max(target_h, 380)

        self._view.setZoomFactor(zoom)
        self._view.setFixedHeight(self._forced_h)
        self.setMinimumHeight(self._forced_h)
        self.setMaximumHeight(self._forced_h)

        self.loading_container.hide()
        self._view.show()
        self.opacity_effect.setOpacity(1.0)
        self.height_calculated.emit(self._forced_h)
        self.refresh_pipeline()
        
    def _failsafe_reveal(self):
        if not self._page_loaded:
            self._on_load_finished(True)

    def _on_load_finished(self, ok):
        self._page_loaded = True
        self._inject_highlight_styles()

        if self._pending_json:
            self.update_pipeline_state(self._pending_json)

        # Allow webengine 400ms to paint and JS to settle before revealing  
        QTimer.singleShot(400, self._reveal_pipeline)
    def _reveal_pipeline(self):
        if self._is_revealed: return

        # Wait for a stable layout width to avoid half-size first paint.
        host_w = self.width()
        if host_w < 500:
            parent = self.parentWidget()
            if parent:
                host_w = max(host_w, parent.width())
        if host_w < 500:
            QTimer.singleShot(120, self._reveal_pipeline)
            return

        self._is_revealed = True
        
        self.pulse_anim.stop()
        
        # Calculate final mathematical height synchronously
        w = host_w if host_w > 100 else 1000
        zoom = w / 2440.0 if w < 2440.0 else 1.0
        target_h = int(620.0 * zoom)
        self._forced_h = max(target_h, 380)
        
        self._view.setZoomFactor(zoom)
        self._view.setFixedHeight(self._forced_h)

        # Smoothly expand the container layout
        self.expand_anim = QPropertyAnimation(self, b"maximumHeight")
        self.expand_anim.setDuration(500)
        self.expand_anim.setStartValue(150)
        self.expand_anim.setEndValue(self._forced_h)
        self.expand_anim.setEasingCurve(QEasingCurve.Type.InOutExpo)
        
        self.min_expand_anim = QPropertyAnimation(self, b"minimumHeight")
        self.min_expand_anim.setDuration(500)
        self.min_expand_anim.setStartValue(150)
        self.min_expand_anim.setEndValue(self._forced_h)
        self.min_expand_anim.setEasingCurve(QEasingCurve.Type.InOutExpo)

        def on_expand_finished():
            self.loading_container.hide()
            self._view.show()
            
            # Crossfade the fully loaded webview in
            self.fade_anim = QPropertyAnimation(self.opacity_effect, b"opacity")
            self.fade_anim.setDuration(400)
            self.fade_anim.setStartValue(0.0)
            self.fade_anim.setEndValue(1.0)
            self.fade_anim.start()
            
            self.height_calculated.emit(self._forced_h)

        self.expand_anim.finished.connect(on_expand_finished)
        
        self.expand_anim.start()
        self.min_expand_anim.start()

    def _inject_highlight_styles(self):
        css = """
        const style = document.createElement('style');
        style.innerHTML = `
            #page { min-height: 0 !important; padding-bottom: 0 !important; }
            
            @keyframes flowAnim { 
                from { stroke-dashoffset: 15; }
                to { stroke-dashoffset: 0; } 
            }

            @keyframes march {
                from { stroke-dashoffset: 15; }
                to { stroke-dashoffset: 0; }
            }
            
            .stage-success {
                box-shadow: 0 0 15px rgba(74, 222, 128, 0.7), 
                            inset 0 0 8px rgba(74, 222, 128, 0.4) !important;
                border: 2px solid #4ade80 !important;
                opacity: 1.0 !important;
                filter: none !important;
                transition: all 0.4s ease-out;
            }
            
            .stage-fail {
                box-shadow: 0 0 12px rgba(244, 63, 94, 0.6) !important;
                border: 2px solid #f43f5e !important;
                opacity: 1.0 !important;
                filter: none !important;
            }
            
            .stage-skip {
                opacity: 0.25 !important;
                filter: grayscale(100%) brightness(70%) !important;
                box-shadow: none !important;
                border-color: rgba(148, 163, 184, 0.2) !important;
            }

            .arrow-inactive {
                opacity: 0.25 !important;
                filter: grayscale(100%) brightness(70%) !important;
                transition: all 0.4s ease-out;
            }

            path { stroke-width: 1.6px !important; }
            
            path[stroke="#4ade80"] {
                stroke-width: 2.2px !important; 
                stroke-dasharray: 10, 5 !important;
                animation: flowAnim 1s linear infinite !important;
                filter: drop-shadow(0 0 5px rgba(74, 222, 128, 0.8));
                opacity: 1.0 !important;
            }
            
            path[stroke="#f43f5e"] {
                stroke-width: 2.2px !important; 
                filter: drop-shadow(0 0 5px rgba(244, 63, 94, 0.8));
                opacity: 1.0 !important;
            }
            
            path[marker-end*="green"] {
                stroke: #4ade80 !important;
                stroke-width: 2.2px !important;
                stroke-dasharray: 10, 5 !important;
                animation: flowAnim 1s linear infinite !important;
                filter: drop-shadow(0 0 5px rgba(74, 222, 128, 0.8));
            }
        `;
        document.head.appendChild(style);
        """
        self._view.page().runJavaScript(css)

    def sizeHint(self):
        return QSize(2440, 620)
        
    def minimumSizeHint(self):
        return QSize(800, 380)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        
        # Suppress layout thrashing during load
        if not self._is_revealed:
            return 

        w = self.width()
        zoom = w / 2440.0 if w < 2440.0 else 1.0
        target_h = int(620.0 * zoom)
        self._forced_h = max(target_h, 380)
        
        self.setMinimumHeight(self._forced_h)
        self.setMaximumHeight(self._forced_h)
        self._view.setFixedHeight(self._forced_h)
        self._view.setZoomFactor(zoom)

    def update_pipeline_state(self, stages_data, force: bool = False) -> None:
        try:
            if isinstance(stages_data, str):
                raw_flags = json.loads(stages_data) if stages_data else {}
            else:
                raw_flags = stages_data.copy() if stages_data else {}
                
            all_keys = [
                "p1-input", "p1-queue", "p2-dequeue", "p2-pass",
                "p3-router", "p3-movie", "p3-tv", "p4-movie", "p4-tv",
                "p5-check", "p5-fail", "p5-pass", "p6-discovery", "p6-vobsub", "p6-text",
                "p7-heuristics", "p7-audio", "p7-t1", "p7-t2", "p7-t3", "p7-outcome",
                "p8-relocate", "p8-movie", "p8-tv", "p8-cleanup", "p8-complete"
            ]
            flags = {k: False for k in all_keys}
            
            for k, v in raw_flags.items():
                if k in flags:
                    if isinstance(v, str):
                        val = v.lower()
                        if val == 'fail':
                            flags[k] = 'fail'
                        elif val == 'skip':
                            flags[k] = 'skip'
                        elif val == 'pass':
                            flags[k] = 'pass'
                        else:
                            flags[k] = val not in ('false', '0', '')
                    else:
                        flags[k] = bool(v)

            clean_json = json.dumps(flags)
            if (not force) and getattr(self, '_rendered_json', None) == clean_json:
                return
                
            if not self._page_loaded: 
                self._pending_json = clean_json
                return
                
            self._rendered_json = clean_json

            js = f"""
            (function() {{
                const flags = {clean_json};
                if (window.setPipelineState) {{ 
                    const mapped = {{}};
                    
                    Object.keys(flags).forEach(k => {{
                        if (flags[k] === 'fail') mapped[k] = 'fail';
                        else if (flags[k] === 'skip') mapped[k] = 'skip';
                        else if (flags[k] === true || flags[k] === 'pass') {{
                             if (k === 'p5-fail') mapped[k] = 'fail';
                             else mapped[k] = 'pass';
                        }} else {{
                             mapped[k] = 'pending';
                        }}
                    }});
                    
                    if (mapped['p3-movie'] === 'pass' || mapped['p4-movie'] === 'pass' || mapped['p8-movie'] === 'pass') {{
                        mapped['p3-tv'] = 'skip';
                        mapped['p4-tv'] = 'skip';
                        mapped['p8-tv'] = 'skip';
                    }} else if (mapped['p3-tv'] === 'pass' || mapped['p4-tv'] === 'pass' || mapped['p8-tv'] === 'pass') {{
                        mapped['p3-movie'] = 'skip';
                        mapped['p4-movie'] = 'skip';
                        mapped['p8-movie'] = 'skip';
                    }}
                    
                    if (mapped['p5-fail'] === 'fail') {{
                        mapped['p5-pass'] = 'skip';
                    }} else if (mapped['p5-pass'] === 'pass') {{
                        mapped['p5-fail'] = 'skip';
                    }}
                    
                    if (flags['p7-t1'] || flags['p7-t2'] || flags['p7-t3'] || flags['p7-audio']) {{
                        mapped['p7-tiers'] = 'pass';
                    }}
                    
                    window.setPipelineState(mapped); 
                    
                    setTimeout(() => {{
                        Object.keys(mapped).forEach(k => {{
                            const el = document.getElementById(k);
                            if (el) {{
                                if (mapped[k] === 'skip') el.classList.add('stage-skip');
                                else el.classList.remove('stage-skip');
                            }}
                        }});
                    }}, 50);
                }}
            }})();
            """
            self._view.page().runJavaScript(js)
        except Exception:
            pass

    def refresh_pipeline(self) -> None:
        """Force a redraw/rebind when a hidden foldout becomes visible."""
        try:
            if not self._page_loaded:
                return

            if getattr(self, '_rendered_json', None):
                self.update_pipeline_state(self._rendered_json, force=True)

            self._view.page().runJavaScript(
                "window.dispatchEvent(new Event('resize'));"
            )
        except Exception:
            pass

class TimelineApp(QMainWindow):
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

def _build_pipeline_ui(light=False):
    p1 = make_phase_col("01", "Ingest", T)
    p1.layout().addWidget(make_card("p1-input", "User Input", "Add media path to conversion.txt", T))
    p1.layout().addWidget(make_card("p1-queue", "Queue Management", "DatabaseManager reads file\nAdds to SQLite as PENDING", T))
    main_layout.addWidget(p1)
    
    p2 = make_phase_col("02", "Worker", T)
    p2.layout().addWidget(make_card("p2-dequeue", "Job Dequeue", "PENDING → PROCESSING", T))
    p2.layout().addWidget(make_card("p2-pass", "Path Validation — PASS", "Path accepted, proceed", T))
    main_layout.addWidget(p2)
    
    p3 = make_phase_col("03", "Type", Y)
    p3.layout().addWidget(make_card("p3-router", "Media Type Router", "Analyse base path", Y))
    p3.layout().addWidget(make_branch(make_card("p3-movie", "MOVIE", "movies_root", B), make_card("p3-tv", "TV", "tv_root", Y)))
    main_layout.addWidget(p3)
    
    p4 = make_phase_col("04", "Factory", Pu)
    p4.layout().addWidget(make_card("p4-movie", "Movie Processing", "Dir → largest file", B))
    p4.layout().addWidget(make_card("p4-tv", "TV Series Processing", "Dir → scan .mkv .mp4", Y))
    main_layout.addWidget(p4)
    
    p5 = make_phase_col("05", "Check", Y)
    p5.layout().addWidget(make_card("p5-check", "MP4 Existence Check", "Does target .mp4 exist?", Y))
    p5.layout().addWidget(make_card("p5-fail", "EXISTS → Fast Fail", "Skip encode", Re))
    p5.layout().addWidget(make_card("p5-pass", "NOT EXISTS → Continue", "Proceed", T))
    main_layout.addWidget(p5)
    
    p6 = make_phase_col("06", "Subs", Pu)
    p6.layout().addWidget(make_card("p6-discovery", "Subtitle Discovery", "Find external", Pu))
    p6.layout().addWidget(make_card("p6-vobsub", "Binary VobSub", ".idx / MPEG-PS", Pu))
    p6.layout().addWidget(make_card("p6-text", "Text Subtitles", ".srt .ass", Pu))
    main_layout.addWidget(p6)
    
    p7 = make_phase_col("07", "Encode", T)
    p7.layout().addWidget(make_card("p7-heuristics", "Heuristics Check", "Query DB", T))
    p7.layout().addWidget(make_card("p7-audio", "Audio Processing", "5.1/7.1 → 256k", Pu))
    p7.layout().addWidget(make_tier_box([make_card("p7-t1", "Tier 1", "Max Quality", Pu), make_card("p7-t2", "Tier 2", "Balanced", T)]))
    p7.layout().addWidget(make_card("p7-outcome", "Outcome Handler", "Success → save", Y))
    main_layout.addWidget(p7)
    
    p8 = make_phase_col("08", "Final", T)
    p8.layout().addWidget(make_card("p8-relocate", "File Relocation", "Move files", T))
    p8.layout().addWidget(make_branch(make_card("p8-movie", "Movies", "/archive/movies/", B), make_card("p8-tv", "TV", "/archive/tv/", Y)))
    p8.layout().addWidget(make_card("p8-cleanup", "Source Cleanup", "Delete original", T))
    p8.layout().addWidget(make_card("p8-complete", "✓ Job Complete", "COMPLETED", T))
    main_layout.addWidget(p8)

def _build_pipeline_arrows():
    paths_to_draw.clear()
    V('p1-input', 'p1-queue', T)
    FWD('p1-queue', 'p2-dequeue', T)
    
    V('p2-dequeue', 'p2-pass', T)
    
    FWD('p2-pass', 'p3-router', T)
    m3, tv3 = G('p3-movie'), G('p3-tv')
    
    V('p3-router', 'p3-movie', B, x=m3['cx'])
    V('p3-router', 'p3-tv', Y, x=tv3['cx'])
    FWD('p3-movie', 'p4-movie', B, -8, 0, 0.35)
    FWD('p3-tv', 'p4-tv', Y, 8, 12, 0.65)
    FWD('p4-movie', 'p5-check', B, -8, 0, 0.32)
    FWD('p4-tv', 'p5-check', Y, 8, 0, 0.68)
    
    V('p5-check', 'p5-fail', Re)
    SKIP('p5-check', 'p5-pass', T)
    LOOP_BACK('p5-fail', 'p2-dequeue', Re, 0)
    FWD('p5-pass', 'p6-discovery', T)
    V('p6-discovery', 'p6-vobsub', Pu)
    SKIP('p6-discovery', 'p6-text', Pu)
    FWD('p6-vobsub', 'p7-heuristics', Pu, -8, 0, 0.32)
    FWD('p6-text', 'p7-heuristics', Pu, 8, 0, 0.68)
    V('p7-heuristics', 'p7-audio', T)
    FWD('p7-outcome', 'p8-relocate', T)
    m8, tv8 = G('p8-movie'), G('p8-tv')
    
    V('p8-relocate', 'p8-movie', B, x=m8['cx'])
    V('p8-relocate', 'p8-tv', Y, x=tv8['cx'])
    V('p8-movie', 'p8-cleanup', B, x=m8['cx'])
    V('p8-tv', 'p8-cleanup', Y, x=tv8['cx'])
    V('p8-cleanup', 'p8-complete', T)
    main_widget.update()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = TimelineApp()
    window.show()
    sys.exit(app.exec())