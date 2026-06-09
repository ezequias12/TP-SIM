from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Preformatted,
    HRFlowable, KeepTogether
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER

OUTPUT = "explicacion_main.pdf"

doc = SimpleDocTemplate(
    OUTPUT,
    pagesize=A4,
    leftMargin=2.5*cm, rightMargin=2.5*cm,
    topMargin=2.5*cm, bottomMargin=2.5*cm,
    title="Explicación main.py — TP Simulación",
    author="Grupo 22"
)

styles = getSampleStyleSheet()

titulo = ParagraphStyle("titulo",
    parent=styles["Title"],
    fontSize=22, spaceAfter=6, textColor=colors.HexColor("#4a4a8a"),
    alignment=TA_CENTER)

subtitulo = ParagraphStyle("subtitulo",
    parent=styles["Normal"],
    fontSize=11, spaceAfter=20, textColor=colors.HexColor("#666666"),
    alignment=TA_CENTER)

h1 = ParagraphStyle("h1",
    parent=styles["Heading1"],
    fontSize=15, spaceBefore=22, spaceAfter=6,
    textColor=colors.HexColor("#2c2c7a"))

h2 = ParagraphStyle("h2",
    parent=styles["Heading2"],
    fontSize=12, spaceBefore=14, spaceAfter=4,
    textColor=colors.HexColor("#444499"))

h3 = ParagraphStyle("h3",
    parent=styles["Heading3"],
    fontSize=11, spaceBefore=10, spaceAfter=3,
    textColor=colors.HexColor("#666633"))

body = ParagraphStyle("body",
    parent=styles["Normal"],
    fontSize=10, leading=15, spaceAfter=8)

code_style = ParagraphStyle("code",
    parent=styles["Code"],
    fontSize=8.5, leading=13, leftIndent=12,
    backColor=colors.HexColor("#f4f4f4"),
    borderColor=colors.HexColor("#cccccc"),
    borderWidth=0.5, borderPad=6,
    fontName="Courier", spaceAfter=8)

nota = ParagraphStyle("nota",
    parent=styles["Normal"],
    fontSize=9, leading=13, leftIndent=12,
    textColor=colors.HexColor("#555555"),
    backColor=colors.HexColor("#fffbe6"),
    borderColor=colors.HexColor("#e0c040"),
    borderWidth=0.5, borderPad=5,
    spaceAfter=8)

def P(text, style=body):
    return Paragraph(text, style)

def CODE(text):
    return Preformatted(text, code_style)

def HR():
    return HRFlowable(width="100%", thickness=0.5,
                      color=colors.HexColor("#cccccc"), spaceAfter=4)

def NOTA(text):
    return Paragraph(text, nota)

story = []

# ── Portada ───────────────────────────────────────────────────────────────────
story += [
    Spacer(1, 1.5*cm),
    P("Explicación de <b>main.py</b>", titulo),
    P("TP Simulación de Colas — Grupo 22<br/>Sistema de Registro Dactilar — Municipalidad de Río Cuarto", subtitulo),
    HR(),
    Spacer(1, 0.5*cm),
]

# ─────────────────────────────────────────────────────────────────────────────
# 1. VISIÓN GENERAL
# ─────────────────────────────────────────────────────────────────────────────
story += [
    P("1. Visión general de main.py", h1),
    P("""<b>main.py</b> es el archivo de interfaz gráfica de la aplicación. Su responsabilidad
    es mostrar los resultados que produce <b>simulacion.py</b> en una ventana de escritorio
    construida con <b>PyQt5</b>."""),
    P("El archivo se divide en seis bloques principales:"),
    P("""<b>1.</b> Constantes, definición de columnas y tema visual.<br/>
    <b>2.</b> <i>SimModel</i> — el modelo de datos virtual que alimenta la tabla.<br/>
    <b>3.</b> <i>GroupedHeader</i> — el encabezado de dos niveles dibujado a mano.<br/>
    <b>4.</b> <i>SimWorker</i> — el hilo aparte que corre la simulación sin congelar la UI.<br/>
    <b>5.</b> <i>MainWindow</i> — la ventana principal: carga el layout, conecta señales,
    filtra filas y muestra estadísticas.<br/>
    <b>6.</b> Helpers y métodos auxiliares."""),
    NOTA("No hay servidor web, no hay base de datos, no hay navegador. "
         "Todo corre en un único proceso de escritorio."),
]

