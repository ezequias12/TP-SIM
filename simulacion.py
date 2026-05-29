import math
import random
import numpy as np
from flask import Flask, jsonify, request
from flask_cors import CORS

# ── Constantes ────────────────────────────────────────────────────────────────
N_TERMINALES      = 4
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
contador_llegaron = 0
acum_espera       = 0.0
vector_estado     = []
ultimo_idx_terminal = -1  # round-robin: índice de la última terminal asignada a un empleado


# ── Variables aleatorias ──────────────────────────────────────────────────────
def trunc2(x):
    return int(x * 100) / 100


def gen_llegada_emp():
    rnd = random.random()
    t = trunc2(-MEDIA_LLEGADA_EMP * math.log(1 - rnd))
    return rnd, t


def gen_atencion():
    rnd = random.random()
    t = trunc2(ATN_MIN + rnd * (ATN_MAX - ATN_MIN))
    return rnd, t


def gen_mantenimiento():
    rnd = random.random()
    t = trunc2(MANT_MIN + rnd * (MANT_MAX - MANT_MIN))
    return rnd, t


def gen_llegada_tec():
    rnd = random.random()
    t = trunc2(TEC_MIN + rnd * (TEC_MAX - TEC_MIN))
    return rnd, t


# ── Auxiliares ────────────────────────────────────────────────────────────────
def siguiente_evento():
    idx = int(np.argmin([e["tiempo"] for e in eventos]))
    return eventos.pop(idx)


def tiempo_de(tipo):
    tiempos = [e["tiempo"] for e in eventos if e["tipo"] == tipo]
    return round(min(tiempos), 2) if tiempos else "-"


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
    return sum(1 for e in cola if e["tipo"] == "empleado")


def snapshot_empleados():
    snaps = []
    for emp in sorted(empleados.values(), key=lambda e: e["col"]):
        snaps.append({
            "col":             emp["col"],
            "estado":          emp["estado"],
            "hora_llegada":    round(emp["hora_llegada"], 2),
            "hora_inicio_esp": round(emp["hora_inicio_esp"], 2) if emp["hora_inicio_esp"] is not None else "-",
            "terminal_id":     emp["terminal_id"] if emp["terminal_id"] is not None else "-",
        })
    return snaps


def guardar_fila(evento_nombre, rnds):
    pct_rt   = round((contador_rt / contador_llegaron * 100), 2) if contador_llegaron > 0 else 0
    prom_esp = round((acum_espera / contador_atendidos), 3)       if contador_atendidos > 0 else 0

    fila = {
        "num":             len(vector_estado),  # índice secuencial: 0=init, 1,2,3...
        "reloj":           round(reloj, 2),
        "evento":          evento_nombre,
        "prox_emp":        tiempo_de("llegada_emp"),
        "prox_tec":        tiempo_de("llegada_tec"),
        "terminales": [
            {
                "id":       t["id"],
                "estado":   t["estado"],
                "pendiente": "SI" if t["pendiente"] else "NO",
                "fin_aten": round(t["fin_aten"], 2) if t["fin_aten"] else "-"
            }
            for t in terminales
        ],
        "fin_at": [
            round(t["fin_aten"], 2) if t["fin_aten"] else "-"
            for t in terminales
        ],
        "fin_mant":        round(tecnico["fin_manten"], 2) if tecnico["fin_manten"] else "-",
        "tec_estado":      tecnico["estado"],
        "tec_terminal":    tecnico["terminal_id"] if tecnico["terminal_id"] else "-",
        "cola_largo":      len(cola),
        "cnt_atendidos":   contador_atendidos,
        "cnt_rt":          contador_rt,
        "pct_rt":          pct_rt,
        "acum_espera":     round(acum_espera, 2),
        "prom_espera":     prom_esp,
        "rnd_llegada_emp": rnds.get("llegada_emp", "-"),
        "t_llegada_emp":   rnds.get("t_llegada_emp", "-"),
        "rnd_atencion":    rnds.get("atencion", "-"),
        "t_atencion":      rnds.get("t_atencion", "-"),
        "rnd_llegada_tec": rnds.get("llegada_tec", "-"),
        "t_llegada_tec":   rnds.get("t_llegada_tec", "-"),
        "rnd_manten":      rnds.get("manten", "-"),
        "t_manten":        rnds.get("t_manten", "-"),
        "empleados_snap":  snapshot_empleados()
    }
    vector_estado.append(fila)


