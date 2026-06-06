# Documentación técnica — TP4 Simulación de Colas

> Sistema de registro dactilar de la Municipalidad de Río Cuarto, resuelto con una
> **simulación de eventos discretos (DES)**. Este documento explica, paso a paso, cómo
> funciona el código: la generación de números aleatorios, el truncado, la cola de
> eventos, el flujo completo del empleado y del técnico, las prioridades, las
> estadísticas y la interfaz gráfica.

---

## Índice

1. [Arquitectura general](#1-arquitectura-general)
2. [Qué es una simulación de eventos discretos](#2-qué-es-una-simulación-de-eventos-discretos)
3. [Constantes y parámetros del sistema](#3-constantes-y-parámetros-del-sistema)
4. [Generación de números aleatorios](#4-generación-de-números-aleatorios)
5. [Truncado a 2 decimales (`trunc2`)](#5-truncado-a-2-decimales-trunc2)
6. [La cola de eventos (heap)](#6-la-cola-de-eventos-heap)
7. [Estado global y estructuras de datos](#7-estado-global-y-estructuras-de-datos)
8. [Estados posibles de cada entidad](#8-estados-posibles-de-cada-entidad)
9. [Funciones de asignación de terminales](#9-funciones-de-asignación-de-terminales)
10. [Prioridad técnico vs. empleado](#10-prioridad-técnico-vs-empleado)
11. [Flujo completo del EMPLEADO](#11-flujo-completo-del-empleado)
12. [Flujo completo del TÉCNICO](#12-flujo-completo-del-técnico)
13. [Los cuatro procesadores de evento](#13-los-cuatro-procesadores-de-evento)
14. [El loop principal](#14-el-loop-principal)
15. [El vector de estado y el snapshot](#15-el-vector-de-estado-y-el-snapshot)
16. [Cálculo de estadísticas](#16-cálculo-de-estadísticas)
17. [La interfaz gráfica (main.py)](#17-la-interfaz-gráfica-mainpy)
18. [Desviaciones del enunciado (decididas a propósito)](#18-desviaciones-del-enunciado-decididas-a-propósito)
19. [Glosario de columnas del vector de estado](#19-glosario-de-columnas-del-vector-de-estado)
20. [Ejemplo numérico paso a paso](#20-ejemplo-numérico-paso-a-paso)

---

## 1. Arquitectura general

El proyecto tiene **una separación estricta entre lógica y presentación**:

| Archivo | Responsabilidad |
|---|---|
| `simulacion.py` | **Toda** la lógica DES. No importa nada de PyQt. Es Python puro: genera los aleatorios, maneja la cola de eventos, calcula los tiempos y produce el *vector de estado* (la lista de filas). |
| `main.py` | **Solo** la interfaz gráfica (PyQt5). Lee los parámetros de la pantalla, corre la simulación en un hilo aparte, y muestra el vector de estado en una tabla con scroll, encabezados agrupados y columnas congeladas. |
| `main.ui` | Layout de la ventana (XML de Qt Designer), cargado con `uic.loadUi`. |

Esta separación permite probar la lógica sin abrir la ventana, y cambiar la UI sin tocar
la simulación. `main.py` se comunica con `simulacion.py` sobreescribiendo sus variables
globales (parámetros) y leyendo `sim.vector_estado` cuando termina.

---

## 2. Qué es una simulación de eventos discretos

En una DES el tiempo **no avanza de a pasos fijos**, sino que **salta de evento en
evento**. Hay un único "reloj" (`reloj`) que toma el valor del próximo evento más
cercano. Entre dos eventos no pasa nada relevante, así que no hace falta simular esos
instantes intermedios.

Los **cuatro tipos de evento** del sistema son:

1. `llegada_emp` — llega un empleado a registrarse.
2. `fin_atencion` — una terminal termina de registrar a un empleado.
3. `llegada_tec` — el técnico llega (o vuelve) a hacer mantenimiento.
4. `fin_manten` — el técnico termina de mantener una terminal.

El motor (`simular`) repite este ciclo:

1. Saca de la cola el evento con menor tiempo.
2. Adelanta el reloj a ese tiempo.
3. Ejecuta el procesador correspondiente (que puede crear nuevos eventos futuros).
4. Guarda una fila en el vector de estado (una "foto" del sistema tras el evento).

Cada vuelta del `while` = un evento procesado = una fila en la tabla.

---

## 3. Constantes y parámetros del sistema

Definidos al inicio de `simulacion.py:5-11`:

```python
MAX_COLA          = 5        # capacidad de la cola de espera
MAX_ITER          = 99999    # tope de eventos (fila 0 = init + 99.999 = 100.000 filas)
MEDIA_LLEGADA_EMP = 2.0      # media de la exponencial de llegada de empleados (min)
ATN_MIN,  ATN_MAX  = 5, 8    # rango uniforme del tiempo de atención (min)
MANT_MIN, MANT_MAX = 3, 10   # rango uniforme del tiempo de mantenimiento (min)
TEC_MIN,  TEC_MAX  = 57, 63  # rango uniforme del intervalo de regreso del técnico (min)
```

Todos son **configurables desde la GUI**: al apretar "Simular", `main.py` los sobreescribe
con lo que haya en los campos de texto (`SimWorker.run`, `main.py:290-296`). El
`tiempo_max` (cuánto dura la corrida) se pasa como argumento a `simular()`.

> **Por qué 57–63:** el enunciado dice que el técnico vuelve "1 hora ± 3 minutos", es
> decir 60 ± 3 = uniforme entre 57 y 63 minutos.

---

## 4. Generación de números aleatorios

Toda variable aleatoria se genera con `random.random()`, que devuelve un `float` uniforme
en `[0, 1)`. A ese RND se le aplica el **método de la transformada inversa** para obtener
la distribución pedida.

### 4.1. Llegada de empleados — Exponencial negativa

`simulacion.py:36-39`:

```python
def gen_llegada_emp():
    rnd = random.random()
    t = trunc2(-MEDIA_LLEGADA_EMP * math.log(1 - rnd))
    return rnd, t
```

La exponencial de media `μ` tiene función de distribución acumulada
`F(x) = 1 − e^(−x/μ)`. Despejando `x` en `F(x) = rnd`:

```
rnd = 1 − e^(−x/μ)
e^(−x/μ) = 1 − rnd
−x/μ = ln(1 − rnd)
x = −μ · ln(1 − rnd)
```

Por eso la fórmula es `-MEDIA_LLEGADA_EMP * math.log(1 - rnd)` (`math.log` es el logaritmo
natural). Se usa `1 - rnd` y no `rnd` para evitar `ln(0)` cuando `rnd = 0` (la exponencial
así nunca rompe). El resultado es el **tiempo entre llegadas**; el evento de la próxima
llegada se agenda en `reloj + ese tiempo`.

### 4.2. Tiempos uniformes — Atención, mantenimiento, regreso del técnico

`simulacion.py:42-57`:

```python
def gen_atencion():        # uniforme [ATN_MIN, ATN_MAX]
    rnd = random.random()
    t = trunc2(ATN_MIN + rnd * (ATN_MAX - ATN_MIN))
    return rnd, t

def gen_mantenimiento():   # uniforme [MANT_MIN, MANT_MAX]
def gen_llegada_tec():     # uniforme [TEC_MIN, TEC_MAX]
```

Una uniforme en `[a, b]` se obtiene con `a + rnd · (b − a)`. Si `rnd = 0` da `a`; si
`rnd → 1` da `b`. Las tres funciones uniformes siguen exactamente este patrón, solo
cambian los límites.

### 4.3. Cada función devuelve `(rnd, tiempo)`

Todas retornan **la tupla `(rnd, tiempo)`**, no solo el tiempo. Esto es deliberado: el RND
crudo se guarda en la fila del vector de estado para que el profesor pueda **verificar a
mano** que el tiempo calculado corresponde a ese RND. Sin el RND visible, la tabla no se
podría auditar.

> **Importante — un RND por terminal mantenida:** `gen_mantenimiento()` se llama **cada
> vez** que el técnico empieza a mantener una terminal (no una vez por ronda). Si en una
> ronda mantiene 4 terminales, se generan 4 RND de mantenimiento distintos.

---

## 5. Truncado a 2 decimales (`trunc2`)

`simulacion.py:32-33`:

```python
def trunc2(x):
    return int(x * 100) / 100
```

El enunciado exige **truncar, nunca redondear**. `int()` en Python trunca hacia cero, así
que `int(x * 100) / 100` corta en el segundo decimal sin redondear:

- `trunc2(5.678)` → `int(567.8)/100` → `567/100` → `5.67` (no `5.68`).

Se aplica al **valor de cada variable aleatoria** apenas se genera (dentro de los `gen_*`).

### 5.1. Truncado vs. redondeo del reloj

Hay que distinguir dos cosas:

- **Los tiempos aleatorios** (duraciones) se **truncan** con `trunc2`, como pide el
  enunciado.
- **Los instantes absolutos del reloj** (cuándo ocurre un evento) se calculan como
  `round(reloj + duración, 2)` — por ejemplo `asignar_empleado_a_terminal` en
  `simulacion.py:147`: `fin = round(reloj + t_a, 2)`. Acá `round` se usa **solo para
  limpiar el error de representación binaria del `float`** (evitar que `2.1 + 0.2` quede
  `2.3000000000000003`), no para alterar la variable aleatoria, que ya venía truncada.

### 5.2. Truncado en la visualización

En la GUI, al mostrar, se vuelve a truncar por las dudas (`main.py:104-105`):

```python
def trunc2_str(v):
    return str(math.floor(v * 100 + 1e-9) / 100)
```

Usa `math.floor` con un `+1e-9` (épsilon) para que un valor como `5.670000001`, que en
realidad debería ser `5.67`, no se caiga a `5.66` por el error del `float`. Es truncado,
no redondeo.

---

## 6. La cola de eventos (heap)

Los eventos futuros se guardan en un **heap binario** (`heapq`), que mantiene siempre el
menor arriba con costo `O(log n)` por inserción/extracción.

`simulacion.py:64-71`:

```python
def push_evento(tiempo, tipo, eid=None):
    global _seq
    heapq.heappush(eventos, (tiempo, _seq, tipo, eid))
    _seq += 1

def siguiente_evento():
    return heapq.heappop(eventos)
```

Cada evento es la tupla **`(tiempo, seq, tipo, eid)`**:

- `tiempo` — instante absoluto en que ocurre (clave de orden principal).
- `seq` — contador monótono que **desempata** cuando dos eventos caen en el mismo tiempo.
  Garantiza orden FIFO de inserción y resultados reproducibles (sin `seq`, Python intentaría
  comparar el campo siguiente, `tipo`, que es un string, dando un orden arbitrario y a veces
  un `TypeError`).
- `tipo` — `"llegada_emp"`, `"fin_atencion"`, `"llegada_tec"` o `"fin_manten"`.
- `eid` — id de la terminal asociada (para `fin_atencion` y `fin_manten`); `None` para las
  llegadas.

### 6.1. `tiempo_de(tipo)` — para las columnas "Próx. Evento"

`simulacion.py:74-76`:

```python
def tiempo_de(tipo):
    tiempos = [e[0] for e in eventos if e[2] == tipo]
    return min(tiempos) if tiempos else None
```

Devuelve el **próximo** tiempo agendado de un tipo dado. Se usa para llenar las columnas
"Próx. Evento" de Llegada Empleado y Llegada Técnico, que muestran *cuándo* está agendada
la siguiente llegada. En todo momento hay como mucho **una** `llegada_emp` y **una**
`llegada_tec` pendientes (cada una se reagenda al procesarse), mientras que puede haber
hasta **cuatro** `fin_atencion` (una por terminal ocupada) y una `fin_manten`.

---

## 7. Estado global y estructuras de datos

Todo el estado vive en variables globales de `simulacion.py:13-28`, reseteables con
`resetear_estado()` (`simulacion.py:361-384`). Esto permite correr la simulación de nuevo
desde cero sin reiniciar el proceso.

### 7.1. Terminal

```python
{"id": i, "estado": "Libre", "pendiente": True, "fin_aten": None, "emp_id": None}
```

- `id` — 1 a 4.
- `estado` — `"Libre"`, `"Ocupada"` o `"Siendo mantenida"`.
- `pendiente` — `True` si todavía le falta mantenimiento en la ronda actual del técnico.
- `fin_aten` — instante en que termina la atención en curso (o `None`).
- `emp_id` — id del empleado que está atendiendo (o `None`).

### 7.2. Técnico

```python
{"estado": "Descansando", "terminal_id": None, "fin_manten": None}
```

- `estado` — `"Descansando"`, `"Esperando Terminal Libre"` o `"Realizando Mantenimiento"`.
- `terminal_id` — terminal que está manteniendo (o `None`).
- `fin_manten` — instante en que termina el mantenimiento en curso (o `None`).

### 7.3. Empleado

```python
{"id": emp_id, "col": emp_id, "estado": "EA", "hora_llegada": reloj,
 "hora_inicio_esp": None, "hora_asignacion": None, "terminal_id": None}
```

- `id` / `col` — número de llegada (1, 2, 3…). `col` define la columna en la tabla.
- `estado` — `"EA"` (esperando atención), `"SA"` (siendo atendido) o `"AT"` (terminó).
- `hora_llegada` — cuándo llegó.
- `hora_inicio_esp` — cuándo entró a la **cola**. Es `None` si fue directo a una terminal
  libre (no esperó). **Esta es la clave del cálculo de espera.**
- `hora_asignacion` — cuándo una terminal lo empezó a atender.
- `terminal_id` — en qué terminal lo atienden (o `None` si está en cola).

### 7.4. Cola y contadores

- `cola` — lista FIFO que contiene **solo empleados** (`{"tipo": "empleado", "id": …}`). El
  técnico **nunca** entra a esta cola; espera en su propio estado.
- `contador_llegaron`, `contador_atendidos`, `contador_rt` — totales.
- `acum_espera` — suma de los tiempos de espera (para el promedio).
- `ultimo_idx_terminal` — puntero del **round-robin** de asignación de terminales.
- `vector_estado` — la lista de filas que consume la GUI.

---

## 8. Estados posibles de cada entidad

| Entidad | Estado | Significado |
|---|---|---|
| **Terminal** | `Libre` | Disponible. |
| | `Ocupada` | Registrando a un empleado. |
| | `Siendo mantenida` | El técnico la está manteniendo. |
| **Técnico** | `Descansando` | Fuera del sistema, esperando su próximo regreso. |
| | `Esperando Terminal Libre` | Llegó pero todas las pendientes están ocupadas; espera al costado (NO en la cola de empleados). |
| | `Realizando Mantenimiento` | Manteniendo una terminal. |
| **Empleado** | `EA` | En la cola, esperando atención. |
| | `SA` | Siendo atendido en una terminal. |
| | `AT` | Terminó (se muestra como `"x"` roja en la fila de su Fin Atención, después desaparece). |

---

## 9. Funciones de asignación de terminales

### 9.1. `terminal_libre_para_emp()` — Round-robin (solo empleados)

`simulacion.py:79-87`:

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

En vez de devolver **siempre la primera terminal libre** (lo que saturaría la Terminal 1 y
dejaría casi sin uso a la 4), reparte por turnos: arranca a buscar desde la terminal
**siguiente** a la última asignada, en forma cíclica (`% n`). Si ninguna está libre,
devuelve `None`. No usa RNG → es determinista y reproducible. Se resetea a `-1` para que la
primera asignación de la corrida empiece por la Terminal 1.

### 9.2. `terminal_libre_con_pendiente()` — para el técnico

`simulacion.py:90-94`: devuelve la **primera** terminal que esté `Libre` **y** con
`pendiente = True`. El técnico arranca su mantenimiento por la primera libre que todavía no
mantuvo en la ronda (cumple el "empezando por la primera que esté libre" del enunciado).

### 9.3. `hay_pendiente_ocupada()`

`simulacion.py:97-98`: devuelve `True` si existe alguna terminal **Ocupada** con
`pendiente = True`. Sirve para decidir si el técnico debe esperar (porque hay trabajo
pendiente pero la terminal está ocupada por un empleado) o si la ronda ya terminó.

---

## 10. Prioridad técnico vs. empleado

El corazón de la prioridad está en `atender_cola_con_terminal(terminal)`
(`simulacion.py:175-196`), que se llama **cada vez que una terminal queda libre** (al
terminar una atención o un mantenimiento) para decidir quién la toma:

```python
def atender_cola_con_terminal(terminal):
    # Prioridad 1: técnico esperando y terminal pendiente de mantenimiento
    if tecnico["estado"] == "Esperando Terminal Libre" and terminal["pendiente"]:
        rnd_m, t_m = asignar_tecnico_a_terminal(terminal)
        return {"manten": rnd_m, "t_manten": t_m}

    # Prioridad 2: primer empleado en cola
    if cola:
        emp = cola.pop(0)
        rnd_a, t_a = asignar_empleado_a_terminal(emp["id"], terminal)
        return {"atencion": rnd_a, "t_atencion": t_a}

    # Nadie espera
    terminal["estado"] = "Libre"
    return {}
```

Orden de prioridad al liberarse una terminal:

1. **Técnico** — solo si está esperando (`Esperando Terminal Libre`) **y** esa terminal
   todavía tiene mantenimiento pendiente.
2. **Primer empleado de la cola** (FIFO, `cola.pop(0)`).
3. **Nadie** → la terminal queda `Libre`.

Esto implementa las dos reglas del enunciado a la vez:

- **El técnico tiene prioridad sobre los empleados:** si está esperando, agarra la terminal
  antes que la cola.
- **El técnico no interrumpe un registro:** no "saca" a un empleado de una terminal
  ocupada; solo puede tomar una terminal cuando se libera. Mientras tanto espera en estado
  `Esperando Terminal Libre`.

La función **devuelve un dict con los RND que generó** (`{"manten":…}`, `{"atencion":…}` o
`{}`). Así, cuando un Fin Atención libera una terminal y arranca un mantenimiento o una
nueva atención, esos RND quedan registrados en la fila correspondiente.

---

## 11. Flujo completo del EMPLEADO

### Paso 1 — Llegada (`procesar_llegada_emp`, `simulacion.py:200-234`)

Cuando se procesa un evento `llegada_emp`:

1. Se incrementan `id_emp_contador` y `contador_llegaron`. El nuevo `emp_id` es ese número.
2. Se pide una terminal con `terminal_libre_para_emp()` (round-robin). Hay **tres caminos**:

   **a) Hay terminal libre → atención inmediata.**
   ```python
   empleados[emp_id] = {..., "estado": "EA", "hora_llegada": reloj,
                        "hora_inicio_esp": None, ...}
   asignar_empleado_a_terminal(emp_id, term)
   ```
   `hora_inicio_esp` queda en `None` porque **no esperó** (no entró a la cola). Su espera
   será 0.

   **b) No hay libre pero la cola tiene lugar (`emp_en_cola() < MAX_COLA`) → encola.**
   ```python
   empleados[emp_id] = {..., "estado": "EA", "hora_llegada": reloj,
                        "hora_inicio_esp": reloj, ...}
   cola.append({"tipo": "empleado", "id": emp_id})
   ```
   Acá sí se setea `hora_inicio_esp = reloj`: marca el instante en que **empieza a esperar**.

   **c) La cola está llena → se va (RT).**
   ```python
   contador_rt += 1
   ```
   El empleado **no se agrega** al diccionario `empleados`, así que no ocupa columna en la
   tabla ni aparece en ningún snapshot. (Ver [§18](#18-desviaciones-del-enunciado-decididas-a-propósito):
   en este modelo el rechazado no vuelve.)

3. Pase lo que pase, se agenda la **próxima** llegada de empleado generando un nuevo tiempo
   exponencial y se guarda la fila.

### Paso 2 — Asignación a terminal (`asignar_empleado_a_terminal`, `simulacion.py:145-158`)

```python
rnd_a, t_a = gen_atencion()
fin = round(reloj + t_a, 2)
terminal["estado"] = "Ocupada"
terminal["fin_aten"] = fin
terminal["emp_id"] = emp_id
empleados[emp_id]["estado"] = "SA"
empleados[emp_id]["terminal_id"] = terminal["id"]
empleados[emp_id]["hora_asignacion"] = reloj
push_evento(fin, "fin_atencion", terminal["id"])
```

Genera el tiempo de atención (uniforme 5–8), marca la terminal `Ocupada`, pasa al empleado
a `SA`, guarda **`hora_asignacion = reloj`** (cuándo lo empezaron a atender) y agenda el
evento `fin_atencion` para `reloj + t_a`.

### Paso 3 — Fin de atención (`procesar_fin_atencion`, `simulacion.py:237-259`)

```python
contador_atendidos += 1
if emp_id and emp_id in empleados:
    emp = empleados[emp_id]
    if emp["hora_inicio_esp"] is not None and emp["hora_asignacion"] is not None:
        espera = emp["hora_asignacion"] - emp["hora_inicio_esp"]
        acum_espera = round(acum_espera + espera, 2)
    empleados[emp_id]["estado"] = "AT"        # visible en el snapshot de esta fila

term["emp_id"] = None
term["fin_aten"] = None
rnds = atender_cola_con_terminal(term)        # ¿quién toma la terminal ahora?
guardar_fila(f"Fin Atención T{terminal_id}", rnds)

if emp_id and emp_id in empleados:
    del empleados[emp_id]                     # recién acá se borra del dict
```

Pasos clave:

1. Se suma 1 a `contador_atendidos`.
2. **Cálculo de la espera:** solo se acumula si `hora_inicio_esp is not None`, es decir,
   solo para los empleados que **pasaron por la cola**. La espera es
   `hora_asignacion − hora_inicio_esp` = tiempo que estuvo en la cola. Los que fueron
   directo a terminal tienen `hora_inicio_esp = None` y suman espera 0 (pero igual cuentan
   en el promedio, porque sí incrementaron `contador_atendidos`).
3. El empleado se marca `AT`. **Se guarda la fila antes de borrarlo**, así su `"x"` aparece
   en la fila de su Fin Atención; recién después se hace `del empleados[emp_id]` y deja de
   aparecer en las filas siguientes.
4. La terminal se libera y se reasigna por prioridad con `atender_cola_con_terminal`.

#### Resumen visual del ciclo de vida del empleado

```
llegada_emp
   ├── terminal libre  → SA (atención inmediata, espera 0) ─┐
   ├── cola con lugar  → EA (espera en cola) → SA ──────────┤→ fin_atencion → AT ("x") → borrado
   └── cola llena      → RT (se va, no entra al dict)
```

---

## 12. Flujo completo del TÉCNICO

El técnico hace **rondas**: en cada ronda mantiene **todas** las terminales una vez, después
descansa ~60 minutos y vuelve.

### Paso 1 — Llegada del técnico (`procesar_llegada_tec`, `simulacion.py:262-279`)

```python
term = terminal_libre_con_pendiente()
if term:
    asignar_tecnico_a_terminal(term)                 # arranca a mantener
elif hay_pendiente_ocupada():
    tecnico["estado"] = "Esperando Terminal Libre"   # espera al costado
else:
    # nada pendiente → reagenda su próxima llegada
    rnd_t, t_t = gen_llegada_tec()
    push_evento(round(reloj + t_t, 2), "llegada_tec")
```

Tres casos al llegar:

- **a)** Hay una terminal libre y pendiente → empieza a mantenerla.
- **b)** Todas las pendientes están ocupadas → pasa a `Esperando Terminal Libre`. **No
  entra a la cola de empleados**, espera en su propio estado. Tomará la primera terminal
  que se libere (gracias a la prioridad de [§10](#10-prioridad-técnico-vs-empleado)).
- **c)** No queda nada pendiente → simplemente reagenda su regreso.

### Paso 2 — Asignación del técnico a terminal (`asignar_tecnico_a_terminal`, `simulacion.py:161-172`)

```python
rnd_m, t_m = gen_mantenimiento()
fin = round(reloj + t_m, 2)
terminal["estado"] = "Siendo mantenida"
terminal["pendiente"] = False                # ya no le falta mantenimiento en esta ronda
tecnico["estado"] = "Realizando Mantenimiento"
tecnico["terminal_id"] = terminal["id"]
tecnico["fin_manten"] = fin
push_evento(fin, "fin_manten", terminal["id"])
```

Genera el tiempo de mantenimiento (uniforme 3–10), marca la terminal `Siendo mantenida` y
**`pendiente = False`** (clave: así no la vuelve a mantener en la misma ronda), y agenda el
`fin_manten`.

### Paso 3 — Fin de mantenimiento (`procesar_fin_manten`, `simulacion.py:282-319`)

Acá se decide cómo sigue la ronda. Primero libera al técnico de la terminal actual y busca
la siguiente pendiente (la actual ya quedó `pendiente = False`, así que se excluye sola):

```python
sig_libre   = terminal_libre_con_pendiente()
sig_ocupada = hay_pendiente_ocupada()
```

Tres ramas:

**a) Hay otra terminal libre y pendiente → va directo.**
```python
term_actual["estado"] = "Libre"
atender_cola_con_terminal(term_actual)       # la recién liberada, ¿la toma un empleado?
asignar_tecnico_a_terminal(sig_libre)        # nuevo RND de mantenimiento
```

**b) Quedan pendientes pero todas ocupadas → espera.**
```python
tecnico["estado"] = "Esperando Terminal Libre"
term_actual["estado"] = "Libre"
atender_cola_con_terminal(term_actual)
```

**c) No queda ninguna pendiente → RONDA COMPLETA.**
```python
for t in terminales:
    t["pendiente"] = True                    # se reinicia el ciclo para la próxima ronda
tecnico["estado"] = "Descansando"
rnd_t, t_t = gen_llegada_tec()
push_evento(round(reloj + t_t, 2), "llegada_tec")   # vuelve en 60 ± 3
term_actual["estado"] = "Libre"
atender_cola_con_terminal(term_actual)
```

En la rama **(c)** se cumple lo que pide el enunciado: el técnico **vuelve 60 ± 3 minutos
después de terminar la ÚLTIMA terminal de la ronda**. El temporizador (`gen_llegada_tec`) se
dispara justo cuando se completa la ronda, no antes.

#### Resumen visual del ciclo del técnico

```
llegada_tec
   ├── terminal libre+pendiente → RM (mantiene) ─┐
   └── pendiente pero ocupada   → ETL (espera) ──┤
                                                 ↓
                                          fin_manten
                                             ├── queda otra libre+pendiente   → RM (siguiente)
                                             ├── queda pendiente pero ocupada → ETL
                                             └── nada pendiente → RONDA COMPLETA:
                                                    reinicia pendientes, Descansa,
                                                    reagenda regreso (60 ± 3)
```

---

## 13. Los cuatro procesadores de evento

Resumen de qué hace cada uno y qué eventos nuevos genera:

| Procesador | Qué hace | Eventos que agenda |
|---|---|---|
| `procesar_llegada_emp` | Asigna terminal / encola / rechaza al empleado que llega. | La próxima `llegada_emp`; si atiende, una `fin_atencion`. |
| `procesar_fin_atencion` | Cierra la atención, acumula espera, reasigna la terminal por prioridad. | Posible `fin_atencion` (nuevo empleado) o `fin_manten` (técnico esperando). |
| `procesar_llegada_tec` | Manda al técnico a mantener / esperar / reagendar. | `fin_manten` (si mantiene) o `llegada_tec` (si no había nada pendiente). |
| `procesar_fin_manten` | Avanza la ronda del técnico. | `fin_manten` (siguiente terminal) o `llegada_tec` (al cerrar la ronda); posible `fin_atencion` si un empleado toma la terminal liberada. |

---

## 14. El loop principal

`simular(tiempo_max)` (`simulacion.py:323-358`):

```python
def simular(tiempo_max):
    global reloj, iteracion
    # Primeros eventos: la primera llegada de empleado y la del técnico
    rnd_e, t_e = gen_llegada_emp();  push_evento(t_e, "llegada_emp")
    rnd_t, t_t = gen_llegada_tec();  push_evento(t_t, "llegada_tec")
    guardar_fila("Inicialización", {...})       # fila 0 = estado inicial

    while iteracion < MAX_ITER and reloj < tiempo_max:
        if not eventos:
            break
        tiempo, _, tipo, eid = siguiente_evento()
        reloj = tiempo
        if reloj > tiempo_max:
            break
        if   tipo == "llegada_emp":  procesar_llegada_emp()
        elif tipo == "fin_atencion": procesar_fin_atencion(eid)
        elif tipo == "llegada_tec":  procesar_llegada_tec()
        elif tipo == "fin_manten":   procesar_fin_manten(eid)
        iteracion += 1
    return vector_estado
```

Detalles importantes:

- **Fila de inicialización:** antes del `while` se agenda la primera llegada de cada tipo y
  se guarda la fila "Inicialización" (índice `#0`). Es la "foto" de arranque con los dos
  primeros eventos ya agendados pero todavía nada procesado.
- **Doble condición de corte:** la simulación termina cuando se cumple **lo primero** entre:
  - `reloj >= tiempo_max` (el `X` que carga el usuario), o
  - `iteracion >= MAX_ITER` (99.999 eventos → 100.000 filas con la de init).
- El `if reloj > tiempo_max: break` evita procesar (y mostrar) un evento que cae **después**
  del tiempo límite: el reloj se adelanta pero el evento no se ejecuta.

---

## 15. El vector de estado y el snapshot

### 15.1. `guardar_fila` (`simulacion.py:115-141`)

Cada fila del vector de estado es un diccionario con **valores crudos** (sin formatear):
el reloj, el nombre del evento, los RND y tiempos de las variables que se generaron en ese
evento, el estado de las 4 terminales, el del técnico, el largo de la cola, los contadores y
el snapshot de empleados.

> **Decisión de rendimiento:** la fila guarda números y booleanos crudos, **no strings**.
> El formateo (truncar a 2 decimales, `"SI"/"NO"`, `"-"`, calcular `%RT` y el promedio de
> espera) se hace **en la GUI y solo para las celdas visibles**. Así el loop de simulación
> —que puede generar 100.000 filas— no pierde tiempo armando texto que quizás nunca se vea.

### 15.2. `snapshot_empleados` (`simulacion.py:105-112`)

```python
def snapshot_empleados():
    return {
        emp["col"]: (emp["estado"], emp["hora_inicio_esp"], emp["hora_llegada"], emp["terminal_id"])
        for emp in empleados.values()
    }
```

Devuelve un diccionario `{columna: (estado, hora_inicio_esp, hora_llegada, terminal_id)}`
con **una entrada por empleado vivo** en ese instante. Como los rechazados nunca entran a
`empleados`, nunca aparecen acá. La GUI usa este snapshot para armar dinámicamente las
columnas "Empleado N".

---

## 16. Cálculo de estadísticas

Las dos métricas que pide el enunciado se calculan en `main.py` al terminar
(`_on_sim_done`, `main.py:483-501`), leyendo los contadores de la última fila:

### 16.1. Porcentaje de empleados que se van (RT)

```python
"pct_rt": round(nrt / nl * 100, 2) if nl else 0
```

`nrt` = `contador_rt` (rechazados), `nl` = `contador_llegaron` (total que llegó). Es el
**% de empleados que se van para regresar más tarde** que pide el enunciado.

### 16.2. Tiempo promedio de espera

```python
"prom_espera": round(acum / na, 3) if na else 0
```

`acum` = `acum_espera` (suma de esperas en cola), `na` = `contador_atendidos`. El divisor es
**todos los atendidos**, no solo los que esperaron: por eso el promedio considera "todos los
empleados que estuvieron en el sistema" (los de espera 0 también pesan en el promedio).

> Las mismas dos cuentas se muestran **por fila** en las columnas "% RT" y "Prom. Espera",
> calculadas al vuelo en el modelo (`main.py:181-186`) para reflejar el estado acumulado
> hasta esa fila.

---

## 17. La interfaz gráfica (main.py)

### 17.1. Modelo virtual — `SimModel(QAbstractTableModel)`

En vez de crear un widget por celda (lento y pesado con miles de filas), se usa un
**modelo/vista virtual**: Qt le pide al modelo solo el texto y el color de las celdas
**que están visibles** en pantalla. Métodos clave:

- `data()` — devuelve el texto (`Qt.DisplayRole`) o el color (`Qt.ForegroundRole`) de una
  celda.
- `_spec(key)` — decide **cómo** se lee cada columna (escalar, una de las 4 terminales, %RT,
  promedio, o sub-columna de empleado dinámico) y qué mapa de colores le corresponde.
- `_text()` — extrae el valor crudo de la fila según ese spec.
- `_fmt()` — formatea: trunca floats, `True→"SÍ"`, `False→"NO"`, `None→"-"`.

Este diseño es lo que cumple el requerimiento de la cátedra de **no parpadear** y soportar
muchísimas filas sin paginar.

### 17.2. Encabezado agrupado de 2 niveles — `GroupedHeader(QHeaderView)`

Dibuja a mano (`paintEvent`) dos filas de encabezado: arriba el nombre del grupo coloreado
(Llegada Empleado, Fin Atención, Terminal 1…4, Estadísticas, Empleado N…), abajo el título
de cada columna. Permite agrupar columnas relacionadas bajo un mismo rótulo.

### 17.3. Columnas congeladas — panel "frozen"

Las 3 primeras columnas (**#, Reloj, Evento**) se muestran en un segundo `QTableView`
(`self._frozen`) fijo a la izquierda, que **comparte modelo y selección** con la tabla
principal y tiene el scroll vertical **sincronizado**. Así, al hacer scroll horizontal, esas
columnas de referencia **no se pierden**.

> **Detalle técnico (alineación):** ambas tablas tienen el scroll horizontal en
> `ScrollBarAlwaysOn` y `frameShape = NoFrame`. Esto hace que sus *viewports* midan
> **exactamente** igual de alto, para que el rango de scroll vertical coincida y las filas
> congeladas no se desfasen de las demás al llegar al final de la tabla.

### 17.4. Simulación en hilo aparte — `SimWorker` + `QThread`

La simulación corre en un **hilo separado** (`main.py:283-299`) para que la ventana no se
congele durante corridas largas. Mientras corre, se muestra una barra de progreso
indeterminada; al terminar (`finished`), se vuelca el vector de estado y se refrescan las
tablas y las tarjetas de estadísticas.

### 17.5. Filtros de visualización (no re-simulan) — `update_table`

Los campos **j** (hora desde) e **i** (cantidad de filas) son **filtros de la vista**, no
de la simulación. `update_table` (`main.py:529`) usa `bisect` sobre la lista de relojes
para encontrar la primera fila con `reloj >= j` de forma instantánea, y muestra `i` filas
desde ahí. Cambiar j o i **no vuelve a correr la simulación**: se filtra sobre los datos ya
calculados.

### 17.6. Columnas dinámicas de empleados

Por cada empleado que aparece en las filas visibles (`estado` en `EA`/`SA`/`AT`) se arma un
grupo "Empleado N" con 3 sub-columnas: **Estado, Hora inicio, Terminal**. Cuando el empleado
se va (`AT`), el estado se muestra como `"x"` roja y la hora y la terminal se blanquean a
`"-"` (`main.py:187-194`). Los rechazados nunca generan columna.

### 17.7. Copiar a Excel — `on_copiar`

Vuelca los encabezados + todas las filas visibles como **TSV** (separado por tabs) al
portapapeles, listo para pegar en Excel o una planilla. Cumple el requerimiento "deseable"
de la cátedra de poder copiar la grilla.

---

## 18. Desviaciones del enunciado (decididas a propósito)

Dos puntos se resolvieron con una interpretación distinta a la literal del enunciado. Están
documentados para defenderlos ante la cátedra; cada corrección sería de **una sola línea**.

1. **El empleado rechazado no regresa.** El enunciado dice *"se va y regresa a la media
   hora"*. El código solo incrementa `contador_rt` y **no agenda una re-llegada** a los 30
   minutos (`procesar_llegada_emp`, rama `else`). Se reporta únicamente el porcentaje que se
   va.

2. **Cola máxima = 5 (lectura "5 o más").** El enunciado dice *"más de 5 esperando"*, que
   literalmente permitiría hasta 6 en cola. El código usa `emp_en_cola() < MAX_COLA` con
   `MAX_COLA = 5`, es decir rechaza cuando ya hay 5 esperando (cola máxima 5).

---

## 19. Glosario de columnas del vector de estado

| Grupo | Columnas | Significado |
|---|---|---|
| (fijas) | #, Reloj, Evento | Número de fila, instante del reloj, qué evento ocurrió. |
| Llegada Empleado | RND, T. Entrada, Próx. Evento | RND y tiempo entre llegadas generados; instante de la próxima llegada agendada. |
| Llegada Técnico | RND, T. Entrada, Próx. Evento | Ídem para el regreso del técnico. |
| Fin Atención | RND, T. Atención, Fin At. 1–4 | RND y tiempo de atención; instante de fin de atención de cada terminal. |
| Fin Mantenimiento | RND, T. Mantenim., Fin Mantenim. | RND y tiempo de mantenimiento; instante de fin del mantenimiento en curso. |
| Terminal 1–4 | Estado, Pendiente | Estado de cada terminal y si le falta mantenimiento en la ronda. |
| Cola | Cola | Cantidad de empleados esperando. |
| Técnico | Estado, Terminal | Estado del técnico y terminal que mantiene. |
| Estadísticas | Atendidos, Se fueron (RT), % RT, Acum. Espera, Prom. Espera | Contadores y métricas acumuladas hasta esa fila. |
| Empleado N (dinámico) | Estado, Hora inicio, Terminal | Una columna por empleado (N = su número de llegada). |

---

## 20. Ejemplo numérico paso a paso

Las primeras 13 filas de una corrida **real** del código. Para que sea reproducible se fijó
`random.seed(42)` antes de simular; con cualquier otra corrida los RND cambian pero **la
mecánica es idéntica**. Todos los valores están **truncados a 2 decimales**, tal cual los
muestra la grilla.

### 20.1. Tabla de las primeras 13 filas

| # | Reloj | Evento | RND ll. | T.entr | Próx.E | RND at | T.at | Fin At. (T1–T4) | T1 T2 T3 T4 | Cola | Lleg | Aten | RT |
|--:|--:|---|--:|--:|--:|--:|--:|---|:--:|--:|--:|--:|--:|
| 0 | 0.00 | Inicialización | 0.63 | 2.04 | 2.04 | – | – | – / – / – / – | L L L L | 0 | 0 | 0 | 0 |
| 1 | 2.04 | Llegada Empleado 1 | 0.22 | 0.50 | 2.54 | 0.27 | 5.82 | **7.86** / – / – / – | O L L L | 0 | 1 | 0 | 0 |
| 2 | 2.54 | Llegada Empleado 2 | 0.67 | 2.25 | 4.79 | 0.73 | 7.20 | 7.86 / **9.74** / – / – | O O L L | 0 | 2 | 0 | 0 |
| 3 | 4.79 | Llegada Empleado 3 | 0.08 | 0.18 | 4.97 | 0.89 | 7.67 | 7.86 / 9.74 / **12.46** / – | O O O L | 0 | 3 | 0 | 0 |
| 4 | 4.97 | Llegada Empleado 4 | 0.02 | 0.06 | 5.03 | 0.42 | 6.26 | 7.86 / 9.74 / 12.46 / **11.23** | O O O O | 0 | 4 | 0 | 0 |
| 5 | 5.03 | Llegada Empleado 5 | 0.21 | 0.49 | 5.52 | – | – | 7.86 / 9.74 / 12.46 / 11.23 | O O O O | **1** | 5 | 0 | 0 |
| 6 | 5.52 | Llegada Empleado 6 | 0.50 | 1.40 | 6.92 | – | – | 7.86 / 9.74 / 12.46 / 11.23 | O O O O | **2** | 6 | 0 | 0 |
| 7 | 6.92 | Llegada Empleado 7 | 0.02 | 0.05 | 6.97 | – | – | 7.86 / 9.74 / 12.46 / 11.23 | O O O O | **3** | 7 | 0 | 0 |
| 8 | 6.97 | Llegada Empleado 8 | 0.19 | 0.44 | 7.41 | – | – | 7.86 / 9.74 / 12.46 / 11.23 | O O O O | **4** | 8 | 0 | 0 |
| 9 | 7.41 | Llegada Empleado 9 | 0.64 | 2.09 | 9.50 | – | – | 7.86 / 9.74 / 12.46 / 11.23 | O O O O | **5** | 9 | 0 | 0 |
| 10 | 7.86 | Fin Atención T1 | – | – | 9.50 | 0.54 | 6.63 | **14.49** / 9.74 / 12.46 / 11.23 | O O O O | **4** | 1 | 0 |
| 11 | 9.50 | Llegada Empleado 10 | 0.22 | 0.49 | 9.99 | – | – | 14.49 / 9.74 / 12.46 / 11.23 | O O O O | **5** | 10 | 1 | 0 |
| 12 | 9.74 | Fin Atención T2 | – | – | 9.99 | 0.58 | 6.76 | 14.49 / **16.50** / 12.46 / 11.23 | O O O O | **4** | 2 | 0 |

(L = Libre, O = Ocupada. En negrita lo que cambia en cada fila.)

### 20.2. Narración fila por fila

**Fila #0 — Inicialización (reloj = 0).**
Antes de procesar nada se generan los dos primeros eventos:

- *Llegada de empleado* (exponencial, media 2): el primer `random()` con esta semilla es
  `0.6394…` (se muestra truncado **0.63**).
  `T = trunc2(−2 · ln(1 − 0.6394)) = trunc2(−2 · ln(0.3606)) = trunc2(2.0402) = 2.04`.
  → primera llegada agendada en `0 + 2.04 = 2.04` (columna Próx. = 2.04).
- *Llegada del técnico* (uniforme 57–63): `RND ≈ 0.025` (muestra **0.02**).
  `T = trunc2(57 + 0.025 · 6) = trunc2(57.15) = 57.15`. → técnico vuelve recién en 57.15.

Estado: 4 terminales Libres, cola 0, técnico Descansando.

**Fila #1 — Llegada Empleado 1 (reloj = 2.04).**
Llega el primer empleado. `terminal_libre_para_emp()` arranca el round-robin desde el
puntero `-1`: prueba la terminal `(-1 + 1) % 4 = 0` → **T1 está Libre → se la asigna**
(puntero pasa a 0). Como fue directo a terminal, su `hora_inicio_esp = None` (no espera).

- *Atención* (uniforme 5–8): `RND = 0.27 → T = trunc2(5 + 0.275 · 3) = trunc2(5.82) = 5.82`.
  → se agenda **Fin Atención T1** en `2.04 + 5.82 = 7.86`.
- Se genera la *próxima* llegada: `RND = 0.22 → T = 0.50` → próxima en `2.04 + 0.50 = 2.54`.

**Filas #2, #3, #4 — Empleados 2, 3 y 4.**
Acá se ve el **round-robin** en acción: el puntero va 1 → 2 → 3, así que el Empleado 2 cae en
**T2**, el 3 en **T3** y el 4 en **T4**. Cada uno agenda su propio Fin Atención
(9.74, 12.46 y 11.23). En la fila #4 las 4 terminales quedan **Ocupadas** (`O O O O`).
Notar que ninguno esperó: los 4 fueron directo a una terminal libre.

**Filas #5 a #9 — La cola se llena.**
Desde el Empleado 5, ya no hay terminal libre. Como la cola tiene lugar
(`emp_en_cola() < 5`), cada uno **se encola** y se le guarda `hora_inicio_esp = reloj`:

| Empleado | Entra a la cola en (reloj) | Cola resultante |
|---|---|---|
| 5 | 5.03 | 1 |
| 6 | 5.52 | 2 |
| 7 | 6.92 | 3 |
| 8 | 6.97 | 4 |
| 9 | 7.41 | **5 (llena)** |

En la fila #9 la cola llega a 5. **El próximo empleado que llegue con la cola así será
rechazado (RT).** Estos empleados todavía no suman espera: la espera se contabiliza recién
cuando **terminan** de ser atendidos.

**Fila #10 — Fin Atención T1 (reloj = 7.86).**
El evento más cercano ya no es una llegada (la próxima es a las 9.50), sino el
**Fin Atención de T1** agendado en la fila #1. Qué pasa:

1. Termina el Empleado 1. Como fue atendido **directo** (`hora_inicio_esp = None`), su espera
   es **0** → `Acum. Espera` sigue en 0. `Atendidos` pasa a **1**.
2. T1 se libera y `atender_cola_con_terminal(T1)` decide quién la toma: el técnico está
   Descansando (no esperando), así que **toma al primero de la cola, el Empleado 5**.
   - Atención del Empleado 5: `RND = 0.54 → T = trunc2(5 + 0.543 · 3) = trunc2(6.63) = 6.63`
     → nuevo Fin Atención T1 en `7.86 + 6.63 = 14.49`.
   - La cola baja de 5 a **4**.

> **Dónde aparecerá la primera espera:** el Empleado 5 entró a la cola en 5.03 y empezó a ser
> atendido en 7.86, así que su espera será `7.86 − 5.03 = 2.83`. Pero ese 2.83 se suma a
> `Acum. Espera` **recién cuando el Empleado 5 termine** su atención (alrededor de 14.49), no
> en esta fila. Por eso `Acum. Espera` todavía es 0 en la fila #10.

**Filas #11 y #12 — Sigue el régimen saturado.**
Llega el Empleado 10 (#11) y, como todo sigue ocupado, se encola (cola vuelve a 5). En #12
termina T2 (Empleado 2, espera 0, `Atendidos` = 2), se libera y toma al Empleado 6 de la
cola, agendando su Fin Atención en `9.74 + 6.76 = 16.50`.

### 20.3. Qué deja claro este ejemplo

- **Cómo se genera y trunca cada RND** y cómo se convierte en un tiempo (exponencial y
  uniforme).
- **Cómo avanza el reloj de evento en evento** (saltó 0 → 2.04 → 2.54 → … → 7.86, siempre al
  próximo evento más cercano, no de a pasos fijos).
- **El round-robin** repartiendo Empleados 1–4 entre T1–T4.
- **El llenado de la cola** y el momento exacto en que empieza a esperar cada empleado.
- **La prioridad al liberarse una terminal** (Fin Atención T1 toma al primero de la cola).
- **El criterio de acumulación de la espera** (se cuenta al terminar la atención, no al
  asignar la terminal).

---

> **En síntesis:** `simulacion.py` es un motor DES clásico (reloj + cola de eventos por
> heap) que genera variables aleatorias por transformada inversa, las trunca a 2 decimales,
> y produce un vector de estado fila por fila. `main.py` lo presenta en una grilla virtual
> con encabezados agrupados, columnas congeladas y filtros de visualización, corriendo la
> simulación en un hilo aparte para no trabar la interfaz.