# ─────────────────────────────────────────────────────────────────────────────
# 2. CONSTANTES Y ESTRUCTURA DE COLUMNAS
# ─────────────────────────────────────────────────────────────────────────────
story += [
    P("2. Constantes y estructura de columnas", h1),

    P("2.1 La lista COLS", h2),
    P("""<b>COLS</b> es la lista que define todas las columnas estáticas de la tabla,
    en orden. Cada elemento es una tupla <b>(clave, título)</b>: la clave es el nombre
    interno que usa el modelo para saber qué dato leer de cada fila, y el título es
    lo que se muestra en el encabezado."""),
    CODE(
'COLS = [\n'
'    ("num",      "#"),          ("reloj",  "Reloj"),       ("evento",   "Evento"),\n'
'    ("rnd_le",   "RND"),        ("t_le",   "T. Entrada"),  ("prox_emp", "Prox. Evento"),\n'
'    ("rnd_lt",   "RND"),        ("t_lt",   "T. Entrada"),  ("prox_tec", "Prox. Evento"),\n'
'    ("rnd_at",   "RND"),        ("t_at",   "T. Atencion"),\n'
'    ("fin_at_1", "Fin At. 1"),  ("fin_at_2", "Fin At. 2"),\n'
'    ("fin_at_3", "Fin At. 3"),  ("fin_at_4", "Fin At. 4"),\n'
'    ("rnd_mt",   "RND"),        ("t_mt",   "T. Mantenim."), ("fin_mant", "Fin Mantenim."),\n'
'    ("t1_est",   "Estado"),     ("t1_pend", "Pendiente"),\n'
'    ...  # terminales 2, 3, 4\n'
'    ("cola",     "Cola"),\n'
'    ("tec_est",  "Estado"),     ("tec_term", "Terminal"),\n'
'    ("n_lleg",   "Llegadas"),   ("n_rt",   "Se van"),     ("pct_se_van", "% se van"),\n'
'    ("acum_esp", "Acum. espera"), ("n_esp", "Cnt. espera"), ("prom_esp", "Prom. espera"),\n'
']'
    ),
    P("""Esta lista es la única fuente de verdad sobre qué columnas existen y en qué orden.
    Las columnas de empleados <b>no</b> están acá porque son dinámicas: se calculan en cada
    actualización de la tabla según qué empleados aparecen en las filas visibles."""),
    NOTA("Claves como 'fin_at_1' o 't2_est' son interpretadas por _spec para extraer "
         "el dato correcto del índice de la lista interna de terminales."),

    P("2.2 BASE_GROUPS — grupos del encabezado", h2),
    P("""Define los grupos de columnas para el encabezado de dos niveles: nombre del grupo,
    color de fondo, color de texto y cantidad de columnas que abarca. Por ejemplo,
    'Terminal 1' abarca 2 columnas (Estado y Pendiente) con fondo cyan."""),

    P("2.3 DARK — el tema visual", h2),
    P("""El tema visual de toda la aplicación se define en la constante <b>DARK</b>,
    una cadena de texto con estilos CSS que PyQt5 llama <i>stylesheet</i>. Se aplica
    una sola vez al iniciar la app:"""),
    CODE("app.setStyleSheet(DARK)"),
    P("""El tema usado es <b>Catppuccin Mocha</b>, una paleta oscura. Algunos de los
    colores principales:"""),
    P("""— Fondo de ventana y widgets: <b>#1e1e2e</b> (azul muy oscuro).<br/>
    — Fondo de tablas: <b>#181825</b> (aún más oscuro).<br/>
    — Texto principal: <b>#cdd6f4</b> (blanco lavanda).<br/>
    — Botón principal: <b>#cba6f7</b> (violeta).<br/>
    — Bordes y separadores: <b>#45475a</b> (gris medio)."""),
    NOTA("El stylesheet se aplica globalmente a toda la aplicación, por eso "
         "todos los widgets heredan el mismo tema sin necesidad de configurarlos uno por uno."),

    P("2.4 Diccionarios de colores por estado", h2),
    P("""Además del tema general, hay tres diccionarios que mapean estados
    a colores de texto para las celdas de la tabla:"""),
    CODE(
'TERM_COLOR = {"Libre": "#89dceb", "Ocupada": "#fab387", "Siendo mantenida": "#f38ba8"}\n'
'TEC_COLOR  = {"Descansando": "#9399b2",\n'
'              "Esperando Terminal Libre": "#f9e2af",\n'
'              "Realizando Mantenimiento": "#f38ba8"}\n'
'EMP_COLOR  = {"SA": "#a6e3a1", "EA": "#f9e2af", "x": "#f38ba8"}'
    ),
    P("""Cyan para libre, naranja para ocupada, rojo para en mantenimiento.
    Verde para siendo atendido, amarillo para esperando, rojo para el empleado que se va."""),
]

