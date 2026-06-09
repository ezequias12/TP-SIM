from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Preformatted,
    HRFlowable, KeepTogether
)
from reportlab.lib.enums import TA_CENTER

OUTPUT = "explicacion_simulacion.pdf"

doc = SimpleDocTemplate(
    OUTPUT,
    pagesize=A4,
    leftMargin=2.5*cm, rightMargin=2.5*cm,
    topMargin=2.5*cm, bottomMargin=2.5*cm,
    title="Explicacion simulacion.py — TP Simulacion",
    author="Grupo 22"
)

styles = getSampleStyleSheet()

titulo = ParagraphStyle("titulo", parent=styles["Title"],
    fontSize=22, spaceAfter=6, textColor=colors.HexColor("#4a4a8a"),
    alignment=TA_CENTER)
subtitulo = ParagraphStyle("subtitulo", parent=styles["Normal"],
    fontSize=11, spaceAfter=20, textColor=colors.HexColor("#666666"),
    alignment=TA_CENTER)
h1 = ParagraphStyle("h1", parent=styles["Heading1"],
    fontSize=15, spaceBefore=22, spaceAfter=6,
    textColor=colors.HexColor("#2c2c7a"))
h2 = ParagraphStyle("h2", parent=styles["Heading2"],
    fontSize=12, spaceBefore=14, spaceAfter=4,
    textColor=colors.HexColor("#444499"))
body = ParagraphStyle("body", parent=styles["Normal"],
    fontSize=10, leading=15, spaceAfter=8)
code_style = ParagraphStyle("code", parent=styles["Code"],
    fontSize=8.5, leading=13, leftIndent=12,
    backColor=colors.HexColor("#f4f4f4"),
    borderColor=colors.HexColor("#cccccc"),
    borderWidth=0.5, borderPad=6,
    fontName="Courier", spaceAfter=8)
nota = ParagraphStyle("nota", parent=styles["Normal"],
    fontSize=9, leading=13, leftIndent=12,
    textColor=colors.HexColor("#555555"),
    backColor=colors.HexColor("#fffbe6"),
    borderColor=colors.HexColor("#e0c040"),
    borderWidth=0.5, borderPad=5, spaceAfter=8)

def P(text, style=body):   return Paragraph(text, style)
def CODE(text):             return Preformatted(text, code_style)
def HR():                   return HRFlowable(width="100%", thickness=0.5,
                                color=colors.HexColor("#cccccc"), spaceAfter=4)
def NOTA(text):             return Paragraph(text, nota)

story = []

# ── Portada ───────────────────────────────────────────────────────────────────
story += [
    Spacer(1, 1.5*cm),
    P("Explicacion de <b>simulacion.py</b>", titulo),
    P("TP Simulacion de Colas — Grupo 22<br/>"
      "Sistema de Registro Dactilar — Municipalidad de Rio Cuarto", subtitulo),
    HR(), Spacer(1, 0.5*cm),
]

# ─────────────────────────────────────────────────────────────────────────────
# 1. VISION GENERAL
# ─────────────────────────────────────────────────────────────────────────────
story += [
    P("1. Vision general de simulacion.py", h1),
    P("""<b>simulacion.py</b> es el nucleo logico de la aplicacion. Implementa una
    <b>simulacion de eventos discretos (DES)</b> pura: no tiene interfaz grafica,
    no habla con bases de datos ni con la red. Solo recibe parametros, simula el
    sistema y devuelve una lista de filas con el estado del sistema en cada evento."""),
    P("""El sistema simulado es la sala de registro dactilar de la Municipalidad
    de Rio Cuarto: empleados que llegan, hacen fila, son atendidos en terminales,
    y un tecnico que periodicamente mantiene esas terminales."""),
    P("El archivo se organiza en siete bloques:"),
    P("""<b>1.</b> Constantes y variables globales.<br/>
    <b>2.</b> Generadores de variables aleatorias.<br/>
    <b>3.</b> Cola de eventos (heap binario).<br/>
    <b>4.</b> Funciones auxiliares de consulta del estado.<br/>
    <b>5.</b> Funciones de asignacion y resolucion de prioridad.<br/>
    <b>6.</b> Procesadores de eventos (uno por tipo de evento).<br/>
    <b>7.</b> Loop principal y reset."""),
    NOTA("La separacion entre simulacion.py y main.py es intencional: la logica "
         "de simulacion no sabe nada de la GUI, y la GUI no sabe como funciona "
         "la simulacion. Se comunican solo a traves de vector_estado."),
]

