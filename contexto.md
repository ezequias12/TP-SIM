# Contexto completo — TP4 Simulación de Colas (Grupo 22)

## Descripción del trabajo

Simulación de eventos discretos (DES) para el sistema de registro dactilar de la Municipalidad de Río Cuarto.  
Dos archivos únicamente: `simulacion.py` (backend Flask + lógica DES) e `index.html` (frontend React CDN, sin npm).

---

## Sistema simulado

- **4 terminales** de registro dactilar.
- **Empleados** llegan con distribución exponencial negativa (media configurable, default 2 min).
- **Técnico de mantenimiento** llega cada ~60 min ± 3 min (uniforme, rango configurable, default 57–63 min).
- **Tiempo de atención** de empleado: uniforme entre 5 y 8 min (configurable).
- **Tiempo de mantenimiento** por terminal: uniforme entre 3 y 10 min (configurable).
- **Cola máxima**: 5 empleados (configurable). Si llega cuando cola llena → se va sin volver (RT = "rechazado total").
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
| Tiempo máximo simulación (min) | (parámetro en `simular()`) | 480 |

---

## Archivos

```
simulacion.py   — Flask backend + toda la lógica DES
index.html      — React 18 CDN (Babel standalone) frontend
contexto.md     — este archivo
```

---

## simulacion.py — estructura y lógica

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

Estado global (reseteable): `terminales`, `tecnico`, `cola`, `empleados`, `eventos`, `reloj`, `iteracion`, `id_emp_contador`, `contador_atendidos`, `contador_rt`, `contador_llegaron`, `acum_espera`, `vector_estado`.

### Distribuciones

```python
def trunc2(x):
    return int(x * 100) / 100   # truncar (nunca redondear) a 2 decimales

def gen_llegada_emp():
    rnd = random.random()
    t = trunc2(-MEDIA_LLEGADA_EMP * math.log(1 - rnd))   # exponencial negativa
    return rnd, t

def gen_atencion():
    rnd = random.random()
    t = trunc2(ATN_MIN + rnd * (ATN_MAX - ATN_MIN))       # uniforme
    return rnd, t

def gen_mantenimiento():
    rnd = random.random()
    t = trunc2(MANT_MIN + rnd * (MANT_MAX - MANT_MIN))    # uniforme
    return rnd, t

def gen_llegada_tec():
    rnd = random.random()
    t = trunc2(TEC_MIN + rnd * (TEC_MAX - TEC_MIN))       # uniforme
    return rnd, t
```

### Lógica del técnico (campo `pendiente`)

Cada terminal tiene `pendiente: bool`.  
Al inicializar → todas `pendiente=True`.  
Cuando el técnico termina de mantener TODAS las terminales (ronda completa) → resetea `pendiente=True` en todas y descansa.  
El técnico NO mantiene terminales con `pendiente=False`.

Estados del técnico: `"D"` (descansando), `"ETL"` (esperando terminal libre), `"RM"` (realizando mantenimiento).

### `atender_cola_con_terminal` — lógica crítica

Cuando una terminal queda libre, esta función decide a quién atender:

```python
def atender_cola_con_terminal(terminal):
    if not cola:
        terminal["estado"] = "Libre"
        return None, None

    siguiente = cola[0]

    if siguiente["tipo"] == "tecnico":
        if terminal["pendiente"]:          # SOLO si necesita mantenimiento
            cola.pop(0)
            return asignar_tecnico_a_terminal(terminal)
        else:
            # Terminal ya mantenida — omitir técnico, atender empleados
            for i, item in enumerate(cola):
                if item["tipo"] == "empleado":
                    cola.pop(i)
                    return asignar_empleado_a_terminal(item["id"], terminal)
            terminal["estado"] = "Libre"
            return None, None
    else:
        cola.pop(0)
        return asignar_empleado_a_terminal(siguiente["id"], terminal)
```

**Prioridad**: técnico (solo si `pendiente=True`) > empleado > libre.

### `guardar_fila` — numeración secuencial

```python
"num": len(vector_estado)   # 0=init, 1,2,3... — asignado ANTES del append
```

Guarda además `t_llegada_emp`, `t_llegada_tec`, `t_atencion`, `t_manten` (tiempos generados, no solo RNDs).

### `procesar_fin_manten` — lógica de ronda

1. Busca siguiente terminal libre con `pendiente=True` → va directo.
2. Si no hay libre pero hay ocupada con pendiente → `ETL`, entra a cola en posición 0.
3. Si no hay ninguna pendiente → **ronda completa**: resetea todas a `pendiente=True`, descansa, programa próxima llegada.

### Endpoint Flask

```python
@app.route("/simular", methods=["POST"])
def endpoint_simular():
    # Sobreescribe globales antes de resetear
    MAX_COLA = int(data.get("max_cola", 5))
    MEDIA_LLEGADA_EMP = float(data.get("media_llegada_emp", 2.0))
    # ... etc
    resetear_estado()
    vs = simular(tiempo_max)
    # Retorna TODAS las filas — el frontend filtra por j e i
    return jsonify({"filas": vs, "stats": stats})
```

