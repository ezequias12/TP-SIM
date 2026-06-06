# Contexto completo — TP4 Simulación de Colas (Grupo 22)

> **Documento de traspaso (handoff).** Refleja el estado del proyecto al cierre de la
> última sesión. Pensado para retomar el trabajo en otra sesión sin perder contexto.

---

## Descripción del trabajo

Simulación de eventos discretos (DES) para el sistema de registro dactilar de la
Municipalidad de Río Cuarto. Es una **aplicación de escritorio PyQt5** compuesta por
tres archivos de código:

| Archivo | Rol |
|---|---|
| `simulacion.py` | Lógica pura de simulación DES. Sin Flask, sin numpy, sin UI. |
| `main.py` | Frontend PyQt5: carga el `.ui`, modelos virtuales, hilo de simulación, colores, filtros. |
| `main.ui` | Layout visual en formato Qt Designer (XML). Define los widgets y márgenes. |

Archivos de documentación en `docs/`: `contexto.md` (este archivo), `enunciado.txt`.

---

## Cómo correr

```bash
pip install PyQt5
cd TP-SIM
python3 main.py
```

Sin Flask, sin servidor HTTP, sin npm. La app es una ventana de escritorio nativa.

---

## Estado de Git

- **Repo**: `TP2/TP-SIM/` → remote `origin = ezequias12/TP-SIM`, rama `main`.
  (Hay un repo "exterior" en `TP2/` rama `master` que trata a `TP-SIM` como gitlink.
  **Siempre operar git parado dentro de `TP-SIM/`** para no tocar el repo exterior.)
- **Último commit pusheado**: `c36ea68` — "Corregir lógica del técnico: nunca entra en la cola de empleados"
- ⚠️ **Regla acordada**: nunca hacer push sin que el usuario lo pida explícitamente.

---

## Sistema simulado

- **4 terminales** de registro dactilar.
- **Empleados** llegan con distribución exponencial negativa (media configurable, default 2 min).
- **Técnico de mantenimiento** llega cada ~60 min (uniforme, rango configurable, default 57–63 min).
- **Tiempo de atención** de empleado: uniforme \[ATN_MIN, ATN_MAX\] (default 5–8 min).
- **Tiempo de mantenimiento** por terminal: uniforme \[MANT_MIN, MANT_MAX\] (default 3–10 min).
- **Cola máxima**: MAX_COLA empleados (default 5). Si llega con la cola llena → RT (rechazado total).
- Simulación corre hasta `tiempo_max` O hasta 100.000 filas (lo que ocurra primero).

---

## Parámetros configurables desde la UI

| Parámetro | Variable Python | Default |
|---|---|---|
| Media llegada empleado (min) | `MEDIA_LLEGADA_EMP` | 2.0 |
| Máx. en cola | `MAX_COLA` | 5 |
| Atención mín (min) | `ATN_MIN` | 5 |
| Atención máx (min) | `ATN_MAX` | 8 |
| Mantenim. mín (min) | `MANT_MIN` | 3 |
| Mantenim. máx (min) | `MANT_MAX` | 10 |
| Técnico entre-llegada mín (min) | `TEC_MIN` | 57 |
| Técnico entre-llegada máx (min) | `TEC_MAX` | 63 |
| Tiempo máximo simulación (min) | `tiempo_max` en `simular()` | 480 |

---

## simulacion.py — estructura y lógica

### Dependencias
Solo stdlib: `math`, `random`, `heapq`. Sin Flask, sin numpy, sin dependencias externas.

### Constantes y estado global

```python
MAX_COLA          = 5
MAX_ITER          = 99999   # init ocupa fila 0, eventos 1..99999 → 100.000 filas
MEDIA_LLEGADA_EMP = 2.0
ATN_MIN, ATN_MAX   = 5, 8
MANT_MIN, MANT_MAX = 3, 10
TEC_MIN, TEC_MAX   = 57, 63
```

Estado global (reseteable con `resetear_estado()`):
`terminales`, `tecnico`, `cola`, `empleados`, `eventos`, `reloj`, `iteracion`,
`id_emp_contador`, `contador_atendidos`, `contador_rt`, `contador_llegaron`,
`acum_espera`, `vector_estado`, `ultimo_idx_terminal`, `_seq`.

