import os
import sys
import math
import bisect
import simulacion as sim
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QHeaderView, QTableView, QAbstractItemView,
    QFrame, QWidget, QSizePolicy, QVBoxLayout, QHBoxLayout, QLabel
)
from PyQt5.QtCore import (
    Qt, QSize, QRect, QObject, QThread, pyqtSignal, QAbstractTableModel
)
from PyQt5.QtGui import QColor, QPainter
from PyQt5 import uic

# ── Constantes ────────────────────────────────────────────────────────────────
N_FROZEN = 3        # columnas siempre visibles a la izquierda: #, Reloj, Evento

# ── Columnas estáticas ────────────────────────────────────────────────────────
COLS = [
    ("num",      "#"),          ("reloj",  "Reloj"),       ("evento",   "Evento"),
    ("rnd_le",   "RND"),        ("t_le",   "T. Entrada"),  ("prox_emp", "Próx. Evento"),
    ("rnd_lt",   "RND"),        ("t_lt",   "T. Entrada"),  ("prox_tec", "Próx. Evento"),
    ("rnd_at",   "RND"),        ("t_at",   "T. Atención"),
    ("fin_at_1", "Fin At. 1"),  ("fin_at_2", "Fin At. 2"),
    ("fin_at_3", "Fin At. 3"),  ("fin_at_4", "Fin At. 4"),
    ("rnd_mt",   "RND"),        ("t_mt",   "T. Mantenim."), ("fin_mant", "Fin Mantenim."),
    ("t1_est",   "Estado"),     ("t1_pend", "Pendiente"),
    ("t2_est",   "Estado"),     ("t2_pend", "Pendiente"),
    ("t3_est",   "Estado"),     ("t3_pend", "Pendiente"),
    ("t4_est",   "Estado"),     ("t4_pend", "Pendiente"),
    ("cola",     "Cola"),
    ("tec_est",  "Estado"),     ("tec_term", "Terminal"),
    ("n_lleg",     "Llegadas"),    ("n_rt",  "Se van"),         ("pct_se_van", "% se van"),
    ("acum_esp",   "Acum. espera"), ("n_esp", "Cnt. espera"),   ("prom_esp",   "Prom. espera"),
]

BASE_GROUPS = [
    ("",                  "#1e1e2e", "#cdd6f4", 3),
    ("Llegada Empleado",  "#a6e3a1", "#1e1e2e", 3),
    ("Llegada Técnico",   "#f9e2af", "#1e1e2e", 3),
    ("Fin Atención",      "#fab387", "#1e1e2e", 6),
    ("Fin Mantenimiento", "#f38ba8", "#1e1e2e", 3),
    ("Terminal 1",        "#89dceb", "#1e1e2e", 2),
    ("Terminal 2",        "#89dceb", "#1e1e2e", 2),
    ("Terminal 3",        "#89dceb", "#1e1e2e", 2),
    ("Terminal 4",        "#89dceb", "#1e1e2e", 2),
    ("Cola",              "#b4befe", "#1e1e2e", 1),
    ("Técnico",           "#cba6f7", "#1e1e2e", 2),
    ("Estadísticas",      "#89b4fa", "#1e1e2e", 6),
]

STAT_DEFS = [
    ("total_llegaron",    "Total llegaron"),
    ("total_atendidos",   "Atendidos"),
    ("total_rt",          "Se fueron (RT)"),
    ("pct_rt",            "% que se van"),
    ("prom_espera",       "Prom. espera (min)"),
    ("total_iteraciones", "Iteraciones"),
    ("tiempo_simulado",   "Tiempo simulado (min)"),
]

TERM_COLOR  = {"Libre": "#89dceb", "Ocupada": "#fab387", "Siendo mantenida": "#f38ba8"}
TEC_COLOR   = {"Descansando": "#9399b2",
               "Esperando Terminal Libre": "#f9e2af",
               "Realizando Mantenimiento": "#f38ba8"}