El backend retorna TODAS las filas. No filtra por j ni i. El frontend hace el filtrado local.

---

## index.html — estructura

### Stack

- React 18 UMD (CDN)
- Babel Standalone para JSX
- Sin npm, sin build step
- Dark theme (Catppuccin Mocha)

### Estado React

Todos los inputs numéricos se guardan como **strings** para evitar el bug de `Number("") = 0` al borrar.  
Se parsean solo en el momento de uso con helpers:

```javascript
const pf = (s, d) => { const n = parseFloat(s);  return isNaN(n) ? d : n; };
const pi = (s, d) => { const n = parseInt(s, 10); return isNaN(n) ? d : n; };
```

### Decoupling simulación / visualización

- `runSim()` hace fetch y guarda TODO en `todasFilas`.
- `j` (hora desde) e `i` (cantidad filas) son filtros locales — NO re-simulan.
- `filas`, `ultima`, `totalDesdeJ` son `useMemo` sobre `todasFilas`.
- Cambiar j o i nunca llama al backend.

### Encabezados agrupados de 2 niveles

Definidos en constante `GRP`:

```javascript
const GRP = [
  { single:true, key:"num",    label:"#",      w:48  },
  { single:true, key:"reloj",  label:"Reloj",  w:68  },
  { single:true, key:"evento", label:"Evento", w:210 },
  { label:"Llegada Empleado",   bg:"#5c3800", fg:"#ffb86c", cols:[
    { key:"rnd_llegada_emp", label:"RND",    w:72 },
    { key:"t_llegada_emp",   label:"T.entr", w:65 },
    { key:"prox_emp",        label:"Próx.",  w:68 },
  ]},
  { label:"Llegada Técnico",    bg:"#5c3800", fg:"#ffb86c", cols:[...] },
  { label:"Fin Atención",       bg:"#4a4000", fg:"#f9e2af", cols:[...] },
  { label:"Fin Mantenimiento",  bg:"#1e4020", fg:"#a6e3a1", cols:[...] },
  { label:"Terminal 1", bg:"#0e3a2a", fg:"#89dceb", cols:[{key:"t1_estado",...},{key:"t1_pend",...}] },
  // Terminal 2, 3, 4 igual
  { single:true, key:"cola_largo", label:"Cola", w:52 },
  { label:"Técnico",      bg:"#30205a", fg:"#cba6f7", cols:[...] },
  { label:"Estadísticas", bg:"#1a2250", fg:"#89b4fa", cols:[...] },
  // Empleado 1..9
  ...[1,2,3,4,5,6,7,8,9].map(n => ({
    label:`Empleado ${n}`, bg:"#0e3a2a", fg:"#a6e3a1",
    cols:[
      { key:`emp${n}_estado`, label:"Estado", w:58, cf:cfEmp },
      { key:`emp${n}_hora`,   label: n<=4 ? "H.Llegada" : "H.Inic.Esp", w:78 },
    ]
  })),
];
```

`single:true` → `rowSpan=2` en fila 1, nada en fila 2.  
Grupos → `colSpan=N` en fila 1, sub-headers en fila 2.

`COLUMNAS` = lista plana derivada de `GRP` para renderizar celdas de datos:

```javascript
const COLUMNAS = GRP.flatMap(g =>
  g.single ? [{ key:g.key, w:g.w, cf:g.cf }] : g.cols
);
```

`buildThead()` construye el `<thead>` con sticky positioning:

```javascript
const ROW1_H = 26;  // px, altura fija fila 1
// singles: top:0, zIndex:9 (si es primera col) o 7
// group headers fila 1: top:0, zIndex:6
// sub-headers fila 2: top:ROW1_H, zIndex:5
// tbody primera col: position:sticky, left:0, zIndex:2
```

`THEAD = buildThead()` — computado una vez a nivel módulo (estructura estática).

### Transformación backend → fila

```javascript
function transformar(f) {
  const row = { ...f };
  (f.terminales || []).forEach(t => {
    row[`t${t.id}_estado`] = t.estado;
    row[`t${t.id}_pend`]   = t.pendiente;
  });
  (f.fin_at || []).forEach((v, i) => { row[`fin_at_${i+1}`] = v; });
  (f.empleados_snap || []).forEach((e, i) => {
    const n = i+1;
    row[`emp${n}_estado`] = e.estado;
    row[`emp${n}_hora`]   = n <= 4 ? e.hora_llegada : e.hora_inicio_esp;
  });
  return row;
}
```

### Truncado en display

```javascript
const display = typeof raw === "number" ? Math.trunc(raw * 100) / 100 : raw;
```

Todos los números se truncan (no redondean) a 2 decimales en pantalla.

---

## Bugs corregidos (historial)

### 1. Doble fila con num=0

**Problema**: `guardar_fila` usaba `"num": iteracion`. La fila de init se guarda con `iteracion=0`, y el primer evento del loop también usa `iteracion=0` (se incrementa después del `guardar_fila`).  
**Fix**: `"num": len(vector_estado)` — índice secuencial asignado antes del append.

### 2. MAX_ITER off-by-one (100.001 filas)