# ─────────────────────────────────────────────────────────────────────────────
# 2. CONSTANTES Y VARIABLES GLOBALES
# ─────────────────────────────────────────────────────────────────────────────
story += [
    P("2. Constantes y variables globales", h1),

    P("2.1 Constantes de configuracion", h2),
    CODE(
"MAX_COLA          = 5      # maximo de empleados en cola de espera\n"
"MAX_ITER          = 99999  # maximo de eventos a procesar\n"
"MEDIA_LLEGADA_EMP = 2.0    # media de la exponencial de llegada de empleados\n"
"ATN_MIN,  ATN_MAX  = 5, 8  # rango de tiempo de atencion (uniforme)\n"
"MANT_MIN, MANT_MAX = 3, 10 # rango de tiempo de mantenimiento (uniforme)\n"
"TEC_MIN,  TEC_MAX  = 57,63 # rango de tiempo entre llegadas del tecnico (uniforme)"
    ),
    P("""Estas constantes son los parametros del sistema. <b>main.py</b> las
    sobrescribe antes de cada simulacion con los valores que el usuario ingreso
    en la interfaz. Si el usuario no cambia nada, corren con estos valores por defecto."""),

    P("2.2 Estructura: terminales", h2),
    P("""Lista de 4 diccionarios, uno por terminal. Cada terminal tiene:"""),
    CODE(
'{"id": 1, "estado": "Libre", "pendiente": True, "fin_aten": None, "emp_id": None}'
    ),
    P("""— <b>id</b>: numero de terminal (1 a 4).<br/>
    — <b>estado</b>: puede ser <i>Libre</i>, <i>Ocupada</i> o <i>Siendo mantenida</i>.<br/>
    — <b>pendiente</b>: flag booleano que indica si esa terminal todavia necesita
    mantenimiento en esta ronda del tecnico. Arranca en True para todas.<br/>
    — <b>fin_aten</b>: el tiempo de reloj en que termina la atencion actual (None si libre).<br/>
    — <b>emp_id</b>: ID del empleado que esta siendo atendido (None si libre)."""),

    P("2.3 Estructura: tecnico", h2),
    CODE(
'tecnico = {"estado": "Descansando", "terminal_id": None, "fin_manten": None}'
    ),
    P("""Diccionario unico que representa al tecnico. Sus estados posibles son:<br/>
    — <b>Descansando</b>: termino la ronda de mantenimiento y espera su proximo turno.<br/>
    — <b>Esperando Terminal Libre</b>: llego para mantener pero todas las terminales
    que le faltan estan ocupadas. Espera al costado sin entrar a la cola de empleados.<br/>
    — <b>Realizando Mantenimiento</b>: esta trabajando sobre una terminal."""),

    P("2.4 Estructura: cola", h2),
    P("""Lista de diccionarios que representa la fila de espera de empleados.
    Cada elemento tiene solo dos campos: <b>tipo</b> (siempre "empleado") e <b>id</b>.
    El tecnico <b>nunca</b> entra a esta cola; tiene su propio mecanismo de espera."""),
    CODE('cola = [{"tipo": "empleado", "id": 3}, {"tipo": "empleado", "id": 5}, ...]'),

    P("2.5 Estructura: empleados", h2),
    P("""Diccionario global con un registro por cada empleado que esta actualmente
    en el sistema (esperando o siendo atendido). La clave es el emp_id:"""),
    CODE(
'empleados = {\n'
'    3: {"id": 3, "col": 3, "estado": "EA",\n'
'        "hora_inicio_espera": 4.72, "terminal_id": None},\n'
'    5: {"id": 5, "col": 5, "estado": "SA",\n'
'        "hora_inicio_espera": None, "terminal_id": 2}\n'
'}'
    ),
    P("""— <b>col</b>: numero de columna que ocupa en la tabla (igual al ID de llegada).<br/>
    — <b>estado</b>: <i>EA</i> (esperando atencion) o <i>SA</i> (siendo atendido).<br/>
    — <b>hora_inicio_espera</b>: el reloj en que entro a la cola. None si fue atendido
    de inmediato o si ya salio de la cola.<br/>
    — <b>terminal_id</b>: la terminal donde esta siendo atendido. None si todavia espera."""),
    NOTA("Los empleados rechazados (RT) nunca entran a este diccionario. "
         "Los que terminan de ser atendidos se borran despues de guardar la fila. "
         "Por eso los huecos en la numeracion de columnas corresponden a rechazados."),

    P("2.6 Cola de eventos: eventos", h2),
    P("""Lista que funciona como un <b>heap binario minimo</b> (administrada con el
    modulo <i>heapq</i>). Cada elemento es una tupla de 4 valores:"""),
    CODE("(tiempo, seq, tipo, eid)"),
    P("""— <b>tiempo</b>: el momento del reloj en que ocurre el evento.<br/>
    — <b>seq</b>: numero secuencial monotono para desempatar eventos con el mismo tiempo
    (se respeta el orden de insercion, igual que el antiguo min() lineal).<br/>
    — <b>tipo</b>: string que identifica el tipo: "llegada_emp", "fin_atencion",
    "llegada_tec" o "fin_manten".<br/>
    — <b>eid</b>: dato extra, generalmente el ID de la terminal involucrada (None para llegadas)."""),

    P("2.7 Contadores y acumuladores estadisticos", h2),
    CODE(
"reloj             = 0.0   # tiempo actual de la simulacion\n"
"iteracion         = 0     # cantidad de eventos procesados\n"
"id_emp_contador   = 0     # ultimo ID de empleado asignado\n"
"contador_atendidos = 0    # empleados que completaron su atencion\n"
"contador_rt        = 0    # empleados rechazados (cola llena)\n"
"contador_llegaron  = 0    # total de empleados que llegaron al sistema\n"
"contador_espera    = 0    # empleados incluidos en el promedio de espera\n"
"acum_espera        = 0.0  # suma de tiempos de espera de todos los atendidos"
    ),
    P("""Con estos valores se calculan las dos metricas pedidas por el enunciado:<br/>
    — <b>% que se van</b> = contador_rt / contador_llegaron * 100<br/>
    — <b>Promedio de espera</b> = acum_espera / contador_espera"""),
    NOTA("contador_espera incluye a los empleados que esperaron 0 minutos "
         "(fueron atendidos de inmediato). Esto hace que el promedio sea "
         "sobre todos los empleados del sistema, no solo los que esperaron."),

    P("2.8 Otras variables globales", h2),
    CODE(
"ultimo_idx_terminal = -1  # puntero round-robin para asignar terminales\n"
"_seq                = 0   # contador monotono para desempate en el heap\n"
"vector_estado       = []  # lista de filas guardadas, resultado final"
    ),
]