EMP_COLOR   = {"SA": "#a6e3a1", "EA": "#f9e2af", "x": "#f38ba8"}
ESTADO_KEYS = {"t1_est", "t2_est", "t3_est", "t4_est", "tec_est"}

DARK = """
QMainWindow, QWidget          { background:#1e1e2e; color:#cdd6f4; }
QGroupBox                     { border:1px solid #45475a; border-radius:4px; margin-top:10px;
                                padding-top:4px; color:#9399b2; font-size:10px; letter-spacing:1px; }
QGroupBox::title              { subcontrol-origin:margin; left:8px; padding:0 4px; }
QLabel#lbl_titulo             { font-size:18px; font-weight:bold; color:#cba6f7; }
QLabel#lbl_subtitulo          { color:#9399b2; }
QLabel#lbl_info               { color:#a6e3a1; }
QLabel#lbl_filtro             { color:#a6e3a1; }
QLabel#lbl_ultima             { color:#9399b2; font-size:11px; font-weight:bold; margin-top:6px; }
QLineEdit                     { background:#313244; border:1px solid #45475a; border-radius:3px;
                                padding:4px 6px; color:#cdd6f4; max-width:80px; }
QLineEdit:focus               { border-color:#cba6f7; }
QPushButton                   { background:#cba6f7; color:#1e1e2e; border:none;
                                border-radius:4px; padding:6px 14px; font-weight:bold; }
QPushButton:hover             { background:#d4b5ff; }
QPushButton:pressed           { background:#b893e8; }
QPushButton:disabled          { background:#45475a; color:#6c7086; }
QProgressBar                  { background:#313244; border:1px solid #45475a;
                                border-radius:3px; height:14px; }
QProgressBar::chunk           { background:#cba6f7; border-radius:3px; }
QTableView                    { background:#181825; alternate-background-color:#1e1e2e;
                                gridline-color:#313244; color:#cdd6f4; border:none; font-size:11px; }
QTableView::item:selected     { background:#45475a; color:#cdd6f4; }
QScrollBar:horizontal         { background:#181825; height:14px; margin:0; border:none; }
QScrollBar:vertical           { background:#181825; width:14px;  margin:0; border:none; }
QScrollBar::handle:horizontal { background:#45475a; border-radius:3px; min-width:30px;  margin:2px; }
QScrollBar::handle:vertical   { background:#45475a; border-radius:3px; min-height:30px; margin:2px; }
QScrollBar::handle:hover      { background:#585b70; }
QScrollBar::add-line, QScrollBar::sub-line { width:0; height:0; background:none; border:none; }
QScrollBar::add-page, QScrollBar::sub-page { background:none; }
"""


def trunc2_str(v):
    return str(math.floor(v * 100 + 1e-9) / 100)


def col_width(key, header):
    if key == "evento":
        base = 210
    elif key == "tec_est":
        base = 200
    elif key in ESTADO_KEYS:
        base = 140
    elif "rnd" in key:
        base = 72
    else:
        base = 70
    return max(base, len(header) * 8 + 18)


