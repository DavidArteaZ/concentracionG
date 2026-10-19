# Batería de robustez (corrida del 16/10/2026)

Script: `codigo/modelo/05_robustez.py`. Salidas: `data/clean/05_resultados/` (`estimaciones_todo.csv`, `por_rep_todo.csv`, `bitacora.log`, `entorno_todo.json`).

Cada prueba cambia una sola cosa respecto de la principal. Usa XGBoost, los mismos pliegues y las mismas semillas, y solo vuelve a ajustar la función auxiliar que cambia. La fila de referencia reproduce exactamente la fase 2. β está en percentiles de destino por 1 DE de ICE, salvo que se indique otra unidad. SE agrupado en dos dimensiones (municipio × UPM).

## 1. Pruebas previstas (20 repeticiones)

| Prueba | Decisión | n | Condicional (con escala) | p | Total (sin escala) | p |
|---|---|---|---|---|---|---|
| **Principal (referencia)** | | 5,072 | **5.09** [−0.07, 10.24] | 0.053 | **1.21** [−0.41, 2.82] | 0.14 |
| Servicios de vivienda y barrio en X | D6 | 5,072 | 4.91 | 0.062 | 1.14 | 0.18 |
| ICE del año censal más cercano | D15a | 5,072 | 4.87 | 0.061 | 1.24 | 0.13 |
| ICE de 2003 | D15b | 5,072 | 4.90 | 0.045 | 1.16 | 0.15 |
| Sin la edad de 25 | heaping | 3,925 | 5.07 | 0.093 | 1.01 | 0.30 |
| Población censal (en lugar de CONAPO) | D20 | 5,072 | 4.98 | 0.061 | — | |
| + log de UE | D20a | 5,072 | 5.50 | 0.082 | — | |
| Categorías de Soloaga (en lugar del log de población) | D20b | 5,072 | 4.43 | 0.029 | — | |
| + autoadscripción y color de piel autopercibido | D17 | 5,072 | 5.04 | 0.057 | 1.26 | 0.13 |
| Solo no migrantes | D14 | 3,659 | 4.57 | 0.058 | 1.40 | 0.12 |

**Lectura:**
- El β condicional va de 4.4 a 5.5 en las nueve pruebas, y el total de 1.0 a 1.4. Ninguna cambia el signo ni la magnitud de forma relevante.
- El p condicional oscila alrededor de 0.05 (de 0.029 a 0.093). Que dos pruebas crucen el 5% (ICE de 2003 y Soloaga) no cambia la lectura: es lo esperable con un estimador cuyo z está en 1.9. Por la regla fijada, se reporta igual que la principal.
- La prueba de servicios (D6) acota el riesgo de mediación: al controlar por los servicios, β baja solo 4% (de 5.09 a 4.91).
- Soloaga da el p más bajo porque, al usar 4 categorías en lugar del log continuo, deja más variación en Ẽ (0.19 contra 0.14). Esto no es más evidencia: es un control de escala más grueso. Lo dejo dicho para que no se cite como "el resultado significativo".

## 2. Variable dependiente alternativa (20 repeticiones)

| Y | Decisión | Media ponderada | Unidad de β | Condicional | p | Total | p |
|---|---|---|---|---|---|---|---|
| Quintil de destino (1–5) | D3 | — | quintiles | 0.25 | 0.063 | 0.06 | 0.15 |
| Sube al menos un quintil | D9 | 31.2% | pp | 7.0 | 0.059 | 2.4 | 0.11 |
| Sube al menos dos quintiles | D9 | 11.1% | pp | **9.2** | **0.003** | 0.3 | 0.83 |
| De Q1–Q2 a Q4–Q5 (solo origen Q1–Q2, n = 1,514) | D9 | 13.0% | pp | **14.4** | **0.014** | 2.8 | 0.19 |

**Lectura:**
- El quintil reproduce la principal: 0.25 quintiles equivalen a unos 5 percentiles.
- Las dos binarias de movilidad grande son las únicas con evidencia clara. Por 1 DE de ICE no explicado por la escala, la probabilidad de subir dos o más quintiles sube 9.2 pp (sobre una base de 11%). La de llegar a Q4–Q5 desde Q1–Q2 sube 14.4 pp (sobre una base de 13%). En el total no hay nada.
- **Advertencia de comparaciones múltiples:** son 3 umbrales × 2 especificaciones. Con la corrección de Holm para los 3 umbrales condicionales, "sube dos quintiles" sigue por debajo de 0.01 y "Q1–Q2 a Q4–Q5" queda en 0.028. Sobreviven, pero D9 los define como robustez: no pueden pasar a ser el resultado principal después de verlos.
- Es una pista coherente con la pregunta de los "pisos pegajosos": el efecto estaría en los saltos grandes y en quienes parten de abajo. Se prueba formalmente en la heterogeneidad (4.2), con la regla fijada antes.
- Los β binarios en pp por 1 DE de ICE crudo también se reportan por 1 DE de Ẽ (× 0.37): 3.4 pp y 5.3 pp.

## 3. ICE alternativos (33 variantes, 5 repeticiones)

Con 5 repeticiones, la comparación correcta es contra la principal con esas mismas 5 repeticiones: condicional 5.20 (p = 0.052) y total 1.46 (p = 0.075).

| | Condicional | Total |
|---|---|---|
| Rango de β (32 variantes sin fitness) | 5.00 a 5.63 | 1.33 a 1.54 |
| p < 0.05 / p < 0.10 | 10 / 33 | 0 / 31 |
| β negativos | 0 | 0 |

- Los umbrales (U, D, P), excluir regiones y usar solo las ramas comunes no mueven β. El resultado no depende de las decisiones de construcción del ICE.
- **Fitness (Tacchella et al.) es la excepción:** condicional 1.55 (p = 0.09) y total 1.10 (p = 0.10). No es contradictorio. La escala explica mucho menos el fitness (R² de e(X) de 0.39, contra 0.86 del ICE) y Ẽ conserva 61% de su varianza. Por 1 DE de variación independiente, el efecto es similar: 1.55 × 0.78 = 1.2 percentiles para fitness y 5.09 × 0.37 = 1.9 para el ICE. Fitness mezcla diversidad y complejidad, y la diversidad es casi tamaño (D20). Por eso su β condicional por DE cruda es menor.

## Riesgos y siguiente paso

1. **Robusto en magnitud, frágil en significancia.** El β condicional (≈ 5 por DE de ICE, ≈ 1.9 por DE de Ẽ) es estable en las 9 pruebas de especificación y en las 33 variantes de ICE. Su p está siempre entre 0.03 y 0.09. Para el paper: "asociación positiva estable, estimada con imprecisión", no "significativa" ni "nula".
2. **Las binarias de movilidad grande son lo más fuerte del análisis**, pero son robustez. Elevarlas a resultado principal después de verlas sería *p-hacking*. Lo correcto es probarlas en la heterogeneidad por quintil de origen (4.2), que ya estaba prevista.
3. **D17:** "Negra" (52 casos) se agrupó con "Indígena". Hay que documentarlo en D17 o elegir otra agrupación.
4. **D3:** el quintil se estimó con una regresión de E[quintil|X], no con un clasificador. El objetivo es el mismo, pero hay que anotarlo en D3.