# ─────────────────────────────────────────────────────────────────────────────
# 3. GENERADORES DE VARIABLES ALEATORIAS
# ─────────────────────────────────────────────────────────────────────────────
story += [
    P("3. Generadores de variables aleatorias", h1),
    P("""Todos los tiempos aleatorios del sistema se generan con estas cuatro funciones.
    Cada una devuelve una tupla <b>(rnd, tiempo)</b>: el numero aleatorio usado
    y el tiempo calculado. Devolver ambos permite mostrar el RND exacto en la tabla."""),

    P("3.1 trunc2 — truncado a 2 decimales", h2),
    CODE("def trunc2(x):\n    return int(x * 100) / 100"),
    P("""Trunca un numero a 2 decimales sin redondear. Se aplica al RND antes
    de la formula y al resultado, para que el numero mostrado en la tabla
    sea exactamente el que se uso en el calculo. Sin esto, la tabla mostraria
    0.26 pero la formula habria corrido con 0.2634..."""),
    NOTA("El enunciado pide truncar, no redondear. trunc2 usa int() que "
         "siempre descarta los decimales restantes sin importar el valor."),

    P("3.2 gen_llegada_emp — distribucion exponencial negativa", h2),
    CODE(
"def gen_llegada_emp():\n"
"    rnd = trunc2(random.random())\n"
"    t = trunc2(-MEDIA_LLEGADA_EMP * math.log(1 - rnd))\n"
"    return rnd, t"
    ),
    P("""Genera el tiempo hasta la proxima llegada de un empleado.
    Usa la formula de la inversa de la exponencial negativa:
    <b>t = -media * ln(1 - rnd)</b>. Con media = 2 minutos,
    los tiempos entre llegadas son pequenos pero variables."""),

    P("3.3 gen_atencion y gen_mantenimiento — distribucion uniforme", h2),
    CODE(
"def gen_atencion():\n"
"    rnd = trunc2(random.random())\n"
"    t = trunc2(ATN_MIN + rnd * (ATN_MAX - ATN_MIN))\n"
"    return rnd, t"
    ),
    P("""Formula de la uniforme: <b>t = min + rnd * (max - min)</b>.
    Para atencion: entre 5 y 8 minutos. Para mantenimiento: entre 3 y 10 minutos.
    El tecnico genera un nuevo RND por cada terminal que mantiene en la ronda."""),

    P("3.4 gen_llegada_tec — uniforme para el tecnico", h2),
    P("""Igual que las anteriores pero con rango 57-63 minutos. Se llama para
    programar la proxima llegada del tecnico una vez que termina su ronda completa.
    El tecnico llega aproximadamente cada hora."""),
]

# ─────────────────────────────────────────────────────────────────────────────
# 4. COLA DE EVENTOS (HEAP)
# ─────────────────────────────────────────────────────────────────────────────
story += [
    P("4. Cola de eventos — el heap binario", h1),
    P("""El corazon de cualquier simulacion de eventos discretos es la estructura
    que decide cual es el proximo evento a procesar. Aqui se usa un
    <b>heap binario minimo</b> a traves del modulo <i>heapq</i> de Python."""),
    P("""Un heap minimo garantiza que el elemento con menor valor siempre esta
    en la cima. Como los eventos se ordenan por tiempo, el proximo evento
    a procesar siempre es el primero de la estructura. Insertar o extraer
    un elemento cuesta <b>O(log n)</b>, mucho mas eficiente que buscar el
    minimo en una lista no ordenada (O(n))."""),

    P("4.1 push_evento — insertar un evento", h2),
    CODE(
"def push_evento(tiempo, tipo, eid=None):\n"
"    global _seq\n"
"    heapq.heappush(eventos, (tiempo, _seq, tipo, eid))\n"
"    _seq += 1"
    ),
    P("""Cada evento se inserta como una tupla (tiempo, seq, tipo, eid).
    El campo <b>seq</b> es un contador que crece con cada insercion. Cuando
    dos eventos tienen el mismo tiempo, Python los compara por el segundo campo
    de la tupla (seq), y el que fue insertado primero tiene menor seq y sale primero.
    Esto replica exactamente el comportamiento del antiguo min() lineal sobre
    una lista en orden de insercion."""),

    P("4.2 siguiente_evento — extraer el proximo", h2),
    CODE("def siguiente_evento():\n    return heapq.heappop(eventos)"),
    P("""Extrae y devuelve el evento con menor tiempo. Internamente el heap
    se reestructura en O(log n) para mantener su propiedad."""),

    P("4.3 tiempo_de — consultar sin extraer", h2),
    CODE(
"def tiempo_de(tipo):\n"
"    tiempos = [e[0] for e in eventos if e[2] == tipo]\n"
"    return min(tiempos) if tiempos else None"
    ),
    P("""No extrae ningun evento. Busca en el heap el minimo tiempo de los eventos
    de un tipo especifico. Se usa para mostrar en la tabla los campos
    'Prox. Evento' de llegada de empleado y de llegada de tecnico."""),
]

