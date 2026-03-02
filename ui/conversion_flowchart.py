from PyQt6.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsPathItem, QGraphicsTextItem
from PyQt6.QtGui import QPainter, QColor, QPen, QBrush, QFont, QPainterPath
from PyQt6.QtCore import Qt, QPointF

class FlowNode(QGraphicsPathItem):
    """Main backbone node (Rounded Rectangle)."""
    def __init__(self, x, y, width, height, text, solid=False):
        super().__init__()
        
        # Draw rounded rectangle
        path = QPainterPath()
        path.addRoundedRect(0, 0, width, height, 6, 6)
        self.setPath(path)
        
        # Center vertically on the Y axis
        self.setPos(x, y - height / 2)
        
        # Styling
        self.setPen(QPen(QColor("#2c3ed8"), 2)) # Blue border
        if solid:
            self.setBrush(QBrush(QColor("#2c3ed8")))
            text_color = QColor("#ffffff")
        else:
            self.setBrush(QBrush(QColor("#ffffff")))
            text_color = QColor("#000000")

        # Text Setup
        t = QGraphicsTextItem(text, self)
        t.setFont(QFont("Arial", 10, QFont.Weight.Bold if solid else QFont.Weight.Normal))
        t.setDefaultTextColor(text_color)
        r = t.boundingRect()
        t.setPos((width - r.width()) / 2, (height - r.height()) / 2)
        
        # Ports for connections (absolute coordinates)
        self.right_port = QPointF(x + width, y)
        self.left_port = QPointF(x, y)

class TextNode(QGraphicsTextItem):
    """Detail branch node (Text only, like the XMind image)."""
    def __init__(self, x, y, text):
        super().__init__(text)
        self.setFont(QFont("Arial", 9))
        self.setDefaultTextColor(QColor("#000000"))
        
        # Center vertically on the Y axis
        r = self.boundingRect()
        self.setPos(x, y - r.height() / 2)
        
        # Ports for connections
        self.right_port = QPointF(x + r.width(), y)
        self.left_port = QPointF(x, y)

class Connector(QGraphicsPathItem):
    """Draws lines between nodes."""
    def __init__(self, start_pt, end_pt, style="straight"):
        super().__init__()
        pen = QPen(QColor("#2c3ed8"), 2)
        self.setPen(pen)
        
        path = QPainterPath()
        path.moveTo(start_pt)
        
        if style == "straight":
            path.lineTo(end_pt)
        elif style == "tree":
            # Draws a horizontal line out, then vertical, then horizontal into the target
            mid_x = start_pt.x() + 20
            path.lineTo(mid_x, start_pt.y())
            path.lineTo(mid_x, end_pt.y())
            path.lineTo(end_pt)
            
        self.setPath(path)

