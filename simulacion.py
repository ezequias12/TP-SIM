import heapq
import math
import random

# ── Constantes ────────────────────────────────────────────────────────────────
MAX_COLA          = 5
MAX_ITER          = 99999  # init ocupa fila 0, eventos 1..99999 → 100.000 filas total
MEDIA_LLEGADA_EMP = 2.0
ATN_MIN,  ATN_MAX  = 5, 8
MANT_MIN, MANT_MAX = 3, 10
TEC_MIN,  TEC_MAX  = 57, 63

# ── Estado global ─────────────────────────────────────────────────────────────
terminales        = []
tecnico           = {}
cola              = []
empleados         = {}
eventos           = []
reloj             = 0.0
iteracion         = 0
id_emp_contador   = 0
contador_atendidos = 0
contador_rt       = 0
contador_llegaron = 0   # cnt_llegadas: llegadas totales de empleados
contador_espera   = 0   # cnt_espera:   empleados incluidos en el promedio de espera
acum_espera       = 0.0
vector_estado     = []
ultimo_idx_terminal = -1  # round-robin: índice de la última terminal asignada a un empleado
_seq              = 0     # contador monótono para desempate estable en la cola de eventos (heapq)


# ── Variables aleatorias ──────────────────────────────────────────────────────
def trunc2(x):
    return int(x * 100) / 100


# El RND se trunca a 2 decimales ANTES de la fórmula: así el RND que se muestra en la
# tabla es exactamente el que se usó en el cálculo (tabla auditable / reproducible en
# Excel). Sin esto, el display mostraría 0.26 mientras la fórmula corre con 0.2634…
def gen_llegada_emp():
    rnd = trunc2(random.random())
    t = trunc2(-MEDIA_LLEGADA_EMP * math.log(1 - rnd))
    return rnd, t


def gen_atencion():
    rnd = trunc2(random.random())
    t = trunc2(ATN_MIN + rnd * (ATN_MAX - ATN_MIN))
    return rnd, t


def gen_mantenimiento():
    rnd = trunc2(random.random())
    t = trunc2(MANT_MIN + rnd * (MANT_MAX - MANT_MIN))
    return rnd, t


def gen_llegada_tec():
    rnd = trunc2(random.random())
    t = trunc2(TEC_MIN + rnd * (TEC_MAX - TEC_MIN))
    return rnd, t


# ── Cola de eventos (heap binario, O(log n) por inserción/extracción) ──────────
# Evento = (tiempo, seq, tipo, id). `seq` (monótono) desempata por orden de
# inserción cuando dos eventos tienen el mismo tiempo, replicando exactamente el
# orden del antiguo min() lineal sobre la lista en orden de inserción.
def push_evento(tiempo, tipo, eid=None):
    global _seq
    heapq.heappush(eventos, (tiempo, _seq, tipo, eid))
    _seq += 1


def siguiente_evento():
    return heapq.heappop(eventos)


def tiempo_de(tipo):
    tiempos = [e[0] for e in eventos if e[2] == tipo]
    return min(tiempos) if tiempos else None


def terminal_libre_para_emp():
    global ultimo_idx_terminal
    n = len(terminales)
    for offset in range(1, n + 1):
        idx = (ultimo_idx_terminal + offset) % n
        if terminales[idx]["estado"] == "Libre":
            ultimo_idx_terminal = idx
            return terminales[idx]
    return None


def terminal_libre_con_pendiente():
    for t in terminales:
        if t["estado"] == "Libre" and t["pendiente"]:
            return t
    return None


def hay_pendiente_ocupada():
    return any(t["pendiente"] and t["estado"] == "Ocupada" for t in terminales)


def emp_en_cola():
    return len(cola)   # la cola solo contiene empleados; el técnico nunca entra