# ─────────────────────────────────────────────────────────────────────────────
# 5. FUNCIONES AUXILIARES DE CONSULTA
# ─────────────────────────────────────────────────────────────────────────────
story += [
    P("5. Funciones auxiliares de consulta del estado", h1),
    P("""Estas funciones no modifican el estado; solo lo consultan y devuelven
    una respuesta. Son la capa de abstraccion entre el estado global y los
    procesadores de eventos."""),

    P("5.1 terminal_libre_para_emp — round-robin", h2),
    CODE(
"def terminal_libre_para_emp():\n"
"    global ultimo_idx_terminal\n"
"    n = len(terminales)\n"
"    for offset in range(1, n + 1):\n"
"        idx = (ultimo_idx_terminal + offset) % n\n"
"        if terminales[idx]['estado'] == 'Libre':\n"
"            ultimo_idx_terminal = idx\n"
"            return terminales[idx]\n"
"    return None"
    ),
    P("""Busca una terminal libre usando <b>round-robin</b>: en lugar de siempre
    empezar desde la terminal 1, arranca desde la siguiente a la que fue asignada
    la ultima vez. Esto distribuye la carga entre terminales de forma equitativa."""),
    P("""El modulo <b>%</b> hace que el indice sea circular: si la ultima asignada
    fue la terminal 4 (indice 3), la siguiente busqueda empieza por la terminal 1
    (indice 0). Si no hay ninguna libre, devuelve None."""),
    NOTA("El round-robin es deterministico: no usa numeros aleatorios. "
         "La distribucion es predecible y reproducible."),

    P("5.2 terminal_libre_con_pendiente — para el tecnico", h2),
    CODE(
"def terminal_libre_con_pendiente():\n"
"    for t in terminales:\n"
"        if t['estado'] == 'Libre' and t['pendiente']:\n"
"            return t\n"
"    return None"
    ),
    P("""Busca una terminal que este libre Y que todavia tenga mantenimiento
    pendiente en esta ronda. El tecnico solo va a terminales que cumplen ambas
    condiciones. No usa round-robin: toma la primera que encuentra."""),

    P("5.3 hay_pendiente_ocupada", h2),
    CODE(
"def hay_pendiente_ocupada():\n"
"    return any(t['pendiente'] and t['estado'] == 'Ocupada' for t in terminales)"
    ),
    P("""Devuelve True si hay al menos una terminal que esta ocupada (con empleado)
    Y todavia tiene mantenimiento pendiente. Se usa para saber si el tecnico
    debe quedarse esperando o irse a descansar."""),

    P("5.4 emp_en_cola", h2),
    CODE("def emp_en_cola():\n    return len(cola)"),
    P("""Devuelve cuantos empleados hay esperando en la cola.
    Se compara contra MAX_COLA para decidir si un empleado nuevo puede entrar
    o si debe ser rechazado."""),
]

# ─────────────────────────────────────────────────────────────────────────────
# 6. FUNCIONES DE ASIGNACION Y PRIORIDAD
# ─────────────────────────────────────────────────────────────────────────────
story += [
    P("6. Funciones de asignacion y prioridad", h1),

    P("6.1 asignar_empleado_a_terminal", h2),
    CODE(
"def asignar_empleado_a_terminal(emp_id, terminal):\n"
"    rnd_a, t_a = gen_atencion()\n"
"    fin = round(reloj + t_a, 2)\n\n"
"    terminal['estado']   = 'Ocupada'\n"
"    terminal['fin_aten'] = fin\n"
"    terminal['emp_id']   = emp_id\n\n"
"    empleados[emp_id]['estado']      = 'SA'\n"
"    empleados[emp_id]['terminal_id'] = terminal['id']\n\n"
"    push_evento(fin, 'fin_atencion', terminal['id'])\n"
"    return rnd_a, t_a"
    ),
    P("""Hace todo lo necesario para que un empleado empiece a ser atendido:
    genera el tiempo de atencion, marca la terminal como Ocupada, actualiza
    el estado del empleado a SA (Siendo Atendido) y programa el evento
    fin_atencion en el heap para que la simulacion sepa cuando va a terminar."""),

    P("6.2 asignar_tecnico_a_terminal", h2),
    CODE(
"def asignar_tecnico_a_terminal(terminal):\n"
"    rnd_m, t_m = gen_mantenimiento()\n"
"    fin = round(reloj + t_m, 2)\n\n"
"    terminal['estado']     = 'Siendo mantenida'\n"
"    terminal['pendiente']  = False\n"
"    tecnico['estado']      = 'Realizando Mantenimiento'\n"
"    tecnico['terminal_id'] = terminal['id']\n"
"    tecnico['fin_manten']  = fin\n\n"
"    push_evento(fin, 'fin_manten', terminal['id'])\n"
"    return rnd_m, t_m"
    ),
    P("""Analogo al anterior pero para el tecnico. El flag <b>pendiente</b> se pone
    en False en este momento porque el mantenimiento de esa terminal ya esta
    en curso: no hay que volver a hacerlo en esta ronda."""),

    P("6.3 atender_cola_con_terminal — la regla de prioridad", h2),
    P("""Esta es la funcion mas importante del archivo en terminos de logica de negocio.
    Se llama cada vez que una terminal queda disponible (ya sea porque termino una
    atencion o porque termino un mantenimiento) y decide que hacer con ella."""),
    CODE(
"def atender_cola_con_terminal(terminal):\n"
"    # Prioridad 1: tecnico esperando y terminal pendiente\n"
"    if tecnico['estado'] == 'Esperando Terminal Libre' and terminal['pendiente']:\n"
"        rnd_m, t_m = asignar_tecnico_a_terminal(terminal)\n"
"        return {'manten': rnd_m, 't_manten': t_m}\n\n"
"    # Prioridad 2: primer empleado en cola\n"
"    if cola:\n"
"        emp = cola.pop(0)\n"
"        espera = round(reloj - empleados[emp['id']]['hora_inicio_espera'], 2)\n"
"        acum_espera += espera\n"
"        contador_espera += 1\n"
"        rnd_a, t_a = asignar_empleado_a_terminal(emp['id'], terminal)\n"
"        return {'atencion': rnd_a, 't_atencion': t_a}\n\n"
"    # Nadie espera\n"
"    terminal['estado'] = 'Libre'\n"
"    return {}"
    ),
    P("""Las tres posibilidades en orden de prioridad:"""),
    P("""<b>Prioridad 1 — el tecnico tiene preferencia.</b> Si el tecnico esta en
    estado 'Esperando Terminal Libre' Y la terminal que se libero tiene mantenimiento
    pendiente, el tecnico la toma de inmediato antes que cualquier empleado en la cola.
    El tecnico no interrumpe atenciones en curso, pero en cuanto una terminal se libera
    y le corresponde, la toma primero."""),
    P("""<b>Prioridad 2 — empleados en cola.</b> Si no hay tecnico esperando (o la
    terminal no le corresponde), se toma el primer empleado de la cola. En ese momento
    exacto se calcula su tiempo de espera (reloj actual menos hora_inicio_espera) y
    se acumula. El empleado pasa de EA a SA."""),
    P("""<b>Sin prioridad — terminal libre.</b> Si no hay nadie esperando, la terminal
    simplemente queda en estado Libre."""),
    NOTA("La espera se calcula y acumula cuando el empleado SALE de la cola "
         "y empieza a ser atendido, no cuando llega ni cuando termina. "
         "Esto garantiza que el calculo sea exactamente la diferencia entre "
         "el momento de entrar a la cola y el momento de salir de ella."),
]