# ─────────────────────────────────────────────────────────────────────────────
# 3. CONEXIÓN CON main.ui
# ─────────────────────────────────────────────────────────────────────────────
story += [
    P("3. Conexión con main.ui", h1),
    P("""<b>main.ui</b> es un archivo XML generado con Qt Designer. Define la estructura
    visual de la ventana: qué widgets hay, cómo están ubicados y cómo se llaman.
    No contiene lógica de ningún tipo."""),
    P("<b>main.py</b> lo carga con una sola línea:"),
    CODE("uic.loadUi(os.path.join(os.path.dirname(__file__), 'main.ui'), self)"),
    P("""Esto crea automáticamente todos los widgets definidos en el .ui como
    atributos del objeto <i>self</i>. Si en el .ui hay un botón llamado
    <b>btn_simular</b>, después de cargar el archivo ese botón es accesible
    directamente como <b>self.btn_simular</b>."""),
    P("Los widgets principales accedidos desde el código son:"),
    P("""— <b>txt_media_llegada, txt_max_cola, txt_atn_min/max,
    txt_mant_min/max, txt_tec_min/max</b>: parámetros del sistema.<br/>
    — <b>txt_tiempo_max</b>: duración de la simulación en minutos.<br/>
    — <b>btn_simular</b>: arranca la simulación.<br/>
    — <b>btn_copiar</b>: copia los datos al portapapeles.<br/>
    — <b>prg_sim</b>: barra de progreso indeterminada durante la simulación.<br/>
    — <b>lbl_info</b>: muestra mensajes de estado, errores o resultados.<br/>
    — <b>tbl_vector</b>: tabla principal con todas las filas.<br/>
    — <b>tbl_ultima</b>: tabla de una sola fila (estado final).<br/>
    — <b>txt_hora_desde, txt_cant_filas</b>: filtros de visualización j e i.<br/>
    — <b>pnl_stats</b>: panel donde se crean las tarjetas de estadísticas en Python."""),
]

# ─────────────────────────────────────────────────────────────────────────────
# 4. CONEXIÓN CON simulacion.py
# ─────────────────────────────────────────────────────────────────────────────
story += [
    P("4. Conexión con simulacion.py", h1),
    P("<b>main.py</b> importa <b>simulacion.py</b> como un módulo normal:"),
    CODE("import simulacion as sim"),

    P("4.1 Configurar parámetros", h2),
    P("""Antes de simular, lee los campos de texto del usuario y sobrescribe las
    variables globales de <b>simulacion.py</b> directamente:"""),
    CODE(
"sim.MEDIA_LLEGADA_EMP    = p['media']\n"
"sim.MAX_COLA             = p['max_cola']\n"
"sim.ATN_MIN, sim.ATN_MAX   = p['atn_min'],  p['atn_max']\n"
"sim.MANT_MIN, sim.MANT_MAX = p['mant_min'], p['mant_max']\n"
"sim.TEC_MIN,  sim.TEC_MAX  = p['tec_min'],  p['tec_max']"
    ),

    P("4.2 Limpiar y simular", h2),
    P("""Llama a <b>resetear_estado()</b> para partir desde cero, y luego a
    <b>simular(tiempo_max)</b> que corre el loop de eventos y llena
    <b>sim.vector_estado</b> con todas las filas."""),
    CODE(
"sim.resetear_estado()\n"
"sim.simular(p['tiempo_max'])"
    ),

    P("4.3 Leer los resultados", h2),
    P("""Al terminar, lee <b>sim.vector_estado</b> (lista de dicts, uno por fila),
    <b>sim.reloj</b> (tiempo final) y <b>sim.iteracion</b> (eventos procesados):"""),
    CODE(
"self.todas_filas = sim.vector_estado\n"
"self._relojes    = [f['reloj'] for f in self.todas_filas]"
    ),
    P("""A partir de ese momento <b>main.py</b> trabaja solo con esos datos.
    No vuelve a llamar a <b>simulacion.py</b> hasta que el usuario presione
    <i>Simular</i> de nuevo."""),
]