class ConversionFlowViewer(QGraphicsView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.scene_obj = QGraphicsScene()
        self.scene_obj.setBackgroundBrush(QBrush(QColor("#ffffff")))
        self.setScene(self.scene_obj)
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        self.setFixedHeight(300) 
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        
        self.draw_chart()

    def draw_chart(self):
        # Y-Axis center line for the main backbone
        y_main = 400
        nodes = []
        conns = []

        # ==========================================
        # 1. MAIN BACKBONE NODES
        # ==========================================
        n_ingest = FlowNode(50, y_main, 150, 40, "Ingest item path", solid=True)
        n_check_sub = FlowNode(350, y_main, 140, 40, "Check subtitle")
        n_movie_start = FlowNode(900, y_main, 180, 40, "Movie conversion started")
        n_movie_fin = FlowNode(1550, y_main, 180, 40, "Movie conversion finished")
        n_moved = FlowNode(1850, y_main, 140, 40, "Files are moved")

        nodes.extend([n_ingest, n_check_sub, n_movie_start, n_movie_fin, n_moved])

        # Backbone Connectors
        conns.append(Connector(n_ingest.right_port, n_check_sub.left_port, "straight"))
        conns.append(Connector(n_check_sub.right_port, n_movie_start.left_port, "straight"))
        conns.append(Connector(n_movie_start.right_port, n_movie_fin.left_port, "straight"))
        conns.append(Connector(n_movie_fin.right_port, n_moved.left_port, "straight"))

        # ==========================================
        # 2. INGEST DETAILS (Branching from Ingest)
        # ==========================================
        # Top
        i_appended = TextNode(230, 320, "Path appended to /share")
        i_pending = TextNode(230, 360, "DB Monitor -> PENDING")
        # Bottom
        i_dequeued = TextNode(230, 440, "Worker dequeues -> PROCESSING")
        i_valid = TextNode(230, 480, "Domain resolved & Validated")
        
        nodes.extend([i_appended, i_pending, i_dequeued, i_valid])
        for n in [i_appended, i_pending, i_dequeued, i_valid]:
            conns.append(Connector(n_ingest.right_port, n.left_port, "tree"))

        # ==========================================
        # 3. SUBTITLE DETAILS (Branching from Check Subtitle)
        # ==========================================
        # TOP BRANCH: Subtitle Exists
        st_exists = TextNode(520, 250, "Subtitle exists")
        st_conv = TextNode(640, 250, "Converted to srt/UTF-8")
        st_ro = TextNode(810, 220, "Ro language is found")
        st_rep = TextNode(960, 220, "Characters are replaced")
        st_en = TextNode(810, 280, "En language is found")
        
        conns.append(Connector(n_check_sub.right_port, st_exists.left_port, "tree"))
        conns.append(Connector(st_exists.right_port, st_conv.left_port, "straight"))
        conns.append(Connector(st_conv.right_port, st_ro.left_port, "tree"))
        conns.append(Connector(st_ro.right_port, st_rep.left_port, "straight"))
        conns.append(Connector(st_conv.right_port, st_en.left_port, "tree"))

        # BOTTOM BRANCH: Subtitle Extracted
        sb_ext = TextNode(520, 550, "Subtitle is extracted")
        sb_conv = TextNode(660, 550, "Converted to srt/UTF-8")
        sb_ro = TextNode(830, 520, "Ro language is found")
        sb_rep = TextNode(980, 520, "Characters are replaced")
        sb_en = TextNode(830, 580, "En language is found")
        
        conns.append(Connector(n_check_sub.right_port, sb_ext.left_port, "tree"))
        conns.append(Connector(sb_ext.right_port, sb_conv.left_port, "straight"))
        conns.append(Connector(sb_conv.right_port, sb_ro.left_port, "tree"))
        conns.append(Connector(sb_ro.right_port, sb_rep.left_port, "straight"))
        conns.append(Connector(sb_conv.right_port, sb_en.left_port, "tree"))
        
        nodes.extend([st_exists, st_conv, st_ro, st_rep, st_en, sb_ext, sb_conv, sb_ro, sb_rep, sb_en])

        # ==========================================
        # 4. MOVIE DETAILS (Branching from Movie Start)
        # ==========================================
        # TOP BRANCH: Hardware Encoding
        mt_heur = TextNode(1110, 250, "Check DB for HW Heuristics")
        mt_qsv = TextNode(1300, 250, "Intel QSV Encode (HEVC)")
        mt_mix = TextNode(1480, 250, "Audio Downmixed to AAC")
        
        conns.append(Connector(n_movie_start.right_port, mt_heur.left_port, "tree"))
        conns.append(Connector(mt_heur.right_port, mt_qsv.left_port, "straight"))
        conns.append(Connector(mt_qsv.right_port, mt_mix.left_port, "straight"))

        # BOTTOM BRANCH: Fallback / VRAM Error
        mb_err = TextNode(1110, 550, "VRAM Exhaustion Detected")
        mb_down = TextNode(1300, 550, "Downgrade HW Tier (bf/lad)")
        mb_retry = TextNode(1490, 550, "Retry Encode Loop")
        
        conns.append(Connector(n_movie_start.right_port, mb_err.left_port, "tree"))
        conns.append(Connector(mb_err.right_port, mb_down.left_port, "straight"))
        conns.append(Connector(mb_down.right_port, mb_retry.left_port, "straight"))

        nodes.extend([mt_heur, mt_qsv, mt_mix, mb_err, mb_down, mb_retry])

        # ==========================================
        # RENDER TO SCENE
        # ==========================================
        for c in conns:
            self.scene_obj.addItem(c)
        for n in nodes:
            self.scene_obj.addItem(n)
