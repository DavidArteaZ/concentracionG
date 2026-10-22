# DML con el ICE en percentiles (robustez de V1): resultados

**Corrida:** 21/10/2026, con `03b_dml_percentil.py --fase 1` y `--fase 2`. La regla se declaró antes de estimar en `decision_percentil.md`.

**Entorno:** el mismo de `codigo_modelo/requirements.txt` (Python 3.13.16, numpy 2.5.3, pandas 3.0.5, scikit-learn 1.9.1, xgboost 3.4.1, doubleml 0.11.4), Linux x86_64.

**Insumos (sha256):**
- `03_dml.py` (versión con `--ice`): 7b4d61e2…
- `02_base_dml.csv`: 96fa3d7c…
- `diccionario_variables_02.csv`: 8d9e50b6…

**Salidas:** `resultados/03_resultados_percentil_v1/`. Las bitácoras están en `logs/`.

## Controles de la corrida
- **m(X) reproduce la corrida V1.** Las 608,640 predicciones fuera de pliegue coinciden, con diferencia máxima de 6 × 10⁻¹⁴. Los pliegues también son idénticos. Lo único que cambió es e(X) y la etapa final.
- **La validación contra DoubleML pasa:** la diferencia en β es de 10⁻¹⁷ y en el SE es de 10⁻¹⁶.
- No hubo repeticiones con ajuste de la varianza en dos dimensiones. Los grupos son 667 municipios y 1,308 UPM.

## Resultados (aprendiz elegido: XGBoost en los cuatro nuisances, igual que en V1)

| Especificación | Escala de D | β | SE (2 dim.) | IC 95% | z | p | MDE |
|---|---|---|---|---|---|---|---|
| Principal | DE (V1, referencia) | 5.09 | 2.63 | [−0.07, 10.24] | 1.93 | 0.053 | 6.96 |
| Principal | Percentil (por punto) | 0.151 | 0.084 | [−0.015, 0.316] | 1.79 | 0.074 | 0.223 |
| Principal | Percentil, ×10 | 1.51 | 0.84 | [−0.15, 3.16] | 1.79 | 0.074 | 2.23 |
| Total | DE (V1) | 1.21 | 0.82 | [−0.41, 2.82] | 1.47 | 0.142 | 2.28 |
| Total | Percentil, ×10 | 0.42 | 0.28 | [−0.12, 0.96] | 1.52 | 0.130 | 0.77 |

**Cociente condicional/total (D20):** 3.6 con percentil y 4.2 con DE.

**Por aprendiz, principal (z):**
- Percentil: lineal 1.86, RF 1.88, XGBoost 1.79.
- DE: lineal 2.12, RF 2.06, XGBoost 1.93.

**R² fuera de pliegue de e(X):** 0.83 con percentil y 0.86 con DE. El R² de m(X) es 0.45 en los dos casos.

**Variación entre repeticiones (principal):** z de 1.62 a 2.11, que corresponde a p de 0.035 a 0.106.

## Lectura
1. **El resultado es el mismo.** El signo es positivo y la magnitud es parecida: 1 DE del percentil son 28.9 puntos, que equivalen a ≈ 4.4 percentiles de destino, contra 5.09 por DE del ICE. La precisión es igual de insuficiente: el z baja de 1.93 a 1.79 y el IC incluye cero. La conclusión de la principal no cambia, ni para bien ni para mal.
2. **Lectura rango-rango:** pasar 10 percentiles más arriba en la complejidad del municipio de origen se asocia con 1.5 percentiles más en la posición de destino, condicional en X.
3. **No mejora la potencia.** El MDE (2.2 por 10 puntos) supera al β (1.5), igual que en V1 (6.96 contra 5.09).
4. **Las conclusiones no dependen de la cola izquierda.** El rango comprime la cola de municipios poco complejos y el β casi no se mueve. Además, el β varía menos entre aprendices: con XGBoost el z es algo menor y las tres versiones están más juntas que con DE.
5. **El total y la supresión por escala se mantienen.** El total no es significativo y el cociente pasa de 4.2 a 3.6.

## Limitaciones
- Las escalas no son comparables en β. La comparación se hace con el z y con la equivalencia por DE del percentil, que es aproximada porque la transformación no es lineal.
- El percentil se calcula entre las personas de la muestra, así que es un regresor generado. Su incertidumbre no se propaga al SE. Con n = 5,072 se espera que el efecto sea pequeño, pero no se verificó.
- Esta corrida es solo con V1. Para V2 (ZM 2010 y 2020) haría falta correr el mismo script con `--ice v2_zm2010` y `--ice v2_zm2020`, unos 70 minutos cada uno.