# ─────────────────────────────────────────────────────────────────────────────
# 7. SNAPSHOT Y GUARDAR FILA
# ─────────────────────────────────────────────────────────────────────────────
story += [
    P("7. snapshot_empleados y guardar_fila", h1),

    P("7.1 snapshot_empleados", h2),
    CODE(
"def snapshot_empleados():\n"
"    return {\n"
"        emp['col']: (emp['estado'], emp['hora_inicio_espera'], emp['terminal_id'])\n"
"        for emp in empleados.values()\n"
"    }"
    ),
    P("""Toma una foto del estado de todos los empleados activos en el sistema
    en este momento. Devuelve un diccionario donde la clave es el numero de columna
    del empleado (= su ID de llegada) y el valor es una tupla de 3 elementos:
    estado, hora de inicio de espera y terminal asignada."""),
    P("""Este snapshot se guarda dentro de cada fila del vector de estado.
    Cuando la GUI quiere mostrar el estado de un empleado en una fila determinada,
    consulta este dict con el ID del empleado como clave."""),

    P("7.2 guardar_fila", h2),
    CODE(
"def guardar_fila(evento_nombre, rnds):\n"
"    vector_estado.append({\n"
"        'num':      len(vector_estado),\n"
"        'reloj':    reloj,\n"
"        'evento':   evento_nombre,\n"
"        'prox_emp': tiempo_de('llegada_emp'),\n"
"        'prox_tec': tiempo_de('llegada_tec'),\n"
"        'term_est':  [t['estado']    for t in terminales],\n"
"        'term_pend': [t['pendiente'] for t in terminales],\n"
"        'term_fin':  [t['fin_aten']  for t in terminales],\n"
"        'fin_mant':  tecnico['fin_manten'],\n"
"        'tec_est':   tecnico['estado'],\n"
"        'tec_term':  tecnico['terminal_id'],\n"
"        'cola':      len(cola),\n"
"        'n_at':      contador_atendidos,\n"
"        'n_lleg':    contador_llegaron,\n"
"        'n_rt':      contador_rt,\n"
"        'n_esp':     contador_espera,\n"
"        'acum_esp':  acum_espera,\n"
"        'rnd_le': rnds.get('llegada_emp'), ...\n"
"        'emp':    snapshot_empleados(),\n"
"    })"
    ),
    P("""Guarda el estado completo del sistema en el momento exacto de llamarla.
    Todos los valores son <b>crudos</b>: floats sin truncar, booleanos como True/False,
    None donde no hay valor. El formateo (truncado a 2 decimales, SI/NO, guiones,
    porcentajes, promedios) lo hace la GUI al momento de mostrar cada celda."""),
    P("""El parametro <b>rnds</b> es el diccionario con los numeros aleatorios
    generados en ese evento especifico. No todos los eventos generan los mismos RNDs:
    una llegada de empleado genera RND de llegada y puede generar RND de atencion;
    una llegada de tecnico puede generar RND de mantenimiento. guardar_fila
    guarda lo que le llega, y los campos que no corresponden quedan en None."""),
    NOTA("El numero de fila (num) es simplemente la longitud actual de vector_estado "
         "antes de agregar esta fila. La fila 0 es siempre la de Inicializacion."),
]

