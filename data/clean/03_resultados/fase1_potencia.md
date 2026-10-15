# DML, fase 1: funciones auxiliares y potencia

Corrida del 13/10/2026: 20 repeticiones × 5 pliegues agrupados por municipio de origen, n = 5,072. β todavía no se ha calculado.

## Funciones auxiliares (R² ponderado fuera de pliegue, promedio de 20 repeticiones)

| Especificación | Función | Lineal | Random forest | XGBoost |
|---|---|---|---|---|
| Principal (con escala) | m(X) → destino | 0.393 | 0.446 | **0.452** |
| Principal (con escala) | e(X) → ICE | 0.836 | 0.847 | **0.862** |
| Total (sin escala) | m(X) → destino | 0.393 | 0.447 | **0.452** |
| Total (sin escala) | e(X) → ICE | 0.310 | 0.351 | **0.359** |

XGBoost gana en las cuatro funciones auxiliares por la regla fijada de antemano (menor ECM fuera de pliegue). La regresión lineal queda claramente por debajo en m(X) (0.39 contra 0.45): el ML sí aporta (T10).

## Efecto mínimo detectable (α = 0.05, potencia = 0.80; SE agrupado municipio × UPM evaluado en β = 0)

| Especificación | Varianza de Ẽ (ICE estandarizado) | SE | Efecto mínimo detectable |
|---|---|---|---|
| **Principal (con escala)** | 0.138 | 2.48 | **7.0 percentiles por 1 DE de ICE** |
| **Total (sin escala)** | 0.642 | 0.81 | **2.3 percentiles por 1 DE de ICE** |

Para dar escala: la DE del percentil de destino es de unos 29 puntos. 7 percentiles equivalen a 0.24 DE del destino, y 2.3 a 0.08 DE.

## Lectura que propongo fijar antes de ver β

1. **β total (sin escala).** Tiene potencia para efectos moderados. Si su IC excluye el cero, hay asociación entre el ICE de origen y la movilidad. Si no lo excluye, el IC acota el efecto a menos de unos ±2.3 percentiles y se reporta como un nulo informativo.
2. **β condicional (con escala).** Solo puede detectar efectos grandes (≥ 7 percentiles). Si su IC excluye el cero, es evidencia de complejidad más allá de la escala. Si no lo excluye, **no se interpreta como evidencia en contra de la hipótesis**: se reporta como falta de variación independiente (ya previsto en D20), junto con el cociente condicional/total como descripción.
3. **No se cambia la especificación después de ver β.** Las robusteces (servicios, ICE alternativos, ICE de 2003, sin edad = 25, población censal) se corren todas y se reportan todas.

## Archivos

`data/clean/03_resultados/`: `diagnostico_nuisances.csv`, `aprendices_elegidos.csv`, `potencia.csv`, `hiperparametros.csv`, `pliegues.csv.gz`, `predicciones_oof.csv.gz`, `entorno_fase1.json`.