### Cola de eventos — heapq

```python
# Evento = (tiempo, seq, tipo, id)
# seq es monótono → desempata eventos simultáneos por orden de inserción
def push_evento(tiempo, tipo, eid=None): ...
def siguiente_evento(): return heapq.heappop(eventos)
```

O(log n) por inserción/extracción. 2× más rápido que el antiguo min() lineal.

### Distribuciones

```python
def trunc2(x): return int(x * 100) / 100   # truncar, NUNCA redondear

def gen_llegada_emp():    # exponencial negativa
def gen_atencion():       # uniforme [ATN_MIN, ATN_MAX]
def gen_mantenimiento():  # uniforme [MANT_MIN, MANT_MAX]
def gen_llegada_tec():    # uniforme [TEC_MIN, TEC_MAX]
```

### Asignación de terminales a empleados — round-robin

`terminal_libre_para_emp()` rota usando `ultimo_idx_terminal` (sin RNG).
Primera asignación parte desde Terminal 1 (puntero resetea a -1).
Solo aplica a empleados; el técnico usa `terminal_libre_con_pendiente()`.

### Estados

- **Terminal**: `"Libre"`, `"Ocupada"`, `"Siendo mantenida"`.
- **Técnico**: `"Descansando"`, `"Esperando Terminal Libre"`, `"Realizando Mantenimiento"`.
- **Empleado**: `"EA"` (esperando atención), `"SA"` (siendo atendido), `"AT"` (terminó, visible solo en la fila de su Fin Atención, luego se borra del dict).

### Lógica del técnico — IMPORTANTE

**El técnico NUNCA entra en la cola de empleados.** Tiene su propio estado independiente.

- Cuando llega y hay terminal libre con pendiente → va directo (`asignar_tecnico_a_terminal`).
- Cuando llega y todas las terminales con pendiente están ocupadas → `tecnico["estado"] = "Esperando Terminal Libre"`. Nada más. La cola no se toca.
- Cuando se libera una terminal (`Fin Atención` o tras `Fin Mantenimiento`), `atender_cola_con_terminal` verifica:
  1. Si `tecnico["estado"] == "Esperando Terminal Libre"` **y** `terminal["pendiente"] == True` → técnico tiene prioridad.
  2. Si no → primer empleado en cola.
  3. Si la cola está vacía → terminal queda Libre.

### `procesar_fin_manten` — lógica de ronda

1. Hay terminal libre con `pendiente=True` → técnico va directo a ella; libera la actual para empleados.
2. Hay terminal ocupada con `pendiente=True` → técnico pasa a `"Esperando Terminal Libre"`; libera la actual para empleados.
3. Ninguna pendiente → **ronda completa**: resetea todas a `pendiente=True`, técnico descansa, programa próxima llegada.

### Almacenamiento compacto del vector de estado

`guardar_fila()` guarda valores **crudos** (sin formatear). El formateo se hace solo al
momento de mostrar celdas visibles (en `SimModel._text`). Esto reduce la memoria ~46%.

```python
vector_estado.append({
    "num":      len(vector_estado),
    "reloj":    reloj,               # float crudo
    "evento":   evento_nombre,
    "prox_emp": tiempo_de("llegada_emp"),   # float|None
    "prox_tec": tiempo_de("llegada_tec"),
    "term_est":  [t["estado"]    for t in terminales],   # lista de 4 strings
    "term_pend": [t["pendiente"] for t in terminales],   # lista de 4 bools
    "term_fin":  [t["fin_aten"]  for t in terminales],   # lista de 4 float|None
    "fin_mant":  tecnico["fin_manten"],
    "tec_est":   tecnico["estado"],
    "tec_term":  tecnico["terminal_id"],
    "cola":      len(cola),          # solo empleados (técnico nunca está en cola)
    "n_at":      contador_atendidos,
    "n_rt":      contador_rt,
    "n_lleg":    contador_llegaron,  # exacto: se incrementa en cada Llegada Empleado
    "acum_esp":  acum_espera,
    "rnd_le": ..., "t_le": ...,     # RNDs de llegada empleado
    "rnd_at": ..., "t_at": ...,     # RNDs de atención
    "rnd_lt": ..., "t_lt": ...,     # RNDs de llegada técnico
    "rnd_mt": ..., "t_mt": ...,     # RNDs de mantenimiento
    "emp":    snapshot_empleados(),  # dict {col: (estado, hora_inicio_esp, hora_llegada, terminal_id)}
})
```