# ─────────────────────────────────────────────────────────────────────────────
# 5. SimModel — MODELO VIRTUAL
# ─────────────────────────────────────────────────────────────────────────────
story += [
    P("5. SimModel — el modelo virtual de datos", h1),
    P("""PyQt5 separa los datos de la vista. La tabla (<i>QTableView</i>) no guarda
    datos; le pide al <b>modelo</b> qué mostrar en cada celda cuando lo necesita.
    Eso se llama <b>renderizado virtual</b>: aunque haya 100.000 filas, solo
    se renderizan las celdas visibles en pantalla en cada momento."""),
    P("""<b>SimModel</b> hereda de <i>QAbstractTableModel</i> e implementa
    el contrato mínimo que PyQt5 requiere:"""),
    CODE(
"def rowCount(self, parent=None):    return len(self.rows)\n"
"def columnCount(self, parent=None): return len(self._specs)\n"
"def headerData(...):   # devuelve el titulo de cada columna\n"
"def data(index, role): # devuelve el contenido y el color de cada celda"
    ),

    P("5.1 set_content — cargar datos", h2),
    P("""Cuando llegan datos nuevos, se llama a <b>set_content(rows, cols)</b>.
    Recibe la lista de filas y la lista de columnas (clave + título). Construye
    <b>self._specs</b>: una especificación por columna que describe cómo leer
    su valor."""),

    P("5.2 _spec — cómo interpretar cada columna", h2),
    P("""Analiza la clave de cada columna y devuelve una tupla que describe
    cómo extraer el valor. Los tipos posibles son:"""),
    P("""— <b>scalar</b>: columnas simples como <i>reloj</i>, <i>cola</i>, <i>tec_est</i>.
    Se lee directamente del dict de la fila con la clave dada.<br/>
    — <b>termlist</b>: columnas de terminales como <i>t1_est</i>, <i>fin_at_2</i>.
    Se lee de una lista interna de la fila usando el índice (número de terminal - 1).<br/>
    — <b>pct</b>: calcula el porcentaje de rechazados: n_rt / n_lleg * 100.<br/>
    — <b>prom</b>: calcula el promedio de espera: acum_esp / n_esp.<br/>
    — <b>emp</b>: columnas dinámicas de empleados. Extrae estado, hora de inicio
    de espera y terminal del empleado con ese ID."""),
    NOTA("pct y prom se calculan en el modelo, no en simulacion.py. "
         "simulacion.py solo guarda los valores crudos y el formateo queda del lado de la GUI."),

    P("5.3 _text — extraer y convertir el valor de una celda", h2),
    P("""Es el método que realmente obtiene el valor a mostrar usando la spec.
    El caso más importante es el de los empleados (<b>emp</b>):"""),
    CODE(
"if kind == 'emp':\n"
"    tup = f['emp'].get(a)         # busca al empleado por su ID\n"
"    if tup is None: return ''     # el empleado no existe en esta fila\n"
"    estado, hll, tid = tup\n"
"    fue = estado == 'AT'          # 'fue' = ya termino, se va\n"
"    if b == 'estado': return 'x' if fue else estado\n"
"    if b == 'hora':   return '-' if fue else self._fmt(hll)\n"
"    return '-' if fue else self._fmt(tid)"
    ),
    P("""Cuando el estado del empleado es <b>'AT'</b> (termino, se va), la columna
    Estado muestra <b>'x'</b> en lugar del estado interno, y las columnas de hora
    y terminal muestran <b>'-'</b> porque ya no tiene sentido mostrar esos datos.
    La 'x' es lo que se ve en rojo en la tabla."""),

    P("5.4 _fmt — formateo final de valores", h2),
    CODE(
"if v is None:              return '-'\n"
"if v is True:              return 'SI'\n"
"if v is False:             return 'NO'\n"
"if isinstance(v, float):   return trunc2_str(v)\n"
"return str(v)"
    ),
    P("""Los floats se truncan (no redondean) a 2 decimales con <b>trunc2_str</b>,
    que usa <i>math.floor</i> para garantizar truncado verdadero, tal como
    pide el enunciado. Los booleanos se muestran como SI/NO. Los None como guion."""),

    P("5.5 Colores de celdas", h2),
    P("""Cuando PyQt5 pide el color de una celda (rol <i>ForegroundRole</i>),
    el modelo obtiene el texto de esa celda y lo busca en el diccionario
    de colores correspondiente a su columna (TERM_COLOR, TEC_COLOR o EMP_COLOR).
    Si encuentra una entrada, devuelve ese color; si no, la celda queda
    con el color de texto por defecto."""),
]

