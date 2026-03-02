import sys
from PyQt6.QtWidgets import (QGraphicsView, QGraphicsScene, 
                             QGraphicsProxyWidget, QWidget, QVBoxLayout, QHBoxLayout, 
                             QLabel, QPushButton, QFrame, QGraphicsPathItem)
from PyQt6.QtCore import Qt, QPointF, QVariantAnimation, QTimer, QEasingCurve
from PyQt6.QtGui import QPainter, QColor, QPen, QBrush, QFont, QPainterPath, QPolygonF

# --- STYLESHEETS (Matching Dark Theme) ---
MAIN_NODE_QSS = """
QPushButton {
    background-color: #1e293b;
    color: #f1f5f9;
    border: 2px solid #38bdf8;
    border-radius: 8px;
    padding: 12px 20px;
    font-size: 14px;
    font-weight: bold;
}
QPushButton:hover {
    background-color: #334155;
    border: 2px solid #a78bfa;
}
"""

SUB_FLOW_FRAME_QSS = """
QFrame {
    background-color: #1e293b;
    border: 1px dashed #475569;
    border-bottom: 3px solid #a78bfa;
    border-radius: 8px;
}
"""

def get_subnode_qss(border_color="#a78bfa"):
    return f"""
    QFrame {{
        background-color: #334155;
        border: 1px solid {border_color};
        border-radius: 6px;
    }}
    """

# --- CUSTOM WIDGETS ---
class SubNode(QFrame):
    def __init__(self, title, desc, border_color="#a78bfa"):
        super().__init__()
        self.setStyleSheet(get_subnode_qss(border_color))
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        
        t_lbl = QLabel(f"<b>{title}</b>")
        t_lbl.setStyleSheet("color: #f1f5f9; border: none; background: transparent;")
        t_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        d_lbl = QLabel(desc)
        d_lbl.setStyleSheet("color: #cbd5e1; border: none; background: transparent; font-size: 11px;")
        d_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        layout.addWidget(t_lbl)
        layout.addWidget(d_lbl)

class PhaseElement:
    """Holds the logical grouping of a Main Node and its Sub Flow."""
    def __init__(self, scene, title, sub_components):
        self.scene = scene
        self.is_expanded = False
        self.target_x = 0.0
        
        # Main Button
        self.btn = QPushButton(title)
        self.btn.setStyleSheet(MAIN_NODE_QSS)
        self.btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.main_proxy = scene.addWidget(self.btn)
        
        # Sub Flow Container
        self.sub_frame = QFrame()
        self.sub_frame.setStyleSheet(SUB_FLOW_FRAME_QSS)
        sub_layout = QHBoxLayout(self.sub_frame)
        sub_layout.setContentsMargins(15, 15, 15, 15)
        
        for comp in sub_components:
            if isinstance(comp, str): # Arrow
                lbl = QLabel(comp)
                lbl.setStyleSheet("color: #475569; font-weight: bold; font-size: 16px; border: none; background: transparent;")
                sub_layout.addWidget(lbl)
            else:
                sub_layout.addWidget(comp)
                
        self.sub_proxy = scene.addWidget(self.sub_frame)
        self.sub_proxy.setOpacity(0.0)
        self.sub_proxy.setVisible(False)
        
        # Hook up click
        self.btn.clicked.connect(self.toggle)

    def toggle(self):
        self.is_expanded = not self.is_expanded
        if self.scene.parent():
            self.scene.parent().trigger_layout_animation()

    def main_width(self): return self.main_proxy.size().width()
    def sub_width(self): return self.sub_proxy.size().width()