# ─────────────────────────────────────────────────────────────────────────────
# 8. PROCESADORES DE EVENTOS
# ─────────────────────────────────────────────────────────────────────────────
story += [
    P("8. Procesadores de eventos", h1),
    P("""Hay un procesador por cada tipo de evento posible en la simulacion.
    Cada uno recibe el control cuando el loop principal extrae su evento del heap,
    modifica el estado global segun las reglas del sistema, programa los eventos
    futuros que correspondan, y llama a guardar_fila para registrar el estado."""),

    P("8.1 procesar_llegada_emp — llegada de un empleado", h2),
    P("""Es el procesador mas complejo porque tiene tres caminos posibles:"""),
    P("""<b>Camino 1 — hay terminal libre:</b> el empleado es registrado en el dict
    con hora_inicio_espera = None (no espero), se lo asigna de inmediato a la terminal
    via round-robin, y se suma 1 a contador_espera con espera = 0. El promedio
    de espera lo incluye como si hubiera esperado 0 minutos."""),
    P("""<b>Camino 2 — no hay terminal libre pero la cola tiene lugar:</b>
    el empleado entra al dict con hora_inicio_espera = reloj (se anota el momento exacto)
    y se agrega al final de la lista cola. No se genera ningun evento nuevo para el:
    la cola se procesa cuando se libera una terminal."""),
    P("""<b>Camino 3 — la cola esta llena (>= MAX_COLA):</b> el empleado es rechazado.
    Solo se incrementa contador_rt. No entra al dict, no ocupa columna en la tabla,
    no vuelve."""),
    P("""En los tres caminos, al final siempre se genera la proxima llegada de empleado
    y se la programa en el heap. La simulacion debe saber cuando llega el siguiente
    para poder procesarlo en el momento correcto."""),

    P("8.2 procesar_fin_atencion — fin de atencion en una terminal", h2),
    P("""Se ejecuta cuando una terminal termina de atender a un empleado.
    El orden de operaciones es importante:"""),
    P("""<b>1.</b> Se obtiene que terminal termino y que empleado estaba ahi.<br/>
    <b>2.</b> Se incrementa contador_atendidos.<br/>
    <b>3.</b> Se cambia el estado del empleado a "AT" (quedo visible en tabla).<br/>
    <b>4.</b> Se limpia la terminal (emp_id = None, fin_aten = None).<br/>
    <b>5.</b> Se llama a atender_cola_con_terminal: decide si el tecnico, un empleado
    de la cola, o nadie toma esa terminal.<br/>
    <b>6.</b> Se guarda la fila (el empleado todavia esta en el dict con estado AT).<br/>
    <b>7.</b> Se borra el empleado del dict (desaparece de los snapshots futuros)."""),
    NOTA("El empleado se borra despues de guardar la fila, no antes. "
         "Esto es lo que hace que la x roja aparezca en la fila de fin de atencion "
         "y desaparezca en las filas siguientes."),

    P("8.3 procesar_llegada_tec — llegada del tecnico", h2),
    P("""El tecnico llega periodicamente para hacer mantenimiento. Al llegar
    hay tres situaciones posibles:"""),
    P("""<b>Caso 1 — hay terminal libre con pendiente:</b> el tecnico va directo a
    mantenerla. Se genera el tiempo de mantenimiento y se programa fin_manten en el heap."""),
    P("""<b>Caso 2 — todas las terminales pendientes estan ocupadas:</b> el tecnico
    no puede interrumpir. Se queda en estado 'Esperando Terminal Libre'. No entra
    a la cola de empleados. Cuando cualquier terminal ocupada-pendiente se libere,
    atender_cola_con_terminal le dara prioridad sobre los empleados en espera."""),
    P("""<b>Caso 3 — no hay ninguna terminal con pendiente = True:</b> esto significa
    que ya no quedan terminales por mantener en esta ronda (todas tienen pendiente = False).
    El tecnico se va y se programa su proxima llegada en el heap."""),

    P("8.4 procesar_fin_manten — fin de mantenimiento de una terminal", h2),
    P("""Cuando el tecnico termina de mantener una terminal, busca que hacer a continuacion.
    El proceso en orden:"""),
    P("""<b>1.</b> Se limpia el estado del tecnico (terminal_id = None, fin_manten = None).<br/>
    <b>2.</b> Se busca si hay otra terminal libre con pendiente (siguiente en la ronda).<br/>
    <b>3.</b> Se busca si hay alguna terminal ocupada con pendiente (tecnico debe esperar)."""),
    P("""<b>Caso A — hay otra terminal libre con pendiente:</b> la terminal que termino
    de ser mantenida queda Libre, se llama a atender_cola_con_terminal para ver si
    hay empleados esperando, y el tecnico va directo a la siguiente terminal pendiente."""),
    P("""<b>Caso B — hay terminales pendientes pero todas estan ocupadas:</b>
    la terminal que termino queda Libre (y se atiende la cola si hay alguien),
    el tecnico queda en 'Esperando Terminal Libre' hasta que alguna se libere."""),
    P("""<b>Caso C — no quedan terminales pendientes (ronda completa):</b>
    el tecnico termino de mantener todas las terminales. Se resetean todos los
    flags pendiente a True (para la proxima ronda), el tecnico pasa a 'Descansando'
    y se programa su proxima llegada en el heap con gen_llegada_tec.
    La terminal que termino queda Libre."""),
    NOTA("El ciclo del tecnico es: llega -> mantiene terminal 1 -> mantiene terminal 2 "
         "-> ... -> mantiene terminal 4 -> descansa ~60 min -> llega de nuevo. "
         "Si una terminal esta ocupada cuando le toca, espera al costado sin "
         "bloquear la cola de empleados."),
]