def snapshot_empleados():
    # dict {col: (estado, hora_inicio_espera, terminal_id)} — acceso O(1) por columna desde
    # el modelo y mucho más compacto que una lista de dicts. `hora_inicio_espera` es la hora
    # en que el empleado entró a la cola (None si fue atendido de inmediato, sin espera).
    # Valores crudos (sin redondear): el formateo se hace al mostrar.
    return {
        emp["col"]: (emp["estado"], emp["hora_inicio_espera"], emp["terminal_id"])
        for emp in empleados.values()
    }


def guardar_fila(evento_nombre, rnds):
    # Fila compacta con valores CRUDOS. Todo el formateo (truncado a 2 decimales,
    # "SI"/"NO", "-", %RT, prom. espera) se difiere al modelo, que solo formatea
    # las celdas visibles. Así el loop de simulación no construye strings ni redondea.
    vector_estado.append({
        "num":      len(vector_estado),     # índice secuencial: 0=init, 1,2,3...
        "reloj":    reloj,
        "evento":   evento_nombre,
        "prox_emp": tiempo_de("llegada_emp"),
        "prox_tec": tiempo_de("llegada_tec"),
        "term_est":  [t["estado"]    for t in terminales],   # 4 strings
        "term_pend": [t["pendiente"] for t in terminales],   # 4 bools
        "term_fin":  [t["fin_aten"]  for t in terminales],   # 4 float|None (sustituye al antiguo fin_at duplicado)
        "fin_mant":  tecnico["fin_manten"],
        "tec_est":   tecnico["estado"],
        "tec_term":  tecnico["terminal_id"],
        "cola":      len(cola),
        "n_at":      contador_atendidos,
        "n_lleg":    contador_llegaron,   # cnt_llegadas
        "n_rt":      contador_rt,          # cnt_se_van
        "n_esp":     contador_espera,      # cnt_espera
        "acum_esp":  acum_espera,          # acum_espera
        "rnd_le": rnds.get("llegada_emp"), "t_le": rnds.get("t_llegada_emp"),
        "rnd_at": rnds.get("atencion"),    "t_at": rnds.get("t_atencion"),
        "rnd_lt": rnds.get("llegada_tec"), "t_lt": rnds.get("t_llegada_tec"),
        "rnd_mt": rnds.get("manten"),      "t_mt": rnds.get("t_manten"),
        "emp":    snapshot_empleados(),
    })


# ── Asignaciones ──────────────────────────────────────────────────────────────
def asignar_empleado_a_terminal(emp_id, terminal):
    rnd_a, t_a = gen_atencion()
    fin = round(reloj + t_a, 2)

    terminal["estado"]   = "Ocupada"
    terminal["fin_aten"] = fin
    terminal["emp_id"]   = emp_id

    empleados[emp_id]["estado"]      = "SA"
    empleados[emp_id]["terminal_id"] = terminal["id"]

    push_evento(fin, "fin_atencion", terminal["id"])
    return rnd_a, t_a


def asignar_tecnico_a_terminal(terminal):
    rnd_m, t_m = gen_mantenimiento()
    fin = round(reloj + t_m, 2)

    terminal["estado"]     = "Siendo mantenida"
    terminal["pendiente"]  = False
    tecnico["estado"]      = "Realizando Mantenimiento"
    tecnico["terminal_id"] = terminal["id"]
    tecnico["fin_manten"]  = fin

    push_evento(fin, "fin_manten", terminal["id"])
    return rnd_m, t_m


