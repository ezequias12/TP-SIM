# Truncado vs. Redondeo en la simulación

> Documento explicativo. Por qué en `simulacion.py` usamos **`trunc2`** (truncar) en
> unos lugares y **`round`** (redondear) en otros, y por qué eso es correcto y necesario.

---

## TL;DR (resumen de una línea)

- **Variables aleatorias** (los `gen_*`) → se **truncan** con `trunc2`, porque lo exige el enunciado del TP.
- **Cuentas del reloj** (`reloj + duración`, acumulador de espera) → se **redondean** con `round`, para borrar el error de punto flotante y no perder centavos.

> **Truncás lo que el enunciado te obliga a truncar; redondeás las sumas internas para que el float no te robe centavos.**

---

## 1. El problema de fondo: la computadora no guarda los decimales exactos

La computadora guarda los números con decimales en **binario** (base 2), no en decimal.
Muchos números que para nosotros son "redondos" en base 10, en base 2 son **periódicos
infinitos** — igual que `1/3 = 0.3333…` en decimal nunca termina.

Como la memoria es finita, la compu **corta** esa representación infinita y guarda una
aproximación. Por eso:

```python
format(0.29, '.20f')   # → '0.28999999999999998002'
format(0.10, '.20f')   # → '0.10000000000000000555'
format(0.30, '.20f')   # → '0.29999999999999998890'
```

Cuando escribís `0.29`, la compu en realidad guarda `0.28999999999999998…`, un pelín por
**debajo**. No lo ves nunca porque al imprimir Python te lo muestra "lindo" como `0.29`,
pero internamente está ese error minúsculo (en el dígito ~16).

El ejemplo clásico de este fenómeno:

```python
0.1 + 0.2            # → 0.30000000000000004
0.1 + 0.2 == 0.3     # → False
```

⚠️ **Esto NO es un bug de Python.** Pasa igual en Java, C, C++, JavaScript, etc. Es una
limitación física del estándar **IEEE 754** que usan todos los procesadores para los
números con coma flotante (`float`/`double`).

---

## 2. Cómo funciona `trunc2` (la "tijera")

```python
def trunc2(x):
    return int(x * 100) / 100
```

`int()` **corta** la parte decimal hacia abajo, sin mirar lo que viene después. Es como
una tijera: corta en seco y tira el resto.

- `trunc2(7.199)` → `int(719.9) / 100` → `719 / 100` → `7.19`
- `trunc2(7.999)` → `int(799.9) / 100` → `799 / 100` → `7.99`

Nunca redondea hacia arriba. Esto es **exactamente lo que pide el enunciado** para las
variables aleatorias.

---

## 3. Por qué `trunc2` falla al sumar tiempos ya truncados

Acá está el quilombo. Cuando sumás dos números que **ya** tienen 2 decimales, el
resultado puede caer "justo en el borde" y quedar guardado como `…9999998`. La tijera de
`trunc2` se come ese `0.00999…` y te **baja un centavo**.

Casos reales:

```
3.0 + 1.14 = 4.139999999999999...   trunc2 = 4.13  ❌   round = 4.14  ✅
0.0 + 0.29 = 0.289999999999999...   trunc2 = 0.28  ❌   round = 0.29  ✅
```

Paso a paso del primero:

```python
suma          = 3.0 + 1.14          # la compu guarda 4.1399999999999997
suma * 100    = 413.99999999999994
int(suma*100) = 413                 # ← la tijera corta el .9999 y se PIERDE
trunc2(suma)  = 4.13                # ← MAL, deberíamos tener 4.14
round(suma,2) = 4.14                # ← BIEN
```

---

## 4. Por qué `round` lo arregla

```python
round(4.1399999999999997, 2)   # → 4.14
```

`round` no corta a lo bruto: **mira el dígito siguiente y ajusta al valor de 2 decimales
más cercano**. Como el error de float es siempre minúsculo (`4.1399999…` está
pegadísimo a `4.14`), redondear al más cercano **borra ese ruido** y te devuelve el
número que esperabas.

| | Qué hace | Frente a `4.1399999…` |
|---|---|---|
| `trunc2` (tijera) | corta hacia abajo, sin mirar | lo lee como `4.13` → **arrastra el error** |
| `round` (redondeo) | ajusta al más cercano | lo ve cerca de `4.14` → **corrige el error** |

---

## 5. Dónde se usa cada uno en `simulacion.py`

### A) Generar una variable aleatoria → `trunc2`

```python
def gen_llegada_emp():
    rnd = trunc2(random.random())                        # RND truncado a 2 dec (ver §6)
    t = trunc2(-MEDIA_LLEGADA_EMP * math.log(1 - rnd))   # exponencial negativa
    return rnd, t

def gen_atencion():      # uniforme [ATN_MIN, ATN_MAX]
    rnd = trunc2(random.random())
    t = trunc2(ATN_MIN + rnd * (ATN_MAX - ATN_MIN))
    return rnd, t

def gen_mantenimiento(): # uniforme [MANT_MIN, MANT_MAX]
    rnd = trunc2(random.random())
    ...trunc2(...)

def gen_llegada_tec():   # uniforme [TEC_MIN, TEC_MAX]
    rnd = trunc2(random.random())
    ...trunc2(...)
```

**Por qué truncar la variable acá:**

1. Es la convención adoptada para todo el TP: la variable aleatoria se trunca a 2
   decimales, no se redondea.