# ─────────────────────────────────────────────────────────────────────────────
# 6. GroupedHeader
# ─────────────────────────────────────────────────────────────────────────────
story += [
    P("6. GroupedHeader — encabezado de dos niveles", h1),
    P("""El encabezado estándar de PyQt5 muestra una sola fila de títulos.
    Esta aplicación necesita dos filas: la superior con el nombre del grupo
    (coloreado) y la inferior con el título de cada columna individual."""),
    P("""<b>GroupedHeader</b> hereda de <i>QHeaderView</i> y sobreescribe
    <b>paintEvent</b>: dibuja a mano cada celda con un <i>QPainter</i> en lugar
    de usar el pintado estándar."""),

    P("6.1 set_groups — definir la estructura", h2),
    P("""Recibe una lista de tuplas (nombre, color_fondo, color_texto, cantidad_columnas)
    y las convierte en rangos (columna inicio, columna fin). El paintEvent usa esos
    rangos para saber qué segmento del encabezado pintar de qué color."""),

    P("6.2 paintEvent — el dibujado", h2),
    P("""Por cada grupo visible en pantalla, dibuja dos rectángulos:"""),
    P("""— <b>Fila inferior</b> (mitad de abajo): fondo gris oscuro, texto con el
    título individual de cada columna.<br/>
    — <b>Fila superior</b> (mitad de arriba): fondo del color del grupo, texto con
    el nombre del grupo centrado y en negrita."""),
    P("""Solo dibuja lo que está visible en el viewport, optimizando el rendimiento
    en tablas con muchas columnas."""),

    P("6.3 Columnas dinamicas de empleados", h2),
    P("""Las columnas de empleados se agregan al encabezado dinámicamente cada vez
    que se actualiza la tabla. <b>update_table</b> calcula qué empleados aparecen
    en las filas visibles y construye sus grupos:"""),
    CODE(
"emp_groups = [(f'Empleado {c}', '#cba6f7', '#1e1e2e', 3) for c in emp_ids]"
    ),
    P("""Cada empleado ocupa 3 columnas: Estado, Hora inicio espera y Terminal.
    Si en las filas visibles aparecen los empleados 3, 5 y 7, el encabezado
    mostrará tres grupos: Empleado 3, Empleado 5, Empleado 7."""),
]