def atender_cola_con_terminal(terminal):
    """
    Al liberarse una terminal, la asigna en este orden de prioridad:
      1. Técnico en ETL si la terminal aún tiene mantenimiento pendiente.
      2. Primer empleado en cola.
      3. Nadie → terminal queda Libre.
    La cola contiene SOLO empleados; el técnico nunca entra ni la modifica.
    """
    global acum_espera, contador_espera

    # Prioridad 1: técnico esperando y terminal pendiente de mantenimiento
    if tecnico["estado"] == "Esperando Terminal Libre" and terminal["pendiente"]:
        rnd_m, t_m = asignar_tecnico_a_terminal(terminal)
        return {"manten": rnd_m, "t_manten": t_m}

    # Prioridad 2: primer empleado en cola. Su espera se contabiliza AHORA, en el
    # instante exacto en que deja la cola y pasa a ser atendido: acum += reloj - hora_inicio_espera.
    if cola:
        emp = cola.pop(0)
        emp_obj = empleados[emp["id"]]
        espera = round(reloj - emp_obj["hora_inicio_espera"], 2)
        acum_espera = round(acum_espera + espera, 2)
        contador_espera += 1
        emp_obj["hora_inicio_espera"] = None   # dejó de esperar → no se propaga más (se muestra "-")
        rnd_a, t_a = asignar_empleado_a_terminal(emp["id"], terminal)
        return {"atencion": rnd_a, "t_atencion": t_a}

    # Nadie espera
    terminal["estado"] = "Libre"
    return {}


# ── Procesadores de eventos ───────────────────────────────────────────────────
def procesar_llegada_emp():
    global id_emp_contador, contador_llegaron, contador_rt, contador_espera

    id_emp_contador  += 1
    contador_llegaron += 1
    emp_id = id_emp_contador

    rnds = {}
    term = terminal_libre_para_emp()

    if term:
        # Terminal libre → atención inmediata: espera 0, pero cuenta en cnt_espera.
        # NO se anota hora_inicio_espera (no hubo espera en cola).
        empleados[emp_id] = {
            "id": emp_id, "col": emp_id,
            "estado": "EA", "hora_inicio_espera": None, "terminal_id": None
        }
        rnd_a, t_a = asignar_empleado_a_terminal(emp_id, term)
        rnds["atencion"]   = rnd_a
        rnds["t_atencion"] = t_a
        contador_espera += 1   # acum_espera += 0 (atención inmediata)
    elif emp_en_cola() < MAX_COLA:
        # No hay terminal libre → entra a la cola: se anota hora_inicio_espera AHORA.
        empleados[emp_id] = {
            "id": emp_id, "col": emp_id,
            "estado": "EA", "hora_inicio_espera": reloj, "terminal_id": None
        }
        cola.append({"tipo": "empleado", "id": emp_id})
    else:
        # Cola llena → se va (RT). Nunca entra en las estadísticas de espera.
        contador_rt += 1

    rnd_e, t_e = gen_llegada_emp()
    rnds["llegada_emp"]   = rnd_e
    rnds["t_llegada_emp"] = t_e
    push_evento(round(reloj + t_e, 2), "llegada_emp")

    guardar_fila(f"Llegada Empleado {emp_id}", rnds)


def procesar_fin_atencion(terminal_id):
    global contador_atendidos

    term   = next(t for t in terminales if t["id"] == terminal_id)
    emp_id = term["emp_id"]

    contador_atendidos += 1

    # La espera ya se contabilizó cuando el empleado dejó la cola (atender_cola_con_terminal),
    # o al llegar si fue atención inmediata. Aquí solo se marca el fin de su atención.
    if emp_id and emp_id in empleados:
        empleados[emp_id]["estado"] = "AT"  # visible en snapshot de esta fila

    term["emp_id"]   = None
    term["fin_aten"] = None

    rnds = atender_cola_con_terminal(term)
    guardar_fila(f"Fin Atención T{terminal_id}", rnds)

    if emp_id and emp_id in empleados:
        del empleados[emp_id]


def procesar_llegada_tec():
    rnds = {}
    term = terminal_libre_con_pendiente()

    if term:
        rnd_m, t_m = asignar_tecnico_a_terminal(term)
        rnds["manten"]   = rnd_m
        rnds["t_manten"] = t_m
    elif hay_pendiente_ocupada():
        # Espera al costado en su propio estado; nunca entra en la cola de empleados
        tecnico["estado"] = "Esperando Terminal Libre"
    else:
        rnd_t, t_t = gen_llegada_tec()
        rnds["llegada_tec"]   = rnd_t
        rnds["t_llegada_tec"] = t_t
        push_evento(round(reloj + t_t, 2), "llegada_tec")

    guardar_fila("Llegada Técnico", rnds)