# ── Modelo virtual ────────────────────────────────────────────────────────────
class SimModel(QAbstractTableModel):
    def __init__(self):
        super().__init__()
        self.rows   = []
        self._head  = []
        self._specs = []

    def set_content(self, rows, cols):
        self.beginResetModel()
        self.rows   = rows
        self._head  = [h for _, h in cols]
        self._specs = [self._spec(k) for k, _ in cols]
        self.endResetModel()

    def rowCount(self, parent=None):    return len(self.rows)
    def columnCount(self, parent=None): return len(self._specs)

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole \
                and 0 <= section < len(self._head):
            return self._head[section]
        return None

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        if role == Qt.DisplayRole:
            return self._text(self.rows[index.row()], index.column())
        if role == Qt.ForegroundRole:
            cmap = self._specs[index.column()][3]
            if cmap:
                c = cmap.get(self._text(self.rows[index.row()], index.column()))
                if c:
                    return QColor(c)
        return None

    def _spec(self, key):
        if key in ESTADO_KEYS and key.startswith("t") and key[1].isdigit():
            return ("termlist", "term_est",  int(key[1]) - 1, TERM_COLOR)
        if key.startswith("t") and key.endswith("_pend"):
            return ("termlist", "term_pend", int(key[1]) - 1, None)
        if key.startswith("fin_at_"):
            return ("termlist", "term_fin",  int(key[-1]) - 1, None)
        if key == "tec_est":
            return ("scalar",   "tec_est",   None, TEC_COLOR)
        if key == "pct_se_van":
            return ("pct",      None,        None, None)
        if key == "prom_esp":
            return ("prom",     None,        None, None)
        if key.startswith("emp"):
            col_str, field = key[3:].split("_", 1)
            return ("emp", int(col_str), field, EMP_COLOR if field == "estado" else None)
        return ("scalar", key, None, None)

    def _text(self, f, col):
        kind, a, b, _ = self._specs[col]
        if kind == "scalar":   return self._fmt(f.get(a))
        if kind == "termlist": return self._fmt(f[a][b])
        if kind == "pct":
            nl = f["n_lleg"]
            return self._fmt(f["n_rt"] / nl * 100 if nl else 0)
        if kind == "prom":
            ne = f["n_esp"]
            return self._fmt(f["acum_esp"] / ne if ne else 0)
        if kind == "emp":
            tup = f["emp"].get(a)
            if tup is None: return ""
            estado, hll, tid = tup
            fue = estado == "AT"
            if b == "estado": return "x" if fue else estado
            if b == "hora":   return "-" if fue else self._fmt(hll)
            return "-" if fue else self._fmt(tid)
        return ""

    @staticmethod
    def _fmt(v):
        if v is None:   return "-"
        if v is True:   return "SÍ"
        if v is False:  return "NO"
        if isinstance(v, float): return trunc2_str(v)
        return str(v)


# ── Encabezado agrupado de dos niveles ────────────────────────────────────────
class GroupedHeader(QHeaderView):
    ROW_H = 22

    def __init__(self, parent=None):
        super().__init__(Qt.Horizontal, parent)
        self._bounds = []
        self.setMinimumHeight(self.ROW_H * 2)

    def sizeHint(self):
        return QSize(super().sizeHint().width(), self.ROW_H * 2)

    def set_groups(self, groups):
        col, bounds = 0, []
        for name, bg, fg, span in groups:
            bounds.append((col, col + span - 1, name, bg, fg))
            col += span
        self._bounds = bounds
        self.viewport().update()

    def paintEvent(self, event):
        qp   = QPainter(self.viewport())
        h    = self.viewport().height()
        half = h // 2
        sep  = QColor("#45475a")
        n    = self.count()
        if n == 0:
            qp.end(); return

        vw    = self.viewport().width()
        first = max(0, self.logicalIndexAt(1))
        last  = self.logicalIndexAt(vw - 1)
        if last < 0: last = n - 1

        for gs, ge, name, bg, fg in self._bounds:
            if ge < first or gs > last: continue
            ge  = min(ge, n - 1)
            vis = [c for c in range(gs, ge + 1) if not self.isSectionHidden(c)]
            if not vis: continue

            for c in vis:
                x, w = self.sectionViewportPosition(c), self.sectionSize(c)
                txt  = self._htxt(c)
                if name:
                    r = QRect(x, half, w, h - half)
                    qp.fillRect(r, QColor("#313244"))
                    qp.setPen(QColor("#9399b2"))
                    f = self.font(); f.setBold(False); qp.setFont(f)
                else:
                    r = QRect(x, 0, w, h)
                    qp.fillRect(r, QColor("#313244"))
                    qp.setPen(QColor("#cdd6f4"))
                    f = self.font(); f.setBold(True); qp.setFont(f)
                qp.drawText(r.adjusted(2, 1, -2, -1), Qt.AlignCenter | Qt.TextSingleLine, txt)
                qp.setPen(sep)
                qp.drawLine(x + w - 1, r.top(), x + w - 1, h)

            if name:
                x0  = self.sectionViewportPosition(vis[0])
                x1  = self.sectionViewportPosition(vis[-1]) + self.sectionSize(vis[-1])
                top = QRect(x0, 0, x1 - x0, half)
                qp.fillRect(top, QColor(bg))
                qp.setPen(QColor(fg))
                f = self.font(); f.setBold(True); qp.setFont(f)
                qp.drawText(top.adjusted(2, 1, -2, -1), Qt.AlignCenter | Qt.TextSingleLine, name)
                qp.setPen(sep)
                qp.drawRect(top.adjusted(0, 0, -1, -1))
                qp.drawLine(x0, half, x1, half)   # divisor solo bajo grupos nombrados

        qp.end()

    def _htxt(self, c):
        m = self.model()
        return str(m.headerData(c, Qt.Horizontal, Qt.DisplayRole) or "") if m else ""