# --- MAIN SCENE AND VIEW ---
class DynamicTimelineScene(QGraphicsScene):
    def __init__(self, parent):
        super().__init__(parent)
        self.setBackgroundBrush(QBrush(QColor("#0f172a")))
        self.phases = []
        
        # Pen for drawing main connecting lines
        self.main_pen = QPen(QColor("#475569"), 4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
        self.detour_pen = QPen(QColor("#a78bfa"), 2, Qt.PenStyle.SolidLine)
        
    def add_phase(self, phase: PhaseElement):
        self.phases.append(phase)
        
    def drawForeground(self, painter, rect):
        """Draws the dynamic floating elastic lines."""
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        for i, phase in enumerate(self.phases):
            mx = phase.main_proxy.x()
            my = phase.main_proxy.y()
            mw = phase.main_proxy.size().width()
            mh = phase.main_proxy.size().height()
            
            # 1. Draw Main Line to next node
            if i < len(self.phases) - 1:
                next_phase = self.phases[i+1]
                nx = next_phase.main_proxy.x()
                
                painter.setPen(self.main_pen)
                start_pt = QPointF(mx + mw, my + mh / 2)
                end_pt = QPointF(nx, my + mh / 2)
                painter.drawLine(start_pt, end_pt)
                
                # Draw Arrowhead
                arrow_size = 8
                arrow_head = QPolygonF([
                    end_pt,
                    QPointF(end_pt.x() - arrow_size, end_pt.y() - arrow_size / 2),
                    QPointF(end_pt.x() - arrow_size, end_pt.y() + arrow_size / 2)
                ])
                painter.setBrush(QBrush(QColor("#475569")))
                painter.setPen(Qt.PenStyle.NoPen)
                painter.drawPolygon(arrow_head)
                
            # 2. Draw Detour Line if expanded
            if phase.is_expanded and phase.sub_proxy.opacity() > 0.1:
                sx = phase.sub_proxy.x()
                sy = phase.sub_proxy.y()
                sw = phase.sub_proxy.size().width()
                
                painter.setPen(self.detour_pen)
                painter.setBrush(Qt.BrushStyle.NoBrush)
                
                path = QPainterPath()
                # From bottom of main node
                start_detour = QPointF(mx + 30, my + mh) 
                path.moveTo(start_detour)
                # Down to sub box
                path.lineTo(mx + 30, sy)
                # Across sub box top
                path.lineTo(sx + sw - 30, sy)
                # Back up to main node right side
                path.lineTo(mx + mw - 20, my + mh)
                
                painter.drawPath(path)

class ConversionFlowViewer(QGraphicsView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.scene_obj = DynamicTimelineScene(self)
        self.setScene(self.scene_obj)
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        self.setFixedHeight(300) 
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        
        self.build_pipeline()
        
        # Animation Engine
        self.anim = QVariantAnimation()
        self.anim.setDuration(400) # 400ms smooth float
        self.anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.anim.valueChanged.connect(self.animate_step)
        
        # Start initial layout calculation
        QTimer.singleShot(100, self.trigger_layout_animation)

    def build_pipeline(self):
        """Builds out the Data Nodes."""
        p1 = PhaseElement(self.scene_obj, "1. Ingestion", [
            SubNode("User Input", "Appends to conversion.txt"), "→",
            SubNode("Queue Management", "DB marks PENDING")
        ])
        
        p2 = PhaseElement(self.scene_obj, "2. Worker Init", [
            SubNode("Job Dequeue", "Marks PROCESSING"), "→",
            SubNode("Path Validation", "Rejects /share/seeding", "#f87171")
        ])
        
        p3 = PhaseElement(self.scene_obj, "3. Type Detection", [
            SubNode("Media Router", "Checks base path root", "#fbbf24"), "→",
            SubNode("Matching", "base_movies_root\nbase_tvseries_root")
        ])
        
        p4 = PhaseElement(self.scene_obj, "4. Target Check", [
            SubNode("MP4 Existence", "Does target file exist?", "#fbbf24"), "→",
            SubNode("NOT EXISTS", "Proceed to pipeline", "#34d399")
        ])
        
        p5 = PhaseElement(self.scene_obj, "5. Subtitles", [
            SubNode("Discovery", "External or Embedded"), "→",
            SubNode("Processing", "Force UTF-8\nReplace RO chars")
        ])
        
        p6 = PhaseElement(self.scene_obj, "6. Encoding", [
            SubNode("Heuristics & Audio", "Load DB / Downmix AAC"), "→",
            SubNode("Tiered HW Loop", "Tier 1 → Tier 2 → Tier 3", "#fbbf24"), "→",
            SubNode("Outcome Handler", "Save to DB / Abort")
        ])
        
        p7 = PhaseElement(self.scene_obj, "7. Finalization", [
            SubNode("File Relocation", "Move to Target Dir"), "→",
            SubNode("Source Cleanup", "Delete original source"), "→",
            SubNode("Job Complete", "Mark COMPLETED", "#34d399")
        ])
        
        for p in [p1, p2, p3, p4, p5, p6, p7]:
            self.scene_obj.add_phase(p)

    def trigger_layout_animation(self):
        """Calculates where everything SHOULD be, then starts the animation."""
        x_cursor = 50.0
        self.start_positions = {}
        self.target_positions = {}
        self.start_opacities = {}
        self.target_opacities = {}
        
        y_main = 100.0
        y_sub = 200.0
        
        for phase in self.scene_obj.phases:
            # Record start state
            self.start_positions[phase] = (phase.main_proxy.x(), phase.sub_proxy.y())
            self.start_opacities[phase] = phase.sub_proxy.opacity()
            
            # Calculate target X
            w_main = phase.main_width()
            
            # Align logic
            target_main_x = x_cursor
            target_sub_x = x_cursor
            
            # Calculate expansion width needed
            block_width = w_main
            if phase.is_expanded:
                phase.sub_proxy.setVisible(True)
                block_width = max(w_main, phase.sub_width())
                # Center sub proxy under main proxy if it's smaller, else center main over sub
                if phase.sub_width() > w_main:
                    target_main_x = x_cursor + (phase.sub_width() - w_main) / 2
                else:
                    target_sub_x = x_cursor + (w_main - phase.sub_width()) / 2
                    
            self.target_positions[phase] = {
                'mx': target_main_x, 'my': y_main,
                'sx': target_sub_x, 'sy': y_sub if phase.is_expanded else y_main + 20
            }
            self.target_opacities[phase] = 1.0 if phase.is_expanded else 0.0
            
            x_cursor += block_width + 80.0 # Spacing

        # Adjust Scene Rect
        self.scene_obj.setSceneRect(0, 0, x_cursor + 100, 400)
        
        # Fire animation
        self.anim.stop()
        self.anim.setStartValue(0.0)
        self.anim.setEndValue(1.0)
        self.anim.start()

    def animate_step(self, progress):
        """Interpolates between start and target dynamically."""
        for phase in self.scene_obj.phases:
            t_data = self.target_positions[phase]
            start_mx, start_sy = self.start_positions[phase]
            
            # Interpolate Positions
            cur_mx = start_mx + (t_data['mx'] - start_mx) * progress
            cur_sy = start_sy + (t_data['sy'] - start_sy) * progress
            
            phase.main_proxy.setPos(cur_mx, t_data['my'])
            phase.sub_proxy.setPos(t_data['sx'], cur_sy)
            
            # Interpolate Opacity
            start_op = self.start_opacities[phase]
            t_op = self.target_opacities[phase]
            cur_op = start_op + (t_op - start_op) * progress
            phase.sub_proxy.setOpacity(cur_op)
            
            if progress == 1.0 and t_op == 0.0:
                phase.sub_proxy.setVisible(False)
                
        self.scene_obj.update() # Force redraw of dynamic floating lines