`snapshot_empleados()` retorna un **dict** (no lista) `{col → tupla}` para acceso O(1) por columna.
Los empleados rechazados (RT) nunca entran al dict `empleados` → no generan columna.

### Estadísticas finales

- `total_llegaron = contador_llegaron` (exacto, no `atendidos + RT` que omitía los actualmente en atención)
- `pct_rt = (n_rt / n_lleg) * 100`
- `prom_espera = acum_espera / n_at`

---

## main.py — estructura y lógica

### Stack
PyQt5 puro. Sin npm, sin React, sin servidor HTTP. La UI es una ventana nativa.

### Constantes

```python
N_FROZEN = 3   # columnas #/Reloj/Evento siempre fijas a la izquierda
```

### COLS — columnas estáticas (34 en total)

Lista de tuplas `(clave_en_fila, encabezado_visible)`. Las claves mapean directamente
a las keys del dict de cada fila del vector de estado.

Grupos y colores del encabezado agrupado:
| Grupo | Color fondo | Columnas |
|---|---|---|
| (sin grupo, full height) | `#1e1e2e` | `#`, `Reloj`, `Evento` |
| Llegada Empleado | `#a6e3a1` verde | RND, T. Entrada, Próx. Evento |
| Llegada Técnico | `#f9e2af` amarillo | RND, T. Entrada, Próx. Evento |
| Fin Atención | `#fab387` naranja | RND, T. Atención, Fin At. 1-4 |
| Fin Mantenimiento | `#f38ba8` rojo | RND, T. Mantenim., Fin Mantenim. |
| Terminal 1..4 | `#89dceb` cyan | Estado, Pendiente |
| Cola | `#b4befe` lavanda | Cola |
| Técnico | `#cba6f7` mauve | Estado, Terminal |
| Estadísticas | `#89b4fa` azul | Atendidos, Se fueron (RT), % RT, Acum. Espera, Prom. Espera |
| Empleado N (dinámico) | `#cba6f7` mauve | Estado, Hora inicio, Terminal |

### SimModel — modelo virtual (QAbstractTableModel)

Solo formatea las celdas que el QTableView solicita pintar (las visibles en pantalla).
Para 100.000 filas, en vez de crear millones de QTableWidgetItem, el modelo retorna
el texto/color de cada celda bajo demanda en `data(index, role)`.

```python
def set_content(self, rows, cols):
    # rows = subconjunto filtrado del vector_estado
    # cols = COLS + emp_cols (dinámicas según empleados visibles)

def data(self, index, role):
    # DisplayRole → _text(fila, col)  [solo formatea lo visible]
    # ForegroundRole → color según estado
```

`_spec(key)` precomputa cómo leer cada columna (evita if/else en cada render).

### GroupedHeader — encabezado de dos niveles

`QHeaderView` personalizado que pinta:
- **Fila superior**: grupo coloreado (span de N columnas)
- **Fila inferior**: nombre individual de columna
- Columnas sin grupo (`name=""`): nombre a altura completa (sin divisor horizontal)
- Culling de viewport: solo pinta grupos que intersectan el área visible → scroll fluido

### SimWorker + QThread

La simulación corre en un `QThread` separado. La UI no se bloquea.
- `btn_simular` se deshabilita mientras simula + barra de progreso visible.
- `worker.finished` → `_on_sim_done()` actualiza la UI con los resultados.
- `thread.finished` → `_on_thread_done()` hace el cleanup (deleteLater) de worker y thread.
- Las referencias `self._thread` y `self._worker` se nullifican en `_on_thread_done()` para evitar el crash "QThread: Destroyed while thread is still running" al re-simular.

### Panel frozen (columnas fijas)

`_frozen` es un `QTableView` separado colocado a la **izquierda** de `tbl_vector` en un
`QHBoxLayout`. Comparte el mismo `SimModel` y el mismo `selectionModel`.