# ── Worker de simulación (hilo aparte) ───────────────────────────────────────
class SimWorker(QObject):
    finished = pyqtSignal()

    def __init__(self, params):
        super().__init__()
        self.p = params

    def run(self):
        p = self.p
        sim.MEDIA_LLEGADA_EMP    = p["media"]
        sim.MAX_COLA             = p["max_cola"]
        sim.ATN_MIN, sim.ATN_MAX   = p["atn_min"],  p["atn_max"]
        sim.MANT_MIN, sim.MANT_MAX = p["mant_min"], p["mant_max"]
        sim.TEC_MIN,  sim.TEC_MAX  = p["tec_min"],  p["tec_max"]
        sim.resetear_estado()
        sim.simular(p["tiempo_max"])
        self.finished.emit()


# ── Ventana principal ─────────────────────────────────────────────────────────
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        uic.loadUi(os.path.join(os.path.dirname(__file__), "main.ui"), self)
        self.todas_filas = []
        self._relojes    = []
        self._thread     = None
        self._worker     = None

        # ── Tabla principal (scrollable) ──────────────────────────────────
        self.model_vector = SimModel()
        self.tbl_vector.setModel(self.model_vector)
        self._header = GroupedHeader()
        self.tbl_vector.setHorizontalHeader(self._header)
        self._cfg_tbl(self.tbl_vector, alt=True)
        self.tbl_vector.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.tbl_vector.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.tbl_vector.setFrameShape(QFrame.NoFrame)  # mismo frame que el panel frozen

        # ── Panel frozen: #, Reloj, Evento (siempre visibles a la izquierda) ──
        self._frozen     = QTableView()
        self._frozen_hdr = GroupedHeader()
        self._frozen.setHorizontalHeader(self._frozen_hdr)
        self._frozen.setModel(self.model_vector)
        self._frozen.setSelectionModel(self.tbl_vector.selectionModel())  # selección compartida
        self._cfg_tbl(self._frozen, alt=True)
        # Scroll horizontal SIEMPRE visible (igual que la tabla principal): reserva
        # de forma nativa el mismo alto abajo. Así ambos viewports miden exactamente
        # igual y el rango de scroll vertical coincide → sin desfase al llegar al
        # final. (La barra del frozen queda inerte: sus 3 columnas entran justo.)
        self._frozen.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self._frozen.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._frozen.setFrameShape(QFrame.NoFrame)
        self._frozen.setFocusPolicy(Qt.NoFocus)
        # Sincronizar scroll vertical frozen ↔ main
        self.tbl_vector.verticalScrollBar().valueChanged.connect(
            self._frozen.verticalScrollBar().setValue
        )
        self._frozen.verticalScrollBar().valueChanged.connect(
            self.tbl_vector.verticalScrollBar().setValue
        )
        # Actualizar ancho del panel frozen cuando el usuario arrastra sus columnas
        self._frozen_hdr.sectionResized.connect(self._on_frozen_col_resized)

        # Reemplazar tbl_vector en el layout por un contenedor [frozen | main]
        vbl = self.centralWidget().layout()
        idx = vbl.indexOf(self.tbl_vector)
        vbl.takeAt(idx)                          # saca el ítem (no borra el widget)

        container = QWidget()
        container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        row = QHBoxLayout(container)
        row.setContentsMargins(4, 4, 4, 4)
        row.setSpacing(0)
        row.addWidget(self._frozen)              # columnas fijas a la izquierda
        row.addWidget(self.tbl_vector, 1)        # tabla scrollable se expande
        vbl.insertWidget(idx, container, 1)

        # ── Tabla de última fila ──────────────────────────────────────────
        self.model_ultima = SimModel()
        self.tbl_ultima.setModel(self.model_ultima)
        self._header_u = GroupedHeader()
        self.tbl_ultima.setHorizontalHeader(self._header_u)
        self._cfg_tbl(self.tbl_ultima, alt=False)
        self.tbl_ultima.setFixedHeight(96)
        self.tbl_ultima.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.tbl_ultima.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)

        # ── Tarjetas de estadísticas ──────────────────────────────────────
        self._stat_labels = {}
        layout_stats = QHBoxLayout(self.pnl_stats)
        layout_stats.setContentsMargins(0, 8, 0, 8)
        layout_stats.setSpacing(10)
        for key, nombre in STAT_DEFS:
            card = QFrame()
            card.setStyleSheet(
                "background:#181825; border:1px solid #45475a; border-radius:6px;"
            )
            vl = QVBoxLayout(card)
            vl.setContentsMargins(12, 12, 12, 12)
            vl.setSpacing(4)
            lbl_n = QLabel(nombre)
            lbl_n.setStyleSheet(
                "color:#6c7086; font-size:10px; border:none; background:transparent;"
            )
            lbl_v = QLabel("—")
            lbl_v.setStyleSheet(
                "color:#cba6f7; font-size:16px; font-weight:bold;"
                " border:none; background:transparent;"
            )
            vl.addWidget(lbl_n)
            vl.addWidget(lbl_v)
            layout_stats.addWidget(card)
            self._stat_labels[key] = lbl_v

        # ── Señales ───────────────────────────────────────────────────────
        self.btn_simular.clicked.connect(self.on_simular)
        self.btn_copiar.clicked.connect(self.on_copiar)
        self.txt_hora_desde.textChanged.connect(self.update_table)
        self.txt_cant_filas.textChanged.connect(self.update_table)

    # ── Configuración común de tablas ─────────────────────────────────────────
    def _cfg_tbl(self, tbl, alt):
        tbl.setAlternatingRowColors(alt)
        tbl.verticalHeader().setVisible(False)
        tbl.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        tbl.setSelectionBehavior(QAbstractItemView.SelectRows)
        tbl.setSelectionMode(QAbstractItemView.SingleSelection)

    # ── Lectura de inputs ─────────────────────────────────────────────────────
    def _valf(self, w, d):
        try:    return float(w.text().strip()) if w.text().strip() else d
        except: return d

    def _vali(self, w, d):
        try:    return int(float(w.text().strip())) if w.text().strip() else d
        except: return d

    # ── Anchos mínimos ────────────────────────────────────────────────────────
    def _apply_widths(self, tbl, cols):
        tbl.setUpdatesEnabled(False)
        for c, (key, hdr) in enumerate(cols):
            tbl.setColumnWidth(c, col_width(key, hdr))
        tbl.setUpdatesEnabled(True)

    # ── Sincronizar panel frozen con tabla principal ───────────────────────────
    def _sync_frozen(self, cols):
        """
        - Panel frozen: muestra solo las N_FROZEN primeras columnas.
        - Tabla principal: oculta esas N_FROZEN primeras para evitar duplicación.
        - Ajusta el ancho fijo del panel según las columnas visibles.

        La igualación de alto (para que el scroll vertical no se desfase al final)
        la da la reserva nativa del scroll horizontal en ambas tablas (ver __init__),
        no un margen calculado.
        """
        ncols = self.model_vector.columnCount()
        for c in range(ncols):
            self._frozen.setColumnHidden(c, c >= N_FROZEN)
            self.tbl_vector.setColumnHidden(c, c < N_FROZEN)

        self._frozen_hdr.set_groups([("", "#1e1e2e", "#cdd6f4", N_FROZEN)])
        self._apply_widths(self._frozen, cols[:N_FROZEN])

        fw = sum(self._frozen.columnWidth(c) for c in range(N_FROZEN))
        self._frozen.setFixedWidth(fw)

    def _on_frozen_col_resized(self, _logical, _old, _new):
        """Actualiza el ancho del panel frozen cuando el usuario arrastra una columna."""
        fw = sum(self._frozen.columnWidth(c) for c in range(N_FROZEN))
        self._frozen.setFixedWidth(fw)

    # ── Simular (hilo aparte) ─────────────────────────────────────────────────
    def on_simular(self):
        if self._thread and self._thread.isRunning():
            return

        # ── Validación de campos inválidos (texto no convertible a número) ──
        campos = [
            (self.txt_media_llegada, "Media llegada"),
            (self.txt_max_cola,      "Máx. en cola"),
            (self.txt_atn_min,       "Atención mín"),
            (self.txt_atn_max,       "Atención máx"),
            (self.txt_mant_min,      "Mantenimiento mín"),
            (self.txt_mant_max,      "Mantenimiento máx"),
            (self.txt_tec_min,       "Técnico mín"),
            (self.txt_tec_max,       "Técnico máx"),
            (self.txt_tiempo_max,    "Tiempo máximo"),
        ]
        errores = []
        for widget, nombre in campos:
            txt = widget.text().strip()
            if txt:
                try:
                    float(txt)
                except ValueError:
                    errores.append(f"{nombre} tiene un valor inválido: '{txt}'")
        if errores:
            self.lbl_info.setStyleSheet("color:#f38ba8;")
            self.lbl_info.setText("⚠  " + "   ·   ".join(errores))
            return

        params = {
            "media":      self._valf(self.txt_media_llegada, 2.0),
            "max_cola":   self._vali(self.txt_max_cola,       5),
            "atn_min":    self._valf(self.txt_atn_min,        5.0),
            "atn_max":    self._valf(self.txt_atn_max,        8.0),
            "mant_min":   self._valf(self.txt_mant_min,       3.0),
            "mant_max":   self._valf(self.txt_mant_max,       10.0),
            "tec_min":    self._valf(self.txt_tec_min,        57.0),
            "tec_max":    self._valf(self.txt_tec_max,        63.0),
            "tiempo_max": self._valf(self.txt_tiempo_max,     480.0),
        }

        # ── Validación de parámetros ──────────────────────────────────────
        errores = []
        if params["media"] <= 0:
            errores.append("La media de llegadas debe ser mayor a 0")
        if params["tiempo_max"] <= 0:
            errores.append("El tiempo máximo debe ser mayor a 0")
        if params["max_cola"] < 0:
            errores.append("El máximo en cola no puede ser negativo")
        if params["atn_max"] <= params["atn_min"]:
            errores.append("Atención: el máx debe ser mayor al mín")
        if params["mant_max"] <= params["mant_min"]:
            errores.append("Mantenimiento: el máx debe ser mayor al mín")
        if params["tec_max"] <= params["tec_min"]:
            errores.append("Técnico: el máx debe ser mayor al mín")
        if errores:
            self.lbl_info.setStyleSheet("color:#f38ba8;")
            self.lbl_info.setText("⚠  " + "   ·   ".join(errores))
            return

        self.btn_simular.setEnabled(False)
        self.prg_sim.setVisible(True)
        self.lbl_info.setStyleSheet("color:#a6e3a1;")       # verde (restaura si venía de error)
        self.lbl_info.setText("⏳ Simulando…")

        self._thread = QThread()
        self._worker = SimWorker(params)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._on_sim_done)
        self._worker.finished.connect(self._thread.quit)
        self._thread.finished.connect(self._on_thread_done)
        self._thread.start()

    def _on_sim_done(self):
        self.todas_filas = sim.vector_estado
        self._relojes    = [f["reloj"] for f in self.todas_filas]

        self.btn_simular.setEnabled(True)
        self.prg_sim.setVisible(False)

        n = len(self.todas_filas)
        self.lbl_info.setText(
            f"{n} filas  ·  t={trunc2_str(sim.reloj)} min  ·  {sim.iteracion} iter"
        )
        last = self.todas_filas[-1] if self.todas_filas else {}
        na, nrt, nl, ne, acum = (last.get(k, 0) for k in ("n_at", "n_rt", "n_lleg", "n_esp", "acum_esp"))
        stats = {
            "total_llegaron":    nl,          # contador_llegaron: exacto por definición
            "total_atendidos":   na,
            "total_rt":          nrt,
            "pct_rt":            round(nrt / nl * 100, 2) if nl else 0,
            "prom_espera":       round(acum / ne, 3)     if ne else 0,
            "total_iteraciones": sim.iteracion,
            "tiempo_simulado":   round(sim.reloj, 2),
        }
        for key, lbl in self._stat_labels.items():
            lbl.setText(str(stats.get(key, "—")))

        self._fill_ultima()
        self.update_table()

    def _on_thread_done(self):
        if self._worker: self._worker.deleteLater()
        if self._thread: self._thread.deleteLater()
        self._worker = self._thread = None

    # ── Última fila ───────────────────────────────────────────────────────────
    def _fill_ultima(self):
        if not self.todas_filas:
            return
        last = self.todas_filas[-1]
        self.lbl_ultima.setText(
            f"Última fila — #{last['num']},  t={trunc2_str(last['reloj'])} min"
        )
        self.model_ultima.set_content([last], COLS)
        self._header_u.set_groups(BASE_GROUPS)
        self._apply_widths(self.tbl_ultima, COLS)

    # ── Filtrado j/i (bisect, instantáneo) ────────────────────────────────────
    def update_table(self):
        if not self.todas_filas:
            return
        j = self._valf(self.txt_hora_desde, 0.0)
        i = self._vali(self.txt_cant_filas,  20)

        start = bisect.bisect_left(self._relojes, j)
        filas = self.todas_filas[start : start + i] if i > 0 else self.todas_filas[start:]

        emp_ids = sorted({
            c for f in filas
            for c, tup in f["emp"].items()
            if tup[0] in ("EA", "SA", "AT")
        })
        emp_cols   = [(f"emp{c}_{fld}", h)
                      for c in emp_ids
                      for fld, h in (("estado", "Estado"),
                                     ("hora",   "Hora inicio espera"),
                                     ("term",   "Terminal"))]
        emp_groups = [(f"Empleado {c}", "#cba6f7", "#1e1e2e", 3) for c in emp_ids]

        cols = COLS + emp_cols
        self.model_vector.set_content(filas, cols)
        self._header.set_groups(BASE_GROUPS + emp_groups)
        self._apply_widths(self.tbl_vector, cols)

        # Sincronizar panel frozen (ocultar columnas duplicadas, ajustar ancho)
        self._sync_frozen(cols)

        self.lbl_filtro.setText(
            f"mostrando {len(filas)} de {len(self.todas_filas)} desde t={trunc2_str(j)}"
        )

    # ── Copiar a Excel (TSV, todas las filas visibles + encabezados) ──────────
    def on_copiar(self):
        m    = self.model_vector
        ncol = m.columnCount()
        nrow = m.rowCount()
        # Fila de encabezados
        lines = ["\t".join(str(m.headerData(c, Qt.Horizontal) or "") for c in range(ncol))]
        # Filas de datos
        for r in range(nrow):
            lines.append(
                "\t".join(m.data(m.index(r, c), Qt.DisplayRole) or "" for c in range(ncol))
            )
        QApplication.clipboard().setText("\n".join(lines))


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyleSheet(DARK)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