# ─────────────────────────────────────────────────────────────────────────────
# 9. LOOP PRINCIPAL — simular()
# ─────────────────────────────────────────────────────────────────────────────
story += [
    P("9. Loop principal — simular(tiempo_max)", h1),
    P("""Es el punto de entrada de la simulacion. Recibe el tiempo maximo en minutos
    y corre el loop de eventos hasta que se cumpla alguna condicion de corte."""),

    P("9.1 Inicializacion", h2),
    CODE(
"rnd_e, t_e = gen_llegada_emp()\n"
"push_evento(t_e, 'llegada_emp')\n\n"
"rnd_t, t_t = gen_llegada_tec()\n"
"push_evento(t_t, 'llegada_tec')\n\n"
"guardar_fila('Inicializacion', {...})"
    ),
    P("""Antes de empezar el loop, se programan los dos primeros eventos:
    la primera llegada de empleado y la primera llegada del tecnico.
    Ambos se insertan en el heap con sus tiempos generados aleatoriamente.
    Luego se guarda la fila de inicializacion (fila 0) con el estado inicial."""),

    P("9.2 El loop", h2),
    CODE(
"while iteracion < MAX_ITER and reloj < tiempo_max:\n"
"    if not eventos:\n"
"        break\n\n"
"    tiempo, _, tipo, eid = siguiente_evento()\n\n"
"    if tiempo > tiempo_max:\n"
"        break\n\n"
"    reloj = tiempo\n\n"
"    if tipo == 'llegada_emp':   procesar_llegada_emp()\n"
"    elif tipo == 'fin_atencion': procesar_fin_atencion(eid)\n"
"    elif tipo == 'llegada_tec':  procesar_llegada_tec()\n"
"    elif tipo == 'fin_manten':   procesar_fin_manten(eid)\n\n"
"    iteracion += 1"
    ),
    P("""En cada iteracion el loop hace exactamente esto:"""),
    P("""<b>1.</b> Extrae el evento con menor tiempo del heap (siguiente_evento).<br/>
    <b>2.</b> Si ese tiempo supera tiempo_max, corta el loop SIN pisar el reloj
    (el reloj conserva el tiempo del ultimo evento efectivamente procesado).<br/>
    <b>3.</b> Avanza el reloj al tiempo del evento.<br/>
    <b>4.</b> Llama al procesador correspondiente segun el tipo de evento.<br/>
    <b>5.</b> Incrementa el contador de iteraciones."""),

    P("9.3 Condiciones de corte", h2),
    P("""El loop se detiene cuando ocurre cualquiera de estas condiciones:"""),
    P("""— <b>iteracion >= MAX_ITER</b> (99.999 eventos procesados + fila 0 = 100.000 filas totales).<br/>
    — <b>reloj >= tiempo_max</b> (al inicio del loop, antes de extraer).<br/>
    — <b>El heap esta vacio</b> (no quedan eventos programados, situacion inusual).<br/>
    — <b>El proximo evento supera tiempo_max</b> (al extraerlo, antes de procesar)."""),
    NOTA("El limite de 100.000 filas existe para que la aplicacion no se cuelgue "
         "en simulaciones muy largas. En condiciones normales el corte ocurre "
         "por tiempo_max, no por MAX_ITER."),
]

# ─────────────────────────────────────────────────────────────────────────────
# 10. RESETEAR_ESTADO
# ─────────────────────────────────────────────────────────────────────────────
story += [
    P("10. resetear_estado — preparar para una nueva simulacion", h1),
    P("""Antes de cada simulacion, <b>main.py</b> llama a <b>resetear_estado()</b>
    para limpiar todas las variables globales y partir desde cero. Sin esto,
    la segunda simulacion arrancaria con el estado final de la primera."""),
    CODE(
"terminales = [\n"
"    {'id': i, 'estado': 'Libre', 'pendiente': True,\n"
"     'fin_aten': None, 'emp_id': None}\n"
"    for i in range(1, 5)\n"
"]\n"
"tecnico   = {'estado': 'Descansando', 'terminal_id': None, 'fin_manten': None}\n"
"cola      = []\n"
"empleados = {}\n"
"eventos   = []\n"
"reloj     = 0.0\n"
"# ... todos los contadores en 0"
    ),
    P("""Recrea las 4 terminales desde cero con pendiente=True, reinicia el tecnico
    a 'Descansando', vacia la cola, el dict de empleados, el heap de eventos,
    y pone todos los contadores y acumuladores en cero."""),
]