2. Es un valor recién calculado a partir del RND (no es una suma de cosas ya truncadas),
   así que el "error de borde" del float casi no aparece.

> Notá que el **RND también se trunca a 2 decimales** (`trunc2(random.random())`). El
> porqué de esto es importante y tiene su propia sección: ver **§6**.

### B) Calcular un tiempo del reloj → `round`

```python
fin = round(reloj + t_a, 2)                       # fin de atención
fin = round(reloj + t_m, 2)                       # fin de mantenimiento
espera      = round(reloj - emp["hora_inicio_espera"], 2)   # tiempo esperado en cola
acum_espera = round(acum_espera + espera, 2)                 # acumulador de espera
push_evento(round(reloj + t_e, 2), "llegada_emp") # próxima llegada empleado
push_evento(round(reloj + t_t, 2), "llegada_tec") # próxima llegada técnico
```

**Por qué redondear acá:**

Todas estas son **sumas/restas de números que ya tienen 2 decimales** — justo la
operación que genera el `4.1399999…`. Si usáramos `trunc2`:

- Perderíamos centavos en los tiempos de cada evento.
- Y como el **reloj se va acumulando** evento tras evento, esos centavos perdidos se
  irían **sumando** a lo largo de la simulación, corriendo todo el cronograma.

`round` limpia el ruido binario en cada paso y mantiene el reloj exacto. No cambia el
valor "real" del cálculo: solo elimina el error que mete IEEE 754 al sumar.

---

## 6. El RND: "lo que se muestra debe ser lo que se usa"

Este punto es **clave** y es el que un profe estricto va a mirar primero.

### El problema

`random.random()` devuelve un número con muchísimos decimales, por ejemplo
`0.26341809…`. Si lo usamos tal cual en la fórmula pero en la tabla lo **mostramos**
truncado a 2 decimales (`0.26`), aparece una inconsistencia grave:

```
RND mostrado en la tabla:  0.26
RND realmente usado:       0.26341809…

t (programa, con 0.2634…)  →  0.61
t (a mano/Excel, con 0.26) →  0.60   ← ¡NO COINCIDE!
```

Si el profe (o vos en Excel) toma el RND que figura en la fila —`0.26`— y lo mete en la
fórmula, le da `0.60`, distinto al `0.61` de la tabla. La tabla **no cierra**.

### La regla de oro

> **Trazabilidad / auditabilidad:** cualquier fila se tiene que poder recalcular tomando
> los valores que figuran *en esa fila* y aplicando las fórmulas, y debe dar exactamente
> el mismo resultado.

Para cumplirla, el RND que se usa tiene que ser el mismo que se muestra. Por eso se
trunca el RND a 2 decimales **ANTES** de la fórmula:

```python
rnd = trunc2(random.random())   # ej: 0.26341809… → 0.26
t   = trunc2(-MEDIA_LLEGADA_EMP * math.log(1 - rnd))   # usa 0.26 → t = 0.60
```

Ahora la tabla muestra `0.26` y la fórmula usó `0.26`: recalcular a mano da **exactamente
0.60**, idéntico a Excel. Tabla 100 % auditable.

### Detalle: nunca hay `log(0)`

Al truncar, el RND queda en el rango `0.00`–`0.99`. Entonces `1 - rnd` va de `1.00` a
`0.01`, nunca `0`, así que `math.log(1 - rnd)` nunca explota.

### Por qué 2 decimales (y no más)

Es coherente con el resto del TP, que trabaja todo a 2 decimales, y hace la tabla
reproducible a mano. (Como contrapartida, el RND solo puede tomar 100 valores distintos;
si se quisiera más finura estadística se usarían 4 decimales, mostrándolos también con 4
para no romper la auditabilidad. Acá se eligió 2 por coherencia y simplicidad.)

---

## 7. En la visualización (`main.py`)

Al **mostrar** los floats en la tabla se trunca de nuevo a 2 decimales, coherente con el
enunciado:

```python
def trunc2_str(v):
    return str(math.floor(v * 100 + 1e-9) / 100)
```

Notá el `+ 1e-9`: es una **épsilon de seguridad**. Empuja el número un poquitito hacia
arriba *antes* de truncar, para que un valor guardado como `4.1399999998` no se muestre
como `4.13`. Es la misma idea que `round`, aplicada al momento de formatear el texto: que
el usuario vea `4.14` y no un centavo de menos por culpa del float.

---

## 8. Resumen mental

| Situación | Operación | Función | Motivo |
|---|---|---|---|
| Generar el RND | `trunc2(random.random())` | **`trunc2`** | Que el RND mostrado = RND usado (tabla auditable) |
| Generar variable aleatoria | `gen_llegada_emp/atencion/mantenimiento/llegada_tec` | **`trunc2`** | Convención del TP (truncar, no redondear) |
| Sumar al reloj | `reloj + duración` | **`round`** | Borrar error de float, no perder centavos |
| Acumular espera | `acum_espera + espera` | **`round`** | Ídem |
| Mostrar en tabla | formateo de celdas | **`trunc2_str`** (+épsilon) | Coherencia visual con el enunciado |

**Truncamos el RND y las distribuciones (para que la tabla sea auditable y por la
convención del TP) y redondeamos las cuentas internas del reloj (para que el punto
flotante no nos robe centavos a lo largo de la simulación).**