# ─────────────────────────────────────────────────────────────────────────────
# 7. SimWorker — hilo aparte
# ─────────────────────────────────────────────────────────────────────────────
story += [
    P("7. SimWorker — simulacion en hilo aparte", h1),
    P("""Las interfaces gráficas en PyQt5 tienen un <b>hilo principal</b> que
    es el único que puede actualizar la UI. Si se corre una operación pesada
    (como 100.000 eventos) en ese hilo, la ventana se congela y no responde."""),
    P("""La simulación se corre en un <b>hilo separado</b> con <i>QThread</i>.
    <b>SimWorker</b> contiene la lógica a ejecutar en ese hilo:"""),
    CODE(
"class SimWorker(QObject):\n"
"    finished = pyqtSignal()\n\n"
"    def run(self):\n"
"        sim.MEDIA_LLEGADA_EMP = p['media']\n"
"        ...  # configura el resto de parametros\n"
"        sim.resetear_estado()\n"
"        sim.simular(p['tiempo_max'])\n"
"        self.finished.emit()   # avisa que termino"
    ),
    P("""La señal <b>finished</b> es el mecanismo de comunicación segura entre hilos
    en Qt. Cuando la simulación termina en el hilo secundario, emite esa señal,
    y el hilo principal la recibe para actualizar la UI sin condiciones de carrera."""),

    P("7.1 Ciclo de vida del hilo", h2),
    P("""<b>1.</b> El usuario presiona <i>Simular</i>.<br/>
    <b>2.</b> Se crean un <i>QThread</i> y un <i>SimWorker</i>.<br/>
    <b>3.</b> El worker se mueve al hilo nuevo con <i>moveToThread</i>.<br/>
    <b>4.</b> Al iniciarse el hilo, llama a <i>worker.run()</i>.<br/>
    <b>5.</b> Al terminar, emite <i>finished</i>, que dispara <i>_on_sim_done</i>
    y luego <i>thread.quit()</i>.<br/>
    <b>6.</b> Cuando el hilo para, <i>_on_thread_done</i> hace la limpieza:"""),
    CODE(
"def _on_thread_done(self):\n"
"    if self._worker: self._worker.deleteLater()\n"
"    if self._thread: self._thread.deleteLater()\n"
"    self._worker = self._thread = None"
    ),
    P("""<b>deleteLater</b> es el mecanismo de Qt para liberar objetos de forma
    segura cuando el hilo ya terminó. Poner ambos en None permite que
    Python los garbage-collecte y evita referencias colgadas."""),
    NOTA("Si el usuario presiona Simular mientras ya hay una simulacion corriendo, "
         "on_simular detecta que el hilo esta activo y no hace nada: "
         "if self._thread and self._thread.isRunning(): return"),
]

# ─────────────────────────────────────────────────────────────────────────────
# 8. on_simular — VALIDACIÓN Y ARRANQUE
# ─────────────────────────────────────────────────────────────────────────────
story += [
    P("8. on_simular — validacion y arranque", h1),
    P("""Es el método que se ejecuta cuando el usuario presiona el botón <i>Simular</i>.
    Tiene dos responsabilidades: validar los parámetros ingresados y, si todo está bien,
    lanzar la simulación en un hilo aparte."""),

    P("8.1 Lectura de parámetros con helpers", h2),
    P("""Los valores de los campos de texto se leen con dos helpers:"""),
    CODE(
"def _valf(self, w, d):\n"
"    try:    return float(w.text().strip()) if w.text().strip() else d\n"
"    except: return d\n\n"
"def _vali(self, w, d):\n"
"    try:    return int(float(w.text().strip())) if w.text().strip() else d\n"
"    except: return d"
    ),
    P("""<b>_valf</b> lee un float (con valor por defecto <i>d</i> si el campo está
    vacío o tiene texto inválido). <b>_vali</b> hace lo mismo pero convierte a entero.
    Ambos nunca tiran excepción hacia afuera: si el texto no es un número válido,
    devuelven el valor por defecto silenciosamente."""),

    P("8.2 Validacion de parámetros", h2),
    P("""Antes de simular, se validan las reglas de negocio y se acumulan los errores:"""),
    CODE(
"errores = []\n"
"if params['media'] <= 0:\n"
"    errores.append('La media de llegadas debe ser mayor a 0')\n"
"if params['atn_max'] <= params['atn_min']:\n"
"    errores.append('Atencion: el max debe ser mayor al min')\n"
"...  # otras validaciones\n\n"
"if errores:\n"
"    self.lbl_info.setStyleSheet('color:#f38ba8;')  # rojo\n"
"    self.lbl_info.setText('  ' + '   .   '.join(errores))\n"
"    return"
    ),
    P("""Si hay errores, se muestran todos juntos en <b>lbl_info</b> con texto rojo
    y la función termina sin simular. Si todo está bien, el label vuelve a verde
    y se lanza el hilo."""),
]

