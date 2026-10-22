# Propuesta de D26. ICE en percentiles como robustez

**Escrita el 21/10/2026, antes de correr la estimación.** Se propone agregarla a `decisiones_metodologicas.md`. Ese archivo lo mantiene el hilo "ICE por zona metropolitana", así que aquí no se editó.

**Decisión:**
- **Principal (sin cambio):** ICE estandarizado con pesos, DE 1 (D15).
- **Robustez:** $D$ = percentil ponderado del ICE de origen entre las personas de la muestra de análisis (n = 5,072).
  - Escala de 0 a 100.
  - Se usa el factor de expansión.
  - Empates por rango medio: $pct(v) = 100\,[W(ICE<v) + W(ICE=v)/2]/W$.
- **Alcance:** V1, con las especificaciones principal y total (D20).
- **Todo lo demás es idéntico a `03_dml.py --ice v1`:** X, aprendices, rejillas, semillas (20261013 + r), 20 repeticiones, pliegues, SE agrupados en dos dimensiones, regla de elección del aprendiz y agregación.
- **Código:** `03b_dml_percentil.py`. Importa el 03 sin modificarlo y sustituye solo `tratamiento()`.

**Lectura:** β son los percentiles de destino por punto de percentil del ICE (pendiente rango-rango). β × 10 es el efecto de 10 puntos.

**Cómo se reporta, pase lo que pase:**
- La tabla de robustez lleva β, IC al 95%, z, el MDE de la fase 1 y el cociente condicional/total.
- Para compararlo con la principal se usa el z, no β, porque las escalas no son comparables.
- Si el signo o la significancia difieren de la principal, se reporta la discrepancia. No se cambia la principal.

**Por qué es robustez y no principal:** la escala principal ya se fijó y ya se vieron sus resultados. Cambiarla ahora estaría condicionado a esos resultados.

**Control de reproducibilidad:** m(X) no depende de D. Por eso sus predicciones fuera de pliegue tienen que coincidir con las de la corrida V1 (`corrida_dml/data/clean/03_resultados/predicciones_oof.csv.gz`).