# ─────────────────────────────────────────────────────────────────────────────
# 11. ESTADISTICAS FILA A FILA
# ─────────────────────────────────────────────────────────────────────────────
story += [
    P("11. Como se acumulan las estadisticas fila a fila", h1),
    P("""Las estadisticas no se calculan al final: se van acumulando evento a evento.
    Cada fila del vector de estado guarda una foto de los contadores en ese momento,
    de modo que al mirar cualquier fila se puede ver el estado de las estadisticas
    hasta ese punto de la simulacion."""),

    P("11.1 contador_llegaron", h2),
    P("""Se incrementa en 1 al inicio de cada llamada a procesar_llegada_emp,
    antes de decidir si el empleado es atendido, encolado o rechazado.
    Cuenta <b>todos</b> los empleados que llegaron al sistema, sin excepcion."""),

    P("11.2 contador_rt", h2),
    P("""Se incrementa solo en el tercer camino de procesar_llegada_emp,
    cuando la cola esta llena. Cuenta solo los rechazados.
    El porcentaje se calcula en la GUI: n_rt / n_lleg * 100."""),

    P("11.3 contador_atendidos", h2),
    P("""Se incrementa en procesar_fin_atencion cada vez que un empleado
    termina su atencion. No cuenta a los que estan siendo atendidos ahora,
    solo a los que ya terminaron."""),

    P("11.4 acum_espera y contador_espera", h2),
    P("""Son los mas delicados. La espera de un empleado se contabiliza en
    dos situaciones diferentes, pero siempre en el momento exacto en que
    el empleado <b>pasa de esperar a ser atendido</b>:"""),
    P("""— <b>Atencion inmediata</b> (en procesar_llegada_emp): el empleado
    llego y habia terminal disponible. Su espera es 0. Se suma 0 a acum_espera
    y se incrementa contador_espera en 1.<br/>
    — <b>Desde la cola</b> (en atender_cola_con_terminal): el empleado esperaba
    en cola. Su espera es reloj - hora_inicio_espera. Se suma esa diferencia
    a acum_espera y se incrementa contador_espera en 1."""),
    P("""El promedio de espera en cualquier fila es: acum_espera / contador_espera.
    Este promedio incluye a todos los empleados del sistema, incluso los que
    esperaron 0 minutos, por lo que representa el promedio real del sistema."""),
    NOTA("Los rechazados (RT) nunca entran en acum_espera ni en contador_espera: "
         "se fueron sin esperar y sin ser atendidos. Solo afectan contador_rt y contador_llegaron."),
]

# ─────────────────────────────────────────────────────────────────────────────
# 12. QUE DEVUELVE LA SIMULACION
# ─────────────────────────────────────────────────────────────────────────────
story += [
    P("12. Que devuelve la simulacion y en que formato", h1),
    P("""Al terminar el loop, <b>simular()</b> devuelve <b>vector_estado</b>:
    una lista de diccionarios donde cada elemento representa una fila de la tabla."""),
    P("""Cada diccionario contiene:"""),
    P("""— Datos de identificacion: num, reloj, evento.<br/>
    — Proximos eventos: prox_emp, prox_tec.<br/>
    — Estado de terminales: listas de 4 elementos (term_est, term_pend, term_fin).<br/>
    — Estado del tecnico: fin_mant, tec_est, tec_term.<br/>
    — Longitud de la cola: cola.<br/>
    — Contadores acumulados: n_at, n_lleg, n_rt, n_esp, acum_esp.<br/>
    — Numeros aleatorios generados en este evento: rnd_le, t_le, rnd_at, t_at, etc.<br/>
    — Snapshot de empleados: emp (dict con el estado de cada empleado activo)."""),
    P("""Todos los valores son <b>crudos</b>: floats, enteros, booleanos o None.
    El formateo se hace en la GUI al momento de mostrar cada celda, nunca en la simulacion."""),
    P("""Ademas de vector_estado, quedan disponibles como variables del modulo:
    <b>sim.reloj</b> (tiempo del ultimo evento), <b>sim.iteracion</b> (eventos
    procesados), y todos los contadores finales que la GUI usa para las tarjetas
    de estadisticas."""),
]

# ─────────────────────────────────────────────────────────────────────────────
# 13. FLUJO COMPLETO ENCADENADO
# ─────────────────────────────────────────────────────────────────────────────
story += [
    P("13. Flujo completo encadenado", h1),
    P("""Para cerrar, el recorrido completo de la simulacion de principio a fin:"""),
    P("""<b>1. resetear_estado()</b> — se limpian todas las variables. Las 4 terminales
    quedan Libres con pendiente=True. El tecnico queda Descansando.<br/><br/>
    <b>2. simular(tiempo_max)</b> — se generan los dos primeros eventos: la primera
    llegada de empleado y la primera llegada del tecnico. Se guarda la fila de
    Inicializacion. El loop arranca.<br/><br/>
    <b>3. El loop extrae el evento con menor tiempo del heap.</b> Generalmente
    la primera llegada de empleado ocurre antes que la del tecnico (media 2 min
    vs media 60 min).<br/><br/>
    <b>4. procesar_llegada_emp()</b> — el empleado llega. Si hay terminal libre,
    va directo. Se genera la proxima llegada de empleado y se inserta en el heap.
    Se guarda la fila.<br/><br/>
    <b>5. El loop sigue extrayendo eventos.</b> Llegan mas empleados, algunos van
    directo a terminales, otros esperan. El heap va creciendo y decreciendo
    segun se programan y procesan eventos.<br/><br/>
    <b>6. En algun momento ocurre un fin_atencion.</b> La terminal se libera.
    atender_cola_con_terminal decide si el tecnico (si esta esperando) o el
    primer empleado de la cola toma esa terminal. Se guarda la fila.<br/><br/>
    <b>7. Despues de ~60 minutos, llega el tecnico.</b> procesar_llegada_tec
    lo manda a la primera terminal libre con pendiente. Si no hay libre, queda
    esperando. Se guarda la fila.<br/><br/>
    <b>8. El tecnico va terminando terminales.</b> Cada fin_manten busca la
    siguiente. Cuando termina la ronda completa, se resetean los pendientes
    y se programa la proxima llegada del tecnico.<br/><br/>
    <b>9. El loop corta</b> cuando el reloj supera tiempo_max o se alcanzan
    99.999 iteraciones.<br/><br/>
    <b>10. simular() devuelve vector_estado</b> con todas las filas generadas.
    La GUI lee ese resultado y lo muestra en la tabla."""),
]

doc.build(story)
print(f"PDF generado: {OUTPUT}")