# ─────────────────────────────────────────────────────────────────────────────
# 9. PANEL FROZEN — COLUMNAS CONGELADAS
# ─────────────────────────────────────────────────────────────────────────────
story += [
    P("9. Panel de columnas congeladas", h1),
    P("""La tabla tiene muchas columnas y requiere scroll horizontal. Cuando el usuario
    hace scroll hacia la derecha, pierde de vista las columnas clave: #, Reloj y Evento."""),
    P("""La solución es usar <b>dos tablas</b> que comparten el mismo modelo:"""),
    P("""— <b>_frozen</b>: tabla secundaria a la izquierda, solo muestra las 3 primeras
    columnas, sin scroll horizontal.<br/>
    — <b>tbl_vector</b>: tabla principal a la derecha, oculta esas 3 primeras columnas
    y tiene scroll horizontal completo."""),
    P("""Ambas comparten modelo y modelo de selección, por lo que seleccionar una fila
    en una la selecciona en la otra. El scroll vertical está sincronizado en ambos sentidos:"""),
    CODE(
"self.tbl_vector.verticalScrollBar().valueChanged.connect(\n"
"    self._frozen.verticalScrollBar().setValue\n"
")\n"
"self._frozen.verticalScrollBar().valueChanged.connect(\n"
"    self.tbl_vector.verticalScrollBar().setValue\n"
")"
    ),
    P("""Las dos tablas se colocan lado a lado dentro de un contenedor con
    <i>QHBoxLayout</i>: _frozen a la izquierda con ancho fijo, tbl_vector
    a la derecha expandiéndose con el resto del espacio."""),
    P("""Si el usuario arrastra para cambiar el ancho de alguna de las 3 columnas
    congeladas, el método <b>_on_frozen_col_resized</b> recalcula y actualiza
    el ancho fijo del panel frozen."""),
]

# ─────────────────────────────────────────────────────────────────────────────
# 10. FILTRADO j/i
# ─────────────────────────────────────────────────────────────────────────────
story += [
    P("10. Filtrado por j e i — sin re-simular", h1),
    P("""Una vez que la simulación corrió, el usuario puede ajustar dos parámetros
    de visualización:"""),
    P("""— <b>j (hora desde)</b>: mostrar solo las filas a partir de ese minuto.<br/>
    — <b>i (cantidad de filas)</b>: cuántas filas mostrar a partir de j."""),
    P("""Cambiar estos valores <b>no vuelve a simular</b>. Solo filtra los datos
    ya calculados. Para hacer el filtrado rápido, al finalizar la simulación
    se guarda una lista con solo los valores de reloj:"""),
    CODE("self._relojes = [f['reloj'] for f in self.todas_filas]"),
    P("""Cuando el usuario cambia j, se usa <b>bisect_left</b> para encontrar
    la posición de la primera fila con reloj >= j en tiempo O(log n):"""),
    CODE(
"start = bisect.bisect_left(self._relojes, j)\n"
"filas = self.todas_filas[start : start + i]"
    ),
    NOTA("bisect_left es búsqueda binaria. Sobre 100.000 filas encuentra la posición "
         "correcta en unos 17 pasos en lugar de recorrer toda la lista."),
    P("""Después de filtrar, se recalculan las columnas dinámicas de empleados
    a partir de las filas visibles: solo aparecen los empleados que están
    presentes en ese rango."""),
]