**Problema**: Con `MAX_ITER=100000`, el loop `while iteracion < MAX_ITER` corre 100.000 veces + la fila de init = 100.001 filas.  
**Fix**: `MAX_ITER = 99999` → init (fila 0) + 99.999 eventos = exactamente 100.000 filas máximo.

### 3. Bug de borrado en inputs numéricos

**Problema**: `onChange={e => setState(Number(e.target.value))}` → al borrar el campo queda `Number("") = 0`, React re-renderiza con 0, usuario no puede escribir otro número.  
**Fix**: Todos los estados numéricos almacenados como strings. Se parsean solo al usar con `pf()` / `pi()`.

### 4. Re-mantenimiento incorrecto de terminales

**Problema**: En `procesar_fin_manten`, cuando no había otra terminal pendiente y el técnico entraba a la cola como ETL, luego `atender_cola_con_terminal(term_actual)` asignaba el técnico a esa misma terminal ya mantenida (`pendiente=False`).  
**Fix**: En `atender_cola_con_terminal`, verificar `if terminal["pendiente"]` antes de asignar el técnico. Si `pendiente=False`, saltar al técnico y buscar el primer empleado en la cola.

### 5. Columnas t_* faltantes en backend

**Problema**: `guardar_fila` solo almacenaba los RNDs pero no los tiempos generados (`t_llegada_emp`, `t_llegada_tec`, `t_atencion`, `t_manten`).  
**Fix**: En cada call site de `guardar_fila`, agregar las claves `t_*` al dict `rnds`, y en `guardar_fila` leerlas con `rnds.get("t_llegada_emp", "-")` etc.

### 6. Sticky headers mal aplicados (CSS vs inline style)

**Problema**: Regla CSS `thead th:first-child { position: sticky; left: 0 }` aplicaba sticky-left al primer `<th>` de la fila 2 del thead, no solo a la columna `#`.  
**Fix**: Eliminar esa regla CSS. Manejar todo sticky por inline style dentro de `buildThead()`. Solo el `<th rowSpan=2>` de `#` tiene `left:0`.

---

## Columnas del vector de estado (en orden)

| Grupo | Columnas |
|---|---|
| (single) | #, Reloj, Evento |
| Llegada Empleado | RND, T.entr, Próx. |
| Llegada Técnico | RND, T.entr, Próx. |
| Fin Atención | RND, T.at, At 1, At 2, At 3, At 4 |
| Fin Mantenimiento | RND, T.mant, Fin |
| Terminal 1 | Estado, Pend. |
| Terminal 2 | Estado, Pend. |
| Terminal 3 | Estado, Pend. |
| Terminal 4 | Estado, Pend. |
| (single) | Cola |
| Técnico | Estado, Term. |
| Estadísticas | Aten., RT, % RT, AcumEsp, PromEsp |
| Empleado 1..4 | Estado, H.Llegada |
| Empleado 5..9 | Estado, H.Inic.Esp |

---

## Colores del frontend

Estados de terminal: Libre → cyan (`#89dceb`), Ocupada → naranja (`#fab387`), Siendo mantenida → rojo (`#f38ba8`).  
Estados técnico: D → gris, ETL → amarillo, RM → rojo.  
Estados empleado: SA (siendo atendido) → verde, EA (esperando atención) → amarillo.

Grupos de encabezado:
- Llegada Empleado / Llegada Técnico → naranja oscuro `#5c3800` / `#ffb86c`
- Fin Atención → amarillo oscuro `#4a4000` / `#f9e2af`
- Fin Mantenimiento → verde oscuro `#1e4020` / `#a6e3a1`
- Terminales / Empleados → verde azulado oscuro `#0e3a2a` / `#89dceb` (terminales), `#a6e3a1` (empleados)
- Técnico → violeta oscuro `#30205a` / `#cba6f7`
- Estadísticas → azul oscuro `#1a2250` / `#89b4fa`
- Singles (#, Reloj, Evento, Cola) → `#313244` / `#b4befe`

---

## Cómo correr

```bash
pip install flask flask-cors numpy
python simulacion.py    # corre en localhost:5000
# abrir index.html en el navegador
```

---

## Decisiones de diseño

- **Sin npm/bundler**: React y Babel desde CDN. Abre como `file://` directamente.
- **Backend retorna todo**: El endpoint devuelve todas las filas; `j` e `i` son filtros puramente de visualización en el frontend (sin re-simular).
- **`trunc2` = truncar nunca redondear**: Requerimiento explícito del enunciado. `int(x * 100) / 100` en Python, `Math.trunc(raw * 100) / 100` en JS.
- **`THEAD` estático**: `buildThead()` se llama una vez a nivel módulo. No re-renderiza con el estado.
- **`COLUMNAS` plano**: Derivado de `GRP` para que la definición de grupos sea la única fuente de verdad tanto para headers como para data cells.
- **Empleados snap**: Se guarda snapshot de los primeros 9 empleados activos por fila. Empleados 1-4 muestran hora de llegada; 5-9 muestran hora inicio espera (siguiendo convención del Excel de referencia).
