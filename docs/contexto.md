# Contexto completo — TP4 Simulación de Colas (Grupo 22)

> **Documento de traspaso (handoff).** Refleja el estado real del proyecto. Pensado para
> retomar el trabajo en otra sesión sin perder contexto.

## Descripción del trabajo

Simulación de eventos discretos (DES) del sistema de registro dactilar de la Municipalidad
de Río Cuarto. Aplicación **de escritorio** con interfaz gráfica.

- `simulacion.py` — lógica DES pura (sin web, sin dependencias de UI). Cola de eventos con
  `heapq`.
- `main.py` — interfaz gráfica **PyQt5** (modelo/vista virtual, encabezado agrupado,
  panel de columnas congeladas, hilo de simulación, tarjetas de estadísticas).
- `main.ui` — layout de la ventana (Qt Designer, cargado con `uic.loadUi`).

> No hay servidor Flask, ni React, ni navegador. Toda la app corre en un único proceso
> de escritorio. (El stack web de versiones anteriores fue reemplazado en el commit
> `e9fcf34` "Migrar frontend a PyQt5".)

---

## Cómo correr

```bash
pip install PyQt5
cd TP-SIM
python main.py
```

Se abre la ventana "TP4 — Simulación: Sistemas de Colas". No requiere conexión de red ni
puerto.

---

## Archivos

```
simulacion.py    — lógica DES (variables aleatorias, eventos, procesadores, loop)
main.py          — GUI PyQt5 (modelo, vista, header agrupado, worker, stats)
main.ui          — layout de la ventana (Qt Designer XML)
README.md        — captura de pantalla
docs/enunciado.txt      — enunciado del TP
docs/consideraciones.md — requerimientos de interfaz para TP3+
docs/contexto.md        — este archivo
```

---

## Sistema simulado

- **4 terminales** de registro dactilar.
- **Empleados** llegan con distribución exponencial negativa (media configurable, default 2 min).
- **Tiempo de atención** de empleado: uniforme entre 5 y 8 min (configurable).
- **Técnico de mantenimiento** vuelve cada ~60 min (uniforme, default 57–63 min), medido
  desde que terminó el mantenimiento de la **última** terminal de la ronda.
- **Tiempo de mantenimiento** por terminal: uniforme entre 3 y 10 min (configurable). El
  técnico genera un RND nuevo por cada terminal que mantiene.
- El técnico tiene **prioridad sobre los empleados** pero **no interrumpe** un registro en
  curso: si no hay terminal libre pendiente, espera (`Esperando Terminal Libre`) y toma la
  primera que se libere antes que la cola de empleados.
- **Cola**: si un empleado llega y la cola ya está llena (≥ `MAX_COLA`, default 5) se va y
  cuenta como RT (rechazado). **No vuelve** y no ocupa columna en la tabla.
- La simulación corre hasta `tiempo_max` minutos **o** hasta 100.000 filas, lo que ocurra
  primero (`MAX_ITER = 99999` + fila de inicialización).

---

## Métricas pedidas por el enunciado

- **% de empleados que se van para regresar más tarde** → `% que se van = RT / llegaron`.
- **Tiempo promedio de espera** (todos los empleados del sistema) → `acum_espera / atendidos`
  (incluye a quienes esperaron 0 por ir directo a una terminal libre).

---

## Desviaciones del enunciado (decididas a propósito)

> Dos puntos del enunciado se resolvieron con una interpretación distinta a la literal. Si
> la cátedra objeta, cada corrección es de **una línea**.

1. **El rechazado no regresa.** El enunciado dice *"se va y regresa a la media hora"*
   (+30 min). El código solo incrementa `contador_rt`; no programa una re-llegada. Solo se
   reporta el porcentaje. Ubicación: `simulacion.py` (rama `else` de `procesar_llegada_emp`).
2. **Cola máxima = 5 (lectura "5 o más").** El enunciado dice *"más de 5 esperando"*, que
   literalmente permitiría hasta 6 en cola. El código usa `emp_en_cola() < MAX_COLA` con
   `MAX_COLA = 5`, es decir rechaza cuando ya hay 5 esperando. Ubicación:
   `simulacion.py` (condición `elif emp_en_cola() < MAX_COLA`).

