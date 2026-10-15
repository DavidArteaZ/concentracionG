# DML, fase 2: β (corrida del 14/10/2026)

n = 5,072; 20 repeticiones × 5 pliegues agrupados por municipio de origen; XGBoost en m(X) y e(X) (regla de la fase 1). β en percentiles de destino por 1 DE de ICE de origen. SE agrupado en dos dimensiones: 667 municipios de origen × 1,308 UPM.

## Resultado principal (combinación elegida: XGBoost / XGBoost)

| Especificación | β | SE (2 dim.) | IC 95% | p | Efecto mínimo detectable |
|---|---|---|---|---|---|
| Total (sin escala) | 1.21 | 0.82 | [−0.41, 2.82] | 0.14 | 2.3 |
| Condicional (con escala) | 5.09 | 2.63 | [−0.07, 10.24] | 0.053 | 7.0 |

Dispersión entre repeticiones (β por repetición): total 0.91–1.54; condicional 4.67–5.44. La partición de la muestra no mueve el resultado.

## Lectura con la regla fijada antes de ver β

1. **Total:** el IC incluye el cero. Es un nulo informativo: no se detecta asociación, y el IC excluye efectos mayores a 2.8 percentiles por 1 DE de ICE.
2. **Condicional:** el IC incluye el cero, aunque por muy poco (p = 0.053). Por la regla, **no** se reporta como evidencia de complejidad más allá de la escala, ni como evidencia en contra. Se reporta como falta de variación independiente.
3. **Cociente condicional/total = 4.2.** No es una "proporción que sobrevive": el β condicional es mayor que el total. Ver la sección de riesgos.

## Comparación con los otros algoritmos (no cambia la lectura)

| Especificación | Lineal | Random forest | XGBoost (elegido) |
|---|---|---|---|
| Total | 0.90 (p = 0.26) | 1.33 (p = 0.13) | 1.21 (p = 0.14) |
| Condicional | 4.61 (p = 0.034) | 5.16 (p = 0.039) | 5.09 (p = 0.053) |

Con lineal y random forest, el condicional cruza el 5%. La regla elige el algoritmo con menor error fuera de pliegue y se respeta. Reportar "significativo con RF" sería escoger la especificación favorable.

## Riesgos críticos antes de redactar

1. **Supresión: el condicional es 4 veces el total.** Con el mismo tamaño de municipio, más complejidad se asocia con más movilidad. Con la misma complejidad, más población se asocia con menos movilidad. Los dos efectos se cancelan en el total. Es una historia económica posible (congestión, competencia, costo de vida en municipios grandes), pero también es la firma típica de la colinealidad: Ẽ conserva solo 14% de la varianza del ICE.
2. **Escala de β.** β está por 1 DE del ICE crudo, pero la DE de Ẽ es 0.37. Un movimiento típico del ICE no anticipado por las circunstancias y la escala equivale a 5.09 × 0.37 ≈ **1.9 percentiles**. Así debe reportarse para no exagerar el tamaño.
3. **Influencia.** Con tan poca variación residual, unos pocos municipios atípicos (pequeños pero muy complejos, o al revés) pueden mover β.

## Pruebas pendientes (sin cambiar la especificación principal)

- **Diagnóstico de supresión:** coeficiente de la escala condicional al ICE y distribución de Ẽ por tamaño de municipio.
- **Influencia:** excluir un estado a la vez, y excluir el 1% de municipios con |Ẽ| más alto.
- **Robustez prevista en las decisiones:** servicios y barrio en X (D6), ICE de 2003 y del año censal más cercano (D15), sin edad = 25, población censal en lugar de CONAPO (D20), log de UE (D20a), categorías de Soloaga, ICE alternativos, Y por quintil (D3) y binarias de movilidad (D9).
- **Heterogeneidad** por quintil de origen, sexo, región y ruralidad (4.2) y **mecanismos** (4.3).

## Validación

Con pesos iguales a 1, β y el SE heterocedástico calculados a mano coinciden con DoubleMLPLR a precisión de máquina (`validacion_doubleml.csv`).