# ─────────────────────────────────────────────────────────────────────────────
# 11. TABLA DE ÚLTIMA FILA Y ESTADÍSTICAS
# ─────────────────────────────────────────────────────────────────────────────
story += [
    P("11. Tabla de ultima fila y estadisticas", h1),

    P("11.1 Tabla de ultima fila", h2),
    P("""Debajo de la tabla principal hay una tabla de una sola fila que muestra
    el <b>estado final del sistema</b> al terminar la simulación. Usa el mismo
    <i>SimModel</i> cargado con solo la última fila:"""),
    CODE("self.model_ultima.set_content([last], COLS)"),
    P("""Altura fija de 96px y sin scroll vertical, para que siempre ocupe el mismo
    espacio en pantalla sin importar el contenido."""),

    P("11.2 Tarjetas de estadisticas", h2),
    P("""El panel de estadísticas muestra 7 métricas globales en tarjetas visuales
    creadas en Python (no en el .ui). Las métricas son:"""),
    P("""Total llegaron · Atendidos · Se fueron (RT) · % que se van ·
    Promedio de espera (min) · Iteraciones · Tiempo simulado (min)."""),
    P("""Los valores se calculan a partir de la última fila del vector y de las
    variables globales de <b>simulacion.py</b>:"""),
    CODE(
"na, nrt, nl, ne, acum = (last.get(k, 0) for k in\n"
"    ('n_at', 'n_rt', 'n_lleg', 'n_esp', 'acum_esp'))\n\n"
"stats = {\n"
"    'pct_rt':      round(nrt / nl * 100, 2) if nl else 0,\n"
"    'prom_espera': round(acum / ne, 3)       if ne else 0,\n"
"    ...\n"
"}"
    ),
]

# ─────────────────────────────────────────────────────────────────────────────
# 12. COPIAR A EXCEL
# ─────────────────────────────────────────────────────────────────────────────
story += [
    P("12. Copiar a Excel", h1),
    P("""El botón <i>Copiar</i> vuelca al portapapeles todas las filas visibles
    en formato <b>TSV</b> (valores separados por tabulaciones). Al pegarlo en
    Excel, cada valor queda en su celda correspondiente."""),
    CODE(
"lines = ['\\t'.join(str(m.headerData(c, Qt.Horizontal) or '') for c in range(ncol))]\n"
"for r in range(nrow):\n"
"    lines.append('\\t'.join(\n"
"        m.data(m.index(r, c), Qt.DisplayRole) or '' for c in range(ncol)))\n"
"QApplication.clipboard().setText('\\n'.join(lines))"
    ),
    P("""Primero agrega la fila de encabezados, luego recorre todas las filas
    y columnas del modelo leyendo exactamente el mismo texto que se ve en pantalla."""),
]

# ─────────────────────────────────────────────────────────────────────────────
# 13. FLUJO COMPLETO
# ─────────────────────────────────────────────────────────────────────────────
story += [
    P("13. Flujo completo de la aplicacion", h1),
    P("""<b>1. Inicio:</b> se carga <i>main.ui</i>, se construye el panel frozen,
    se crean las tarjetas de estadísticas, se conectan las señales de botones y campos.<br/><br/>
    <b>2. El usuario configura parámetros</b> y presiona <i>Simular</i>.<br/><br/>
    <b>3. on_simular()</b> lee y valida los parámetros. Si hay errores, los muestra
    en rojo y no continúa. Si todo está bien, deshabilita el botón, muestra la barra
    de progreso y lanza <i>SimWorker</i> en un hilo aparte.<br/><br/>
    <b>4. SimWorker.run()</b> configura las constantes de <i>simulacion.py</i>,
    llama a <i>resetear_estado()</i> y luego a <i>simular(tiempo_max)</i>.
    Al terminar emite la señal <i>finished</i>.<br/><br/>
    <b>5. _on_sim_done()</b> se ejecuta en el hilo principal. Lee el vector de estado,
    calcula estadísticas, actualiza las tarjetas, rellena la tabla de ultima fila
    y llama a <i>update_table()</i>.<br/><br/>
    <b>6. _on_thread_done()</b> libera el hilo y el worker con <i>deleteLater</i>.<br/><br/>
    <b>7. update_table()</b> aplica los filtros j e i, calcula columnas dinámicas de
    empleados, carga los datos en el modelo, actualiza el encabezado y sincroniza
    el panel frozen.<br/><br/>
    <b>8. El usuario puede cambiar j o i</b> para navegar por los datos sin re-simular.
    Cada cambio dispara <i>update_table()</i> de nuevo.<br/><br/>
    <b>9. El usuario puede copiar</b> las filas visibles al portapapeles con <i>Copiar</i>."""),
]

doc.build(story)
print(f"PDF generado: {OUTPUT}")
