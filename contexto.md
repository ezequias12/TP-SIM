# Contexto completo — TP4 Simulación de Colas (Grupo 22)

> **Documento de traspaso (handoff).** Refleja el estado del proyecto al cierre de la
> última sesión, con TODOS los cambios aplicados. Pensado para retomar el trabajo en
> otra sesión sin perder contexto.

## Descripción del trabajo

Simulación de eventos discretos (DES) para el sistema de registro dactilar de la
Municipalidad de Río Cuarto.
Dos archivos de código únicamente: `simulacion.py` (backend Flask + lógica DES) e
`index.html` (frontend React por CDN, sin npm).

---

## Cómo correr (estado actual)

```bash
pip install flask flask-cors numpy
cd TP-SIM
python3 simulacion.py            # corre en http://localhost:5001
# abrir index.html en el navegador (file://)
```

- **Backend escucha en el puerto `5001`** (`app.run(debug=True, port=5001)` al final de `simulacion.py`).
- **El frontend hace fetch a `http://localhost:5001/simular`** (función `runSim` en `index.html`).
- ⚠️ En macOS el puerto 5001 puede estar ocupado por *ControlCenter*. Si pasa, liberar
  con `kill $(lsof -ti :5001)` o cambiar el puerto **en los dos archivos** (deben coincidir).

---

## Estado de Git (importante para retomar)

- Repo de trabajo: **interior** en `TP2/TP-SIM/` → remote `origin = ezequias12/TP-SIM`, rama `main`.
  (Existe además un repo "exterior" en `TP2/` rama `master` que trata a `TP-SIM` como
  submódulo/gitlink. **Siempre operar git con `git -C .../TP-SIM ...` o parado dentro de
  `TP-SIM/`** para no tocar el repo exterior por error.)
- Último push hecho: merge `65960f9` ya en `origin/main`.
- En el merge con los cambios de ezequias (que tocó los mismos archivos), se resolvió el
  conflicto **quedándose con nuestra versión** de `index.html` y `simulacion.py`, y se
  conservó el `README.md` que él agregó. Hablado con ezequias, OK.
- ⚠️ **Seguridad pendiente:** la URL del remote tiene un **token `ghp_...` embebido en
  texto plano**. Conviene revocarlo en GitHub y reconfigurar el remote sin token.

---

## Sistema simulado

- **4 terminales** de registro dactilar.
- **Empleados** llegan con distribución exponencial negativa (media configurable, default 2 min).
- **Técnico de mantenimiento** llega cada ~60 min (uniforme, rango configurable, default 57–63 min).
- **Tiempo de atención** de empleado: uniforme entre 5 y 8 min (configurable).
- **Tiempo de mantenimiento** por terminal: uniforme entre 3 y 10 min (configurable).
  El técnico genera un **RND nuevo cada vez que empieza a mantener una terminal** (ver más abajo).
- **Cola máxima**: 5 empleados (configurable). Si un empleado llega con la cola llena → se
  va sin volver (RT = "rechazado total") y **no ocupa columna** en la tabla.
- Simulación corre hasta tiempo X O hasta 100.000 filas (lo que ocurra primero).

---

## Parámetros configurables desde el frontend

| Parámetro | Variable Python | Default |
|---|---|---|
| Media llegada empleado (min) | `MEDIA_LLEGADA_EMP` | 2.0 |
| Máx. en cola | `MAX_COLA` | 5 |
| Atención mín (min) | `ATN_MIN` | 5 |
| Atención máx (min) | `ATN_MAX` | 8 |
| Mantenimiento mín (min) | `MANT_MIN` | 3 |
| Mantenimiento máx (min) | `MANT_MAX` | 10 |
| Técnico entre-llegada mín (min) | `TEC_MIN` | 57 |
| Técnico entre-llegada máx (min) | `TEC_MAX` | 63 |
| Tiempo máximo simulación (min) | (parámetro `tiempo_max` en `simular()`) | 480 |

---

## Archivos