---

## Parámetros configurables (desde la GUI)

| Parámetro | Widget (`main.ui`) | Variable (`simulacion.py`) | Default |
|---|---|---|---|
| Media llegada empleado (min) | `txt_media_llegada` | `MEDIA_LLEGADA_EMP` | 2 |
| Máx. en cola | `txt_max_cola` | `MAX_COLA` | 5 |
| Atención mín (min) | `txt_atn_min` | `ATN_MIN` | 5 |
| Atención máx (min) | `txt_atn_max` | `ATN_MAX` | 8 |
| Mantenimiento mín (min) | `txt_mant_min` | `MANT_MIN` | 3 |
| Mantenimiento máx (min) | `txt_mant_max` | `MANT_MAX` | 10 |
| Técnico entre-llegada mín (min) | `txt_tec_min` | `TEC_MIN` | 57 |
| Técnico entre-llegada máx (min) | `txt_tec_max` | `TEC_MAX` | 63 |
| Tiempo máximo (X, min) | `txt_tiempo_max` | (arg `tiempo_max` de `simular()`) | 480 |
| Hora desde (j, min) | `txt_hora_desde` | filtro de visualización | 0 |
| Cant. filas (i) | `txt_cant_filas` | filtro de visualización | 20 |

`on_simular()` lee los widgets, sobrescribe las globales de `simulacion`, llama
`resetear_estado()` y corre `simular(tiempo_max)` en un hilo aparte.

---

## simulacion.py — estructura y lógica

### Constantes y estado global

```python
MAX_COLA          = 5
MAX_ITER          = 99999   # init = fila 0; eventos 1..99999 → 100.000 filas
MEDIA_LLEGADA_EMP = 2.0
ATN_MIN,  ATN_MAX  = 5, 8
MANT_MIN, MANT_MAX = 3, 10
TEC_MIN,  TEC_MAX  = 57, 63
```

Estado global reseteable por `resetear_estado()`: `terminales`, `tecnico`, `cola`,
`empleados`, `eventos`, `reloj`, `iteracion`, `id_emp_contador`, `contador_atendidos`,
`contador_rt`, `contador_llegaron`, `acum_espera`, `vector_estado`, `ultimo_idx_terminal`
(puntero round-robin), `_seq` (desempate del heap).

### Variables aleatorias

```python
def trunc2(x):  return int(x * 100) / 100   # truncar (nunca redondear) a 2 decimales

def gen_llegada_emp():   # exponencial negativa: -media * ln(1 - rnd)
def gen_atencion():      # uniforme [ATN_MIN, ATN_MAX]
def gen_mantenimiento(): # uniforme [MANT_MIN, MANT_MAX]  ← se llama por CADA terminal
def gen_llegada_tec():   # uniforme [TEC_MIN, TEC_MAX]
```

Cada generador devuelve `(rnd, tiempo_truncado)`.

### Cola de eventos (heap)

Evento = `(tiempo, seq, tipo, eid)`. `push_evento` / `siguiente_evento` usan `heapq`
(O(log n)). `seq` (monótono) desempata por orden de inserción cuando dos eventos comparten
tiempo. `tiempo_de(tipo)` devuelve el próximo tiempo de un tipo de evento (para columnas
"Próx. Evento").

### Asignación de terminales

- `terminal_libre_para_emp()` — **round-robin** con `ultimo_idx_terminal` (sin RNG): reparte
  empleados entre terminales, empezando desde la siguiente a la última asignada. Solo aplica
  a empleados.
- `terminal_libre_con_pendiente()` — primera terminal Libre con `pendiente=True` (para el
  técnico).
- `hay_pendiente_ocupada()` — hay alguna terminal Ocupada con mantenimiento pendiente.

### Prioridad al liberarse una terminal — `atender_cola_con_terminal(terminal)`

1. Técnico (si está `Esperando Terminal Libre` y la terminal tiene `pendiente=True`).
2. Primer empleado de la cola.
3. Nadie → la terminal queda `Libre`.