# ── Asignaciones ──────────────────────────────────────────────────────────────
def asignar_empleado_a_terminal(emp_id, terminal):
    rnd_a, t_a = gen_atencion()
    fin = round(reloj + t_a, 2)

    terminal["estado"]   = "Ocupada"
    terminal["fin_aten"] = fin
    terminal["emp_id"]   = emp_id

    empleados[emp_id]["estado"]          = "SA"
    empleados[emp_id]["terminal_id"]     = terminal["id"]
    empleados[emp_id]["hora_asignacion"] = reloj

    eventos.append({"tipo": "fin_atencion", "tiempo": fin, "id": terminal["id"]})
    return rnd_a, t_a


def asignar_tecnico_a_terminal(terminal):
    rnd_m, t_m = gen_mantenimiento()
    fin = round(reloj + t_m, 2)

    terminal["estado"]     = "Siendo mantenida"
    terminal["pendiente"]  = False
    tecnico["estado"]      = "RM"
    tecnico["terminal_id"] = terminal["id"]
    tecnico["fin_manten"]  = fin

    eventos.append({"tipo": "fin_manten", "tiempo": fin, "id": terminal["id"]})
    return rnd_m, t_m


def atender_cola_con_terminal(terminal):
    """
    Prioridad: técnico (solo si terminal tiene pendiente=True) > empleado > libre.
    Si el técnico está al frente pero la terminal ya fue mantenida,
    se omite al técnico y se sirve al primer empleado en espera.
    Retorna dict con las claves de random generadas (puede estar vacío).
    """
    if not cola:
        terminal["estado"] = "Libre"
        return {}

    siguiente = cola[0]

    if siguiente["tipo"] == "tecnico":
        if terminal["pendiente"]:
            cola.pop(0)
            rnd_m, t_m = asignar_tecnico_a_terminal(terminal)
            return {"manten": rnd_m, "t_manten": t_m}
        else:
            # Terminal no necesita mantenimiento — saltar al técnico, atender empleados
            for i, item in enumerate(cola):
                if item["tipo"] == "empleado":
                    cola.pop(i)
                    rnd_a, t_a = asignar_empleado_a_terminal(item["id"], terminal)
                    return {"atencion": rnd_a, "t_atencion": t_a}
            terminal["estado"] = "Libre"
            return {}
    else:
        cola.pop(0)
        rnd_a, t_a = asignar_empleado_a_terminal(siguiente["id"], terminal)
        return {"atencion": rnd_a, "t_atencion": t_a}


# ── Procesadores de eventos ───────────────────────────────────────────────────
def procesar_llegada_emp():
    global id_emp_contador, contador_llegaron, contador_rt

    id_emp_contador  += 1
    contador_llegaron += 1
    emp_id = id_emp_contador

    rnds = {}
    term = terminal_libre_para_emp()

    if term:
        empleados[emp_id] = {
            "id": emp_id, "col": emp_id,
            "estado": "EA", "hora_llegada": reloj,
            "hora_inicio_esp": None, "hora_asignacion": None, "terminal_id": None
        }
        rnd_a, t_a = asignar_empleado_a_terminal(emp_id, term)
        rnds["atencion"]   = rnd_a
        rnds["t_atencion"] = t_a
    elif emp_en_cola() < MAX_COLA:
        empleados[emp_id] = {
            "id": emp_id, "col": emp_id,
            "estado": "EA", "hora_llegada": reloj,
            "hora_inicio_esp": reloj, "hora_asignacion": None, "terminal_id": None
        }
        cola.append({"tipo": "empleado", "id": emp_id})
    else:
        contador_rt += 1

    rnd_e, t_e = gen_llegada_emp()
    rnds["llegada_emp"]   = rnd_e
    rnds["t_llegada_emp"] = t_e
    eventos.append({"tipo": "llegada_emp", "tiempo": round(reloj + t_e, 2), "id": None})

    guardar_fila(f"Llegada Empleado {emp_id}", rnds)