def procesar_fin_manten(terminal_id):
    rnds = {}

    term_actual = next(t for t in terminales if t["id"] == terminal_id)
    tecnico["terminal_id"] = None
    tecnico["fin_manten"]  = None

    # Buscar próxima terminal pendiente (excluyendo la que acaba de terminar — pendiente=False)
    sig_libre   = terminal_libre_con_pendiente()
    sig_ocupada = hay_pendiente_ocupada()

    if sig_libre:
        # Ir directo a la siguiente terminal libre con pendiente
        term_actual["estado"] = "Libre"
        atender_cola_con_terminal(term_actual)
        rnd_m, t_m = asignar_tecnico_a_terminal(sig_libre)
        rnds["manten"]   = rnd_m
        rnds["t_manten"] = t_m

    elif sig_ocupada:
        # Espera al costado en su propio estado; nunca entra en la cola de empleados
        tecnico["estado"] = "Esperando Terminal Libre"
        term_actual["estado"] = "Libre"
        atender_cola_con_terminal(term_actual)

    else:
        # Ronda completa — resetear pendiente y descansar
        for t in terminales:
            t["pendiente"] = True
        tecnico["estado"] = "Descansando"
        rnd_t, t_t = gen_llegada_tec()
        rnds["llegada_tec"]   = rnd_t
        rnds["t_llegada_tec"] = t_t
        push_evento(round(reloj + t_t, 2), "llegada_tec")
        term_actual["estado"] = "Libre"
        atender_cola_con_terminal(term_actual)

    guardar_fila(f"Fin Mantenimiento T{terminal_id}", rnds)


# ── Loop principal ────────────────────────────────────────────────────────────
def simular(tiempo_max):
    global reloj, iteracion

    rnd_e, t_e = gen_llegada_emp()
    push_evento(t_e, "llegada_emp")

    rnd_t, t_t = gen_llegada_tec()
    push_evento(t_t, "llegada_tec")

    guardar_fila("Inicialización", {
        "llegada_emp": rnd_e, "t_llegada_emp": t_e,
        "llegada_tec": rnd_t, "t_llegada_tec": t_t
    })

    while iteracion < MAX_ITER and reloj < tiempo_max:
        if not eventos:
            break

        tiempo, _, tipo, eid = siguiente_evento()
        reloj = tiempo

        if reloj > tiempo_max:
            break

        if tipo == "llegada_emp":
            procesar_llegada_emp()
        elif tipo == "fin_atencion":
            procesar_fin_atencion(eid)
        elif tipo == "llegada_tec":
            procesar_llegada_tec()
        elif tipo == "fin_manten":
            procesar_fin_manten(eid)

        iteracion += 1

    return vector_estado


def resetear_estado():
    global terminales, tecnico, cola, empleados, eventos
    global reloj, iteracion, id_emp_contador
    global contador_atendidos, contador_rt, contador_llegaron, contador_espera, acum_espera
    global vector_estado, ultimo_idx_terminal, _seq

    terminales = [
        {"id": i, "estado": "Libre", "pendiente": True, "fin_aten": None, "emp_id": None}
        for i in range(1, 5)
    ]
    tecnico   = {"estado": "Descansando", "terminal_id": None, "fin_manten": None}
    cola      = []
    empleados = {}
    eventos   = []
    reloj     = 0.0
    iteracion = 0
    id_emp_contador    = 0
    contador_atendidos = 0
    contador_rt        = 0
    contador_llegaron  = 0
    contador_espera    = 0
    acum_espera        = 0.0
    vector_estado      = []
    ultimo_idx_terminal = -1
    _seq               = 0