Devuelve un dict con los RND generados (`{"manten":…}` / `{"atencion":…}` / `{}`) para que
la fila correspondiente muestre el RND correcto.

### Procesadores de eventos

- `procesar_llegada_emp()` — asigna terminal libre (round-robin) o encola si hay lugar; si
  no, RT. Programa la próxima llegada de empleado.
- `procesar_fin_atencion(term_id)` — acumula la espera del empleado atendido
  (`hora_asignacion - hora_inicio_esp`), marca `AT`, libera la terminal y la reasigna por
  prioridad. El empleado se borra del dict después de guardar la fila.
- `procesar_llegada_tec()` — manda al técnico a una terminal libre pendiente; si no hay pero
  hay ocupada pendiente, queda `Esperando Terminal Libre`; si no hay ninguna pendiente,
  reprograma su próxima llegada.
- `procesar_fin_manten(term_id)` — busca la siguiente terminal pendiente (libre u ocupada).
  Si no queda ninguna → **ronda completa**: resetea `pendiente=True` en todas, el técnico
  descansa y se programa su próxima llegada (60±3 desde el fin de la última terminal).

### Loop principal — `simular(tiempo_max)`

Programa primera llegada de empleado y de técnico, guarda fila "Inicialización" y corre
hasta `MAX_ITER` o `reloj >= tiempo_max` (o cola de eventos vacía). Devuelve `vector_estado`.

### Estados

- **Terminal**: `Libre`, `Ocupada`, `Siendo mantenida` (+ flag `pendiente`).
- **Técnico**: `Descansando`, `Esperando Terminal Libre`, `Realizando Mantenimiento`.
- **Empleado**: `EA` (esperando atención), `SA` (siendo atendido), `AT` (acaba de terminar /
  se va — visible solo en la fila de su Fin Atención; se muestra como `"x"`).

### Empleado: columna = id de llegada

Cada empleado entra al dict `empleados` con `"col": emp_id` (su número de llegada). Los
rechazados (RT) nunca entran al dict → no aparecen en ningún snapshot ni ocupan columna. Los
huecos en la numeración de columnas corresponden a llegadas rechazadas.

### Fila del vector de estado — `guardar_fila`

Guarda **valores crudos** (sin formatear). El truncado a 2 decimales, los `"SI"/"NO"`, los
`"-"`, el `%RT` y el promedio de espera se calculan en el modelo de la GUI, solo para las
celdas visibles (para no construir strings en el loop de simulación).

---

## main.py — estructura (PyQt5)

### `SimModel(QAbstractTableModel)` — modelo virtual

Renderizado virtual: solo se piden las celdas visibles, sin parpadeo aunque haya miles de
filas. `set_content(rows, cols)` fija filas y columnas. `_spec(key)` decide cómo leer cada
columna (escalar, lista de terminales, %RT, promedio, empleado dinámico) y qué mapa de
colores aplicar. `_fmt` trunca floats (`trunc2_str`), mapea bools a `SI`/`NO` y `None` a `-`.

### `GroupedHeader(QHeaderView)` — encabezado de dos niveles

Dibuja a mano (`paintEvent`) dos filas de encabezado: fila superior con el nombre del grupo
coloreado (Llegada Empleado, Fin Atención, Terminal 1..4, Estadísticas, Empleado N…) y fila
inferior con el título de cada columna. `set_groups(groups)` define los tramos.

### Panel de columnas congeladas (frozen)

Un segundo `QTableView` (`self._frozen`) muestra solo las **3 primeras columnas** (#, Reloj,
Evento) y comparte modelo y selección con la tabla principal. La tabla principal oculta esas
3 columnas. Los scrolls verticales se sincronizan en ambos sentidos → las 3 columnas quedan
siempre visibles al hacer scroll horizontal, y la selección de fila se mantiene.

### `SimWorker(QObject)` + `QThread`

La simulación corre en un hilo aparte para no congelar la UI. Al iniciar muestra
`prg_sim` (barra indeterminada) y "⏳ Simulando…"; al terminar (`finished`) vuelca
`sim.vector_estado`, calcula estadísticas y refresca tablas.