- Muestra solo las primeras `N_FROZEN` (3) columnas: `#`, `Reloj`, `Evento`.
- `tbl_vector` oculta esas 3 columnas → no hay duplicación visual.
- Scrollbars verticales sincronizadas bidireccionalmente.
- Al arrastrar el ancho de una columna frozen, `_on_frozen_col_resized` actualiza el ancho fijo del panel.

### Filtrado j/i — instantáneo

```python
start = bisect.bisect_left(self._relojes, j)   # O(log n)
filas = self.todas_filas[start : start + i]
```

`_relojes` es la columna `reloj` precomputada al terminar la simulación (lista ascendente).
El filtro no re-simula nada, solo actualiza el slice visible del modelo.

### Tabla de última fila

`tbl_ultima` es un `QTableView` separado con altura fija 96px que siempre muestra la
última fila de la simulación completa (no afectada por los filtros j/i).
Sin columnas de empleados (los empleados activos al corte son estado transitorio).

### Tarjetas de estadísticas

7 `QFrame` creados programáticamente en `QHBoxLayout(self.pnl_stats)`.
Cada tarjeta: label nombre (#6c7086, 10px) + label valor (#cba6f7, 16px bold).

Estadísticas mostradas:
- Total llegaron (`n_lleg` = `contador_llegaron`, exacto)
- Atendidos, Se fueron (RT), % que se van
- Prom. espera (min), Iteraciones, Tiempo simulado (min)

### Copiar a Excel

`on_copiar()` genera TSV (tab-separado) con encabezados + todas las filas visibles
según el filtro actual. Incluye columnas frozen. Listo para pegar con Ctrl+V en Excel.

---

## main.ui — layout

```
QMainWindow
  centralwidget
    layout_main (QVBoxLayout, márgenes 16px, spacing 10px)
      lbl_titulo, lbl_subtitulo
      line (separador)
      grp_params (QGroupBox, QGridLayout, márgenes 8px, spacing 6px)
        — 8 pares label+QLineEdit (parámetros del sistema)
      grp_sim (QGroupBox, QHBoxLayout, márgenes 8px)
        — txt_tiempo_max, btn_simular, prg_sim (barra progreso, hidden por defecto), lbl_info
      line2 (separador)
      grp_vis (QGroupBox, QHBoxLayout, márgenes 8px)
        — txt_hora_desde, txt_cant_filas, btn_copiar, lbl_filtro
      [container QWidget con QHBoxLayout]
        _frozen (QTableView, frozen panel, ancho fijo)
        tbl_vector (QTableView, tabla principal, expande)
      lbl_ultima
      tbl_ultima (QTableView, altura fija 96px)
      pnl_stats (QFrame, QHBoxLayout con 7 tarjetas creadas en Python)
```

---

## Colores (stylesheet DARK — Catppuccin Mocha)

```
Fondo principal   #1e1e2e
Superficie        #313244 / #181825
Texto principal   #cdd6f4
Texto secundario  #9399b2
Acento (mauve)    #cba6f7
Verde             #a6e3a1
Amarillo          #f9e2af
Naranja           #fab387
Rojo/rosa         #f38ba8
Cyan              #89dceb
Lavanda           #b4befe
Azul              #89b4fa
```

Colores por estado:
- Terminal Libre → cyan, Ocupada → naranja, Siendo mantenida → rojo
- Técnico Descansando → gris, ETL → amarillo, Realizando Mantenimiento → rojo
- Empleado EA → amarillo, SA → verde, AT → rojo (muestra "x")

---

## Decisiones de diseño clave

- **`trunc2` = truncar, nunca redondear**: requerimiento del enunciado.
- **`col = emp_id`**: una columna por empleado que entró al sistema. Los RT no generan columna.
- **Técnico nunca en cola**: estado independiente. La `cola` contiene solo empleados.
- **`total_llegaron = contador_llegaron`**: exacto. No calcular como `atendidos + RT` (omite los siendo atendidos al corte).
- **Round-robin sin RNG**: reparto determinista de terminales a empleados.
- **Backend retorna todo**: `j` e `i` son filtros de visualización, no re-simulan.
- **Valores crudos en vector_estado**: el formateo se hace solo al pintar celdas visibles.
- **heapq para eventos**: O(log n) en vez de O(n) del antiguo min() lineal.