```
simulacion.py   — Flask backend + toda la lógica DES (corre en :5001)
index.html      — React 18 CDN (Babel standalone) frontend (fetch a :5001)
contexto.md     — este archivo
enunciado.txt   — enunciado del TP
README.md       — agregado por ezequias (incluye una imagen)
```

---

## simulacion.py — estructura y lógica (estado ACTUAL)

### Constantes y estado global

```python
N_TERMINALES      = 4
MAX_COLA          = 5
MAX_ITER          = 99999   # init ocupa fila 0, eventos 1..99999 → 100.000 filas total
MEDIA_LLEGADA_EMP = 2.0
ATN_MIN,  ATN_MAX  = 5, 8
MANT_MIN, MANT_MAX = 3, 10
TEC_MIN,  TEC_MAX  = 57, 63
```

Estado global (reseteable): `terminales`, `tecnico`, `cola`, `empleados`, `eventos`,
`reloj`, `iteracion`, `id_emp_contador`, `contador_atendidos`, `contador_rt`,
`contador_llegaron`, `acum_espera`, `vector_estado`, **`ultimo_idx_terminal`** (puntero
round-robin de terminales).

> NOTA: `col_emp_contador` **ya no existe** (se eliminó — ver cambio #6).

### Distribuciones

```python
def trunc2(x):
    return int(x * 100) / 100   # truncar (nunca redondear) a 2 decimales

def gen_llegada_emp():     # exponencial negativa
    rnd = random.random()
    return rnd, trunc2(-MEDIA_LLEGADA_EMP * math.log(1 - rnd))

def gen_atencion():        # uniforme [ATN_MIN, ATN_MAX]
def gen_mantenimiento():   # uniforme [MANT_MIN, MANT_MAX]  ← se llama por CADA terminal mantenida
def gen_llegada_tec():     # uniforme [TEC_MIN, TEC_MAX]
```

### Asignación de terminales a empleados — ROUND-ROBIN (cambio #5)

`terminal_libre_para_emp()` ya **no** devuelve siempre la primera libre. Reparte por
turnos (sin RNG) usando el puntero global `ultimo_idx_terminal`, empezando a buscar desde
la terminal siguiente a la última asignada, en forma cíclica:

```python
def terminal_libre_para_emp():
    global ultimo_idx_terminal
    n = len(terminales)
    for offset in range(1, n + 1):
        idx = (ultimo_idx_terminal + offset) % n
        if terminales[idx]["estado"] == "Libre":
            ultimo_idx_terminal = idx
            return terminales[idx]
    return None
```

- Se resetea a `-1` en `resetear_estado()` (primera asignación arranca por Terminal 1).
- **Solo aplica a empleados.** El técnico (`terminal_libre_con_pendiente()`) quedó igual:
  en cada ronda mantiene TODAS las terminales pendientes, así que su orden no genera sobrecarga.

### Empleado: columna = id de llegada (cambio #6)

Cada empleado entra al dict `empleados` con `"id": emp_id` y `"col": emp_id` (el mismo
número de llegada). Los **rechazados (RT) nunca entran al dict**, así que no aparecen en
ningún snapshot ni ocupan columna. Resultado: la columna "Empleado N" se corresponde
exactamente con la N-ésima llegada; los huecos (ej. falta "Empleado 46") son llegadas rechazadas.

### Snapshot de empleados (cambio #3)

```python
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
```

Incluye `terminal_id` = terminal donde es atendido (o `"-"` si está en cola esperando).

### Random de mantenimiento visible al disparar desde Fin Atención (cambio #1)

`atender_cola_con_terminal(terminal)` ahora **retorna un dict** con las claves de los RND
generados (`{"manten":…, "t_manten":…}` o `{"atencion":…, "t_atencion":…}` o `{}`), en vez
de una tupla descartada. Así, cuando un **Fin Atención** libera una terminal y el técnico
(en ETL al frente de la cola) empieza a mantenerla, el `rnd_manten`/`t_manten` queda
guardado en esa fila:

```python
# en procesar_fin_atencion:
rnds = atender_cola_con_terminal(term)
guardar_fila(f"Fin Atencion T{terminal_id}", rnds)
```

### Estados

- **Terminal**: `"Libre"`, `"Ocupada"`, `"Siendo mantenida"`.
- **Técnico**: `"Descansando"` (D), `"ETL"` (esperando terminal libre), `"RM"` (realizando mantenimiento).
- **Empleado**: `"EA"` (esperando atención), `"SA"` (siendo atendido), `"AT"` (acaba de
  terminar / se va — visible solo en la fila de su Fin Atención, luego se borra del dict).

### `atender_cola_con_terminal` — prioridad

Técnico (solo si `terminal["pendiente"]==True`) > empleado > libre. Si el técnico está al
frente pero la terminal ya fue mantenida (`pendiente=False`), se omite al técnico y se
atiende al primer empleado de la cola.

### `procesar_fin_manten` — lógica de ronda

1. Hay terminal libre con `pendiente=True` → el técnico va directo.
2. No hay libre pero sí ocupada con pendiente → `ETL`, entra a cola en posición 0.
3. Ninguna pendiente → **ronda completa**: resetea todas a `pendiente=True`, descansa,
   programa próxima llegada del técnico.

### Endpoint Flask

`POST /simular`: sobreescribe las globales con los parámetros del body, llama
`resetear_estado()`, corre `simular(tiempo_max)` y devuelve `{ "filas": [...], "stats": {...} }`.
**Retorna TODAS las filas**; el filtrado por `j` (hora desde) e `i` (cantidad) lo hace el frontend.

---

## index.html — estructura (estado ACTUAL)

### Stack
React 18 UMD + Babel Standalone (CDN), sin npm/build. Dark theme (Catppuccin Mocha).

### Decoupling simulación / visualización
- `runSim()` hace fetch a `:5001/simular` y guarda todo en `todasFilas`.
- `j` (hora desde) e `i` (cantidad de filas) son filtros locales (`useMemo`) — **no re-simulan**.
- Inputs numéricos guardados como **strings** (evita `Number("")=0`); se parsean con `pf()`/`pi()`.

### Columnas de empleado (DINÁMICAS, cambios #3, #4, #6)
- `activeEmpCols` recolecta los `col` (= id de llegada) que aparecen en las filas visibles
  con estado `EA`, `SA` o `AT`. Los rechazados nunca aparecen → no generan columna.
- `empGRP` arma un grupo por cada empleado activo con **3 sub-columnas**:
  `Estado`, `Hora`, **`Term.`** (terminal donde es atendido).
- `transformar(f)` mapea el snapshot a las claves de fila. Cuando el empleado **se va**
  (estado `"AT"`), blanquea hora y terminal:

```javascript
(f.empleados_snap || []).forEach(e => {
  const seFue = e.estado === "AT";               // fin de atención → ya se fue
  row[`emp${e.col}_estado`] = e.estado;
  row[`emp${e.col}_hora`]   = seFue ? "-" : (e.hora_inicio_esp !== "-" ? e.hora_inicio_esp : e.hora_llegada);
  row[`emp${e.col}_term`]   = seFue ? "-" : e.terminal_id;
});
```

### Render: la "x" roja al irse (cambio #4)
En la celda, el estado `"AT"` se muestra como **`"x"`** (en rojo vía `cfEmp` → clase `.fin`),
mientras que hora y `Term.` muestran `"-"`:

```javascript
const display = raw === "AT" ? "x" : (typeof raw === "number" ? Math.trunc(raw * 100) / 100 : raw);
```

Todos los números se **truncan** (no redondean) a 2 decimales en display.

### Encabezados agrupados de 2 niveles
`GRP_STATIC` (columnas fijas) + `empGRP` (empleados dinámicos). `single:true` → `rowSpan=2`.
`buildThead()` arma el `<thead>` con sticky positioning (fila 1 `top:0`, fila 2 `top:ROW1_H`,
primera columna `#` sticky a la izquierda). `COLUMNAS` = lista plana derivada para las celdas.

---

## Resumen de TODOS los cambios de esta sesión

1. **Random de mantenimiento visible desde Fin Atención** — `atender_cola_con_terminal`
   ahora retorna un dict de RNDs y `procesar_fin_atencion` lo pasa a `guardar_fila`
   (antes se pasaba `{}` y se perdía el `rnd_manten`/`t_manten`).
2. *(refactor del punto 1: el retorno tupla `(None,None)` pasó a ser dict `{}`).*
3. **Atributo `terminal_id` del empleado** — agregado al snapshot del backend y nueva
   sub-columna **"Term."** por empleado en el frontend (muestra la terminal de atención,
   o `-` si está en cola).
4. **"x" roja al irse el empleado** — en la fila de su Fin Atención, estado = `"x"` (rojo),
   y hora + terminal = `"-"` (ya se fue).
5. **Asignación round-robin de terminales a empleados** — `terminal_libre_para_emp()` rota
   por turnos con `ultimo_idx_terminal` (sin RNG); reparte la carga, no satura la Terminal 1.
   No aplica al técnico.
6. **Columna = id de llegada del empleado** — se eliminó `col_emp_contador`; `col = emp_id`.
   Los rechazados (RT) no ocupan columna y cada llegada se corresponde con su propia columna
   (con huecos en los rechazados).
7. **Infra/Git** — puerto unificado en 5001 (backend + fetch del frontend); commit y push a
   `origin/main`; merge con los cambios de ezequias resuelto a favor de nuestra versión.

---

## Bugs corregidos en sesiones anteriores (historial)

1. **Doble fila con num=0** → `"num": len(vector_estado)` (índice secuencial pre-append).
2. **MAX_ITER off-by-one** → `MAX_ITER = 99999` (init + 99.999 eventos = 100.000 filas).
3. **Borrado en inputs numéricos** → estados como strings, parseo con `pf()`/`pi()`.
4. **Re-mantenimiento incorrecto** → `atender_cola_con_terminal` chequea `terminal["pendiente"]`
   antes de asignar el técnico; si `False`, salta al técnico y atiende empleados.
5. **Columnas `t_*` faltantes** → `guardar_fila` lee `t_llegada_emp`, `t_atencion`, etc.
6. **Sticky headers (CSS vs inline)** → todo el sticky se maneja por inline style en `buildThead()`.

---

## Columnas del vector de estado (en orden)

| Grupo | Columnas |
|---|---|
| (single) | #, Reloj, Evento |
| Llegada Empleado | RND, T.entr, Próx. |
| Llegada Técnico | RND, T.entr, Próx. |
| Fin Atención | RND, T.at, At 1, At 2, At 3, At 4 |
| Fin Mantenimiento | RND, T.mant, Fin |
| Terminal 1..4 | Estado, Pend. |
| (single) | Cola |
| Técnico | Estado, Term. |
| Estadísticas | Aten., RT, % RT, AcumEsp, PromEsp |
| Empleado N (dinámico, N = id de llegada) | **Estado, Hora, Term.** |

---

## Colores del frontend

- Terminal: Libre → cyan (`#89dceb`), Ocupada → naranja (`#fab387`), Siendo mantenida → rojo (`#f38ba8`).
- Técnico: D → gris, ETL → amarillo, RM → rojo.
- Empleado: SA → verde, EA → amarillo, **AT → rojo (la "x")**.

---

## Decisiones de diseño

- **Sin npm/bundler**: React y Babel por CDN; abre como `file://`.
- **Backend retorna todo**: `j` e `i` son filtros de visualización (no re-simulan).
- **`trunc2` = truncar, nunca redondear**: requerimiento del enunciado.
- **Round-robin sin RNG**: reparto determinista y reproducible de terminales a empleados.
- **`col = emp_id`**: una columna por empleado que efectivamente entró al sistema.