### Tabla de "última fila" + tarjetas de estadísticas

- `tbl_ultima` — altura fija, muestra solo la última fila del vector (estado final).
- `pnl_stats` — tarjetas: Total llegaron, Atendidos, Se fueron (RT), % que se van,
  Prom. espera, Iteraciones, Tiempo simulado.

### Filtro de visualización (no re-simula)

`update_table()` filtra `todas_filas` por **j** (hora desde, con `bisect` sobre la lista de
relojes) e **i** (cantidad de filas). Recalcula las columnas dinámicas de empleados a partir
de las filas visibles. Cambiar j/i NO vuelve a correr la simulación.

### Copiar a Excel — `on_copiar`

Vuelca encabezados + todas las filas visibles como TSV al portapapeles → se pega directo en
Excel/planillas.

---

## main.ui — estructura del layout

`QMainWindow` → `QVBoxLayout`:

1. `lbl_titulo` + `lbl_subtitulo` + separador.
2. `grp_params` (QGroupBox, grilla): los 8 parámetros del sistema.
3. `grp_sim` (QGroupBox): `txt_tiempo_max`, `btn_simular`, `prg_sim`, `lbl_info`.
4. Separador.
5. `grp_vis` (QGroupBox): `txt_hora_desde` (j), `txt_cant_filas` (i), `btn_copiar`,
   `lbl_filtro`.
6. `tbl_vector` (QTableView principal, se expande).
7. `lbl_ultima` + `tbl_ultima` (última fila, altura fija).
8. `pnl_stats` (QFrame, tarjetas creadas en Python).

El tema oscuro (Catppuccin Mocha) se aplica por stylesheet (`DARK`) en `main.py`.

---

## Columnas del vector de estado (en orden)

| Grupo | Columnas |
|---|---|
| (fijas) | #, Reloj, Evento |
| Llegada Empleado | RND, T. Entrada, Próx. Evento |
| Llegada Técnico | RND, T. Entrada, Próx. Evento |
| Fin Atención | RND, T. Atención, Fin At. 1..4 |
| Fin Mantenimiento | RND, T. Mantenim., Fin Mantenim. |
| Terminal 1..4 | Estado, Pendiente |
| Cola | Cola |
| Técnico | Estado, Terminal |
| Estadísticas | Atendidos, Se fueron (RT), % RT, Acum. Espera, Prom. Espera |
| Empleado N (dinámico, N = id de llegada) | Estado, Hora inicio, Terminal |

---

## Colores de la GUI

- Terminal: Libre → cyan (`#89dceb`), Ocupada → naranja (`#fab387`), Siendo mantenida → rojo (`#f38ba8`).
- Técnico: Descansando → gris (`#9399b2`), Esperando Terminal Libre → amarillo (`#f9e2af`), Realizando Mantenimiento → rojo (`#f38ba8`).
- Empleado: SA → verde (`#a6e3a1`), EA → amarillo (`#f9e2af`), "x" (AT) → rojo (`#f38ba8`).

---

## Decisiones de diseño

- **App de escritorio PyQt5**: sin web, sin servidor, sin build. Un solo proceso.
- **Modelo virtual** (`QAbstractTableModel`): solo renderiza celdas visibles → sin parpadeo
  con miles de filas (requerimiento de `consideraciones.md`).
- **Filtros j/i locales**: cambiar la vista no re-simula.
- **`trunc2` = truncar, nunca redondear**: requerimiento del enunciado.
- **Round-robin sin RNG** para asignar terminales a empleados: reparto determinista y
  reproducible.
- **`col = emp_id`**: una columna por empleado que efectivamente entró al sistema.
- **Simulación en hilo aparte**: la UI no se congela durante corridas largas.

---

## Estado de Git

- Remote: `origin = https://github.com/ezequias12/TP-SIM.git`, rama `main` (sin token
  embebido — el problema de seguridad de versiones anteriores quedó resuelto).
- La migración a PyQt5 está en el commit `e9fcf34`; el técnico que nunca entra a la cola de
  empleados, en `c36ea68`.