def procesar_fin_atencion(terminal_id):
    global contador_atendidos, acum_espera

    term   = next(t for t in terminales if t["id"] == terminal_id)
    emp_id = term["emp_id"]

    contador_atendidos += 1

    if emp_id and emp_id in empleados:
        emp = empleados[emp_id]
        if emp["hora_inicio_esp"] is not None and emp["hora_asignacion"] is not None:
            espera = emp["hora_asignacion"] - emp["hora_inicio_esp"]
            acum_espera = round(acum_espera + espera, 2)
        empleados[emp_id]["estado"] = "AT"  # visible en snapshot de esta fila

    term["emp_id"]   = None
    term["fin_aten"] = None

    rnds = atender_cola_con_terminal(term)
    guardar_fila(f"Fin Atencion T{terminal_id}", rnds)

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
        tecnico["estado"] = "ETL"
        cola.insert(0, {"tipo": "tecnico"})
    else:
        rnd_t, t_t = gen_llegada_tec()
        rnds["llegada_tec"]   = rnd_t
        rnds["t_llegada_tec"] = t_t
        eventos.append({"tipo": "llegada_tec", "tiempo": round(reloj + t_t, 2), "id": None})

    guardar_fila("Llegada Tecnico", rnds)


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
        # Esperar al frente de la cola
        tecnico["estado"] = "ETL"
        cola.insert(0, {"tipo": "tecnico"})
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
        eventos.append({"tipo": "llegada_tec", "tiempo": round(reloj + t_t, 2), "id": None})
        term_actual["estado"] = "Libre"
        atender_cola_con_terminal(term_actual)

    guardar_fila(f"Fin Mantenimiento T{terminal_id}", rnds)


# ── Loop principal ────────────────────────────────────────────────────────────
def simular(tiempo_max):
    global reloj, iteracion

    rnd_e, t_e = gen_llegada_emp()
    eventos.append({"tipo": "llegada_emp", "tiempo": t_e, "id": None})

    rnd_t, t_t = gen_llegada_tec()
    eventos.append({"tipo": "llegada_tec", "tiempo": t_t, "id": None})

    guardar_fila("Inicializacion", {
        "llegada_emp": rnd_e, "t_llegada_emp": t_e,
        "llegada_tec": rnd_t, "t_llegada_tec": t_t
    })

    while iteracion < MAX_ITER and reloj < tiempo_max:
        if not eventos:
            break

        ev    = siguiente_evento()
        reloj = ev["tiempo"]

        if reloj > tiempo_max:
            break

        if ev["tipo"] == "llegada_emp":
            procesar_llegada_emp()
        elif ev["tipo"] == "fin_atencion":
            procesar_fin_atencion(ev["id"])
        elif ev["tipo"] == "llegada_tec":
            procesar_llegada_tec()
        elif ev["tipo"] == "fin_manten":
            procesar_fin_manten(ev["id"])

        iteracion += 1

    return vector_estado


# ── Flask ─────────────────────────────────────────────────────────────────────
app = Flask(__name__)
CORS(app, origins="*")


def resetear_estado():
    global terminales, tecnico, cola, empleados, eventos
    global reloj, iteracion, id_emp_contador
    global contador_atendidos, contador_rt, contador_llegaron, acum_espera
    global vector_estado, ultimo_idx_terminal

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
    acum_espera        = 0.0
    vector_estado      = []
    ultimo_idx_terminal = -1


@app.route("/simular", methods=["POST"])
def endpoint_simular():
    global MAX_COLA, MEDIA_LLEGADA_EMP, ATN_MIN, ATN_MAX, MANT_MIN, MANT_MAX, TEC_MIN, TEC_MAX

    data       = request.get_json()
    tiempo_max = float(data.get("tiempo_max", 480))

    # Parámetros del sistema (modificables desde el frontend)
    MAX_COLA          = int(data.get("max_cola", 5))
    MEDIA_LLEGADA_EMP = float(data.get("media_llegada_emp", 2.0))
    ATN_MIN           = float(data.get("atn_min", 5))
    ATN_MAX           = float(data.get("atn_max", 8))
    MANT_MIN          = float(data.get("mant_min", 3))
    MANT_MAX          = float(data.get("mant_max", 10))
    TEC_MIN           = float(data.get("tec_min", 57))
    TEC_MAX           = float(data.get("tec_max", 63))

    resetear_estado()
    vs = simular(tiempo_max)

    # j e i son filtros de visualización — el frontend los aplica sobre todas las filas
    cnt_aten = vs[-1]["cnt_atendidos"] if vs else 0
    prom_espera_final = round(vs[-1]["acum_espera"] / cnt_aten, 3) if cnt_aten > 0 else 0

    stats = {
        "total_llegaron":    cnt_aten + (vs[-1]["cnt_rt"] if vs else 0),
        "total_atendidos":   cnt_aten,
        "total_rt":          vs[-1]["cnt_rt"]  if vs else 0,
        "pct_rt":            vs[-1]["pct_rt"]  if vs else 0,
        "prom_espera":       prom_espera_final,
        "total_iteraciones": iteracion,
        "tiempo_simulado":   round(reloj, 2),
        "total_filas":       len(vs)
    }

    return jsonify({
        "filas": vs,   # todas las filas — el frontend filtra por j e i
        "stats": stats
    })


if __name__ == "__main__":
    app.run(debug=True, port=5001)
