# Reproducibilidad

**Proyecto:** Movilidad social y complejidad económica: un estudio de las características económicas regionales que influyen en la movilidad inesperada en México.
**Última actualización:** 29 de septiembre de 2026.
**Propósito:** este documento centraliza cómo se reproduce cada script del proyecto: qué hace, qué insumos usa, qué decisiones aplica y qué produce. Un tercero debe poder replicar todos los resultados con este archivo, el repositorio y los datos originales, sin contactar a los autores. Las justificaciones completas de cada decisión están en `docs/metodologia/decisiones_metodologicas.md`; aquí solo se cita el código de la decisión (D#, T#).

---

## 0. Convenciones generales

### Estructura del repositorio

| Carpeta | Contenido |
|---|---|
| `codigo/R/` | Scripts del proyecto, numerados en orden de ejecución |
| `codigo/` | `Informe de movilidad social en México 2025.do` (programa del CEEY que se replica) |
| `data/raw/` | Datos originales, nunca se modifican |
| `data/clean/` | Bases generadas por los scripts y carpetas de diagnóstico de cada script |
| `docs/documentacion/` | Diccionario y documentación de la ESRU-EMOVI 2023 |
| `docs/metodologia/` | `decisiones_metodologicas.md` y este archivo |

### Reglas que siguen todos los scripts

- Se ejecutan en orden numérico desde la raíz del proyecto (`project.Rproj`). Las rutas se construyen con `here::here()`; no hay rutas absolutas.
- Cada script lee solo datos originales o salidas de scripts anteriores. Ningún script modifica la salida de otro.
- Cada script fija su semilla en un parámetro al inicio y guarda `sessionInfo()` en su carpeta de diagnóstico.
- Cada script guarda sus tablas de diagnóstico en `data/clean/<nn>_<nombre>_resultados/`.
- Todo filtro que elimina observaciones se registra en una tabla de flujo de la muestra (T6).
- Ningún resultado depende de valores copiados a mano.

### Entorno de cómputo

| Componente | Versión (corrida del 29/09/2026) |
|---|---|
| R | 4.3.2 (2023-10-31 ucrt), Windows 11 x64 |
| haven | 2.5.4 |
| dplyr | 1.1.4 |
| FactoMineR | 2.11 |
| missMDA | 1.19 |
| here | 1.0.2 |

**Pendiente (T8):** fijar las versiones con `renv::snapshot()` y versionar `renv.lock`.

### Datos originales

| Archivo | Fuente | Uso |
|---|---|---|
| `data/raw/entrevistado_2023.dta` | ESRU-EMOVI 2023, base de entrevistados (CEEY). 17,843 observaciones, 296 variables | Script 01 |
| `docs/documentacion/Diccionario ESRU EMOVI 2023.xlsx` | CEEY | Códigos de respuesta (por ejemplo, 8 = "no sabe"; p22 = 999 = "no recuerda") |

---

## Script 01. `codigo/R/01_generar_quintiles_ires_emovi.R`

### Qué hace

Construye el Índice de Recursos Económicos (IRE) comparable del hogar actual y del hogar de origen con la metodología del CEEY. Con esos índices calcula las posiciones de destino y de origen (percentiles y quintiles) que usan los modelos. Además valida la réplica contra las cifras publicadas por el CEEY.

**No hace:** unir con el ICE (T17), excluir a quienes vivían en el extranjero a los 14 (T18), construir $X$ (D6, D10, D13) ni auditar fugas de información (T4). Eso corresponde al script 02.

**Tampoco construye el IRE no comparable** (robustez de D1): su código viene en el programa del Módulo de Inclusión Financiera 2023 del CEEY, que no está en el repositorio.

### Insumos

- `data/raw/entrevistado_2023.dta`
- Réplica de: `codigo/Informe de movilidad social en México 2025.do`, sección "INFORMACIÓN PARA 2023" (líneas 421–932).

### Parámetros

| Parámetro | Valor | Significado |
|---|---|---|
| `SEMILLA` | 20260929 | Semilla de la validación cruzada y de la imputación |
| `COHORTE_ANALISIS` | 1 | Cohorte de 25–34 años (D2) |
| `NCP_IMPUTACION` | `NULL` | Número de dimensiones de la imputación; `NULL` = se elige por validación cruzada |
| `NBSIM_CV` | 20 | Repeticiones de la validación cruzada de `estim_ncpMCA` |
| `NCP_MAX_CV` | 10 | Tope de búsqueda de ncp |
| `REF_T3` | Q1→Q1 = 50, Q5→Q5 = 50 | Cifras publicadas por el CEEY para la validación T3 |
| `TOL_T3` | 2 pp | Tolerancia de la validación T3 (si se excede, el script emite una advertencia) |

### Pasos

1. **Lectura y comprobaciones.** Se lee la base y se eliminan las etiquetas de `haven`. El script se detiene si `index` tiene duplicados o si algún `factor` es faltante o no positivo.

2. **Filtros previos al MCA (muestra CEEY, D11).** Se aplican en el orden del .do:
   - Sin `educ`.
   - Sin `padres_edu`, que es el máximo de `educp` y `educm`, construido como el `egen rowmax` del .do.
   - Sin `region_14`.

   La base de salida conserva a todas las personas con `region_14` y marca la muestra CEEY con `muestra_ceey`. Así, la variante de robustez de D11 puede usar a quienes no tienen `educ` o `padres_edu`.

3. **Activos del hogar actual.** Son 16 activos binarios (`ac1`–`ac16`) más el hacinamiento (`hac`: 1 si `tamhog/p89` ≤ 2.5). Es una traducción literal del .do:
   - Los códigos distintos de 1/2 quedan como `NA`.
   - Un cociente de hacinamiento faltante recibe `hac = 0`, porque en Stata un faltante es mayor que 2.5. En 2023 no hay casos.

4. **Activos del hogar de origen, en dos reglas.** Son 19 activos más `hac_or` (`p22/p23`). Las dos reglas solo difieren en tres variables:

   | Variable | Regla `ceey` (réplica del .do) | Regla `na` (principal, D11 y T5) |
   |---|---|---|
   | Tarjeta de crédito (p32f, p32g) | 0 si ninguna es "sí", aunque ambas sean "no sabe" | 1 si alguna es "sí"; 0 si ambas son "no"; `NA` en otro caso |
   | Ahorro (p32k, p32l) | Igual que tarjeta | Igual que tarjeta |
   | Automóvil (p30) | Faltante → 0 | Faltante → `NA`. p30 no tiene código de "no sabe" (rango 0–20), así que no cambia nada |
   | Hacinamiento | p22 = 999 se usa tal cual (queda como hacinado) | p22 = 999 → `NA` |

   El resto de los activos es igual en ambas reglas: "no sabe" (8) → `NA`.

5. **MCA por cohorte (D4).**
   - Se usa `FactoMineR::MCA` con `row.w = factor_ceey`.
   - Se estima por separado en cada una de las 4 cohortes, solo con los casos completos en los activos. Equivale al `predict ... if e(sample)` del .do.
   - Se conserva la primera dimensión.
   - Se genera un índice por versión:
     - `irec_act`: IRE actual.
     - `irec_or_ceey`: IRE de origen con la regla del CEEY. Solo sirve para validar (T3).
     - `irec_or_na`: IRE de origen principal (D11).

6. **Corrección de signo (D4).** En cada cohorte y versión, el índice se orienta para que su correlación ponderada con la proporción de activos que posee la persona sea positiva.
   - El .do multiplica siempre por −1. Con FactoMineR ese −1 fijo invierte el índice en algunas cohortes.
   - En la corrida del 29/09/2026, FactoMineR invirtió el eje en la cohorte 1 de los tres índices y en la cohorte 4 del IRE de origen.

7. **IRE de origen imputado (D11, D19).** Solo para la cohorte de análisis:
   - Se parte de los activos con la regla `na`.
   - `missMDA::estim_ncpMCA` elige el número de dimensiones con validación cruzada K-fold (ncp de 0 a `NCP_MAX_CV`, `NBSIM_CV` repeticiones, 5% de faltantes simulados).
   - `missMDA::imputeMCA` (método regularizado, `row.w = factor_ceey`) sustituye cada respuesta faltante por una probabilidad.
   - `FactoMineR::MCA(tab.disj = ...)` estima el índice sobre la tabla completa. Resultado: `irec_or_imp`, sin faltantes.

8. **Robustez de D11 sin filtros.** Se repiten los MCA del IRE actual y del IRE de origen (regla `na`) sin los filtros de `educ` y `padres_edu`. Resultado: `irec_act_sf` e `irec_or_na_sf`.

9. **Quintiles nacionales del CEEY y validación T3.**
   - Muestra: `muestra_ceey` con `irec_or_ceey` e `irec_act` no faltantes, con las 4 cohortes (n = 14,924).
   - Se calculan `q_or_nac_ceey` y `q_act_nac_ceey` con `factor_ceey`, replicando `xtile ... [pw = factor], nq(5)`.
   - Se calcula la matriz de transición con porcentajes por renglón (`tab ..., row` con `[aw = factor]`), en total y por sexo.

10. **Posiciones dentro de la cohorte de análisis (D2, D3).** Se calculan sobre toda la cohorte 1 de la muestra CEEY, incluidas las personas sin IRE de origen (D11) y las que vivían en el extranjero a los 14 (esas se excluyen después, en el script 02; D2, paso 4). Peso: `factor` sin redondear.
    - `pct_act_c1`: percentil continuo ponderado de destino (0–100). Se define como $pct(v) = 100\,[W(x<v) + W(x=v)/2]/W_{total}$, así que los empates reciben el percentil promedio y la media ponderada es exactamente 50.
    - `q_act_c1`: quintil de destino dentro de la cohorte.
    - `pct_or_c1_v` y `q_or_c1_v`, para cada versión `v` ∈ {`ceey`, `na`, `imp`}.
    - `q_act_nac`: quintil nacional de destino con las 4 cohortes, sin descartar a quienes no tienen IRE de origen (robustez de D2).
    - `pct_act_c1_sf` y `pct_or_c1_na_sf`: posiciones de la variante sin filtros.

11. **Comprobaciones automáticas.** El script se detiene si:
    - Algún índice queda con correlación negativa con los activos.
    - La media ponderada de `pct_act_c1` no es 50.
    - Algún percentil cae fuera de (0, 100).
    - El IRE actual tiene faltantes en la muestra CEEY.

    Emite una advertencia si T3 se aparta de `REF_T3` en más de `TOL_T3`.

12. **Diagnósticos y guardado.** Ver "Salidas".

### Decisiones que aplica

| Decisión | Qué se aplica en el script |
|---|---|
| D1 | IRE comparable, solo con datos de 2023 |
| D2 | Posiciones calculadas dentro de la cohorte 1; los cortes de destino se hacen sobre toda la cohorte y T18 se aplica después; `factor_ceey` en MCA y T3, `factor` en las posiciones propias |
| D3 | Percentil continuo ponderado con empates promediados como variable principal; quintil como robustez |
| D4 | FactoMineR sobre la matriz indicadora (el .do usa Burt) y corrección de signo adaptativa |
| D11 | "No sabe" → `NA` en la versión principal; se conserva a quienes no tienen IRE de origen; versión imputada; variante sin filtros de educación |
| D12, T5 | p22 = 999 → `NA` en la versión principal; p99 = 8 es un conteo válido |
| D19 | La versión imputada se genera para usarla como quintil de origen en la heterogeneidad |
| T3 | Validación contra la matriz publicada por el CEEY |
| T6, T11 | Flujo de la muestra y tasas de "no sabe" |

**Desviaciones respecto al .do que se reportan en el paper (T2):**
1. MCA sobre la matriz indicadora en lugar de la de Burt.
2. Signo adaptativo en lugar de −1 fijo.
3. En la versión principal, "no sabe" → `NA` en tarjeta, ahorro y auto, y p22 = 999 → `NA`.

### Salidas

**Base:** `data/clean/01_generar_ires_quintiles_esru.rds`. Tiene una fila por persona con `region_14` no faltante (17,789 filas), con todas las variables originales más las siguientes:

| Variable | Descripción |
|---|---|
| `padres_edu` | Máximo nivel educativo de los padres |
| `factor_ceey` | `round(factor) * 10`, peso usado en el MCA y en T3 |
| `muestra_ceey` | `TRUE` si la persona tiene `educ` y `padres_edu` (muestra principal) |
| `ac1`–`ac16`, `hacina`, `hac` | Activos del hogar actual |
| `ac_or1_ceey`–`ac_or19_ceey`, `hac_or_ceey` | Activos de origen, regla del CEEY |
| `ac_or1_na`–`ac_or19_na`, `hac_or_na` | Activos de origen, regla principal |
| `irec_act` | IRE actual comparable (muestra CEEY) |
| `irec_or_ceey` | IRE de origen, regla del CEEY (solo para T3) |
| `irec_or_na` | IRE de origen principal (con `NA`) |
| `irec_or_imp` | IRE de origen imputado (solo cohorte 1) |
| `irec_act_sf`, `irec_or_na_sf` | Índices de la variante sin filtros de educación |
| `q_or_nac_ceey`, `q_act_nac_ceey` | Quintiles nacionales del CEEY (muestra T3) |
| `q_act_nac` | Quintil nacional de destino sin descartar faltantes de origen |
| `pct_act_c1`, `q_act_c1` | Percentil y quintil de destino dentro de la cohorte 1 |
| `pct_or_c1_{ceey,na,imp}`, `q_or_c1_{ceey,na,imp}` | Percentil y quintil de origen dentro de la cohorte 1, por versión |
| `pct_act_c1_sf`, `pct_or_c1_na_sf` | Percentiles de la variante sin filtros |
| `algun_ns_or` | 1 si respondió "no sabe" en alguna pregunta del IRE de origen |

**Cómo filtrar:**
- Muestra principal: `muestra_ceey & cohorte == 1`.
- Variante sin filtros: `cohorte == 1`, usando las columnas `*_sf`.

**Diagnósticos:** `data/clean/01_ire_resultados/`

| Archivo | Contenido |
|---|---|
| `flujo_muestra.csv` | n después de cada filtro, en total y en la cohorte 1 (T6) |
| `diagnostico_mca.csv` | Por versión y cohorte: n, primer eigenvalor, % de inercia, ncp de la imputación, correlación con los activos y signo aplicado |
| `t3_matriz_transicion_nacional.csv` | Matriz de transición nacional (% por renglón) |
| `t3_persistencia_por_sexo.csv` | Q1→Q1, Q1→Q5 y Q5→Q5 por sexo |
| `reparto_quintiles.csv` | Participación ponderada de cada quintil |
| `faltantes_activos_origen_c1.csv` | `NA` por activo de origen en la cohorte 1 (regla principal) |
| `ns_origen_por_cohorte.csv` | % con algún "no sabe" de origen, por cohorte |
| `ns_origen_por_quintil_destino_c1.csv` | % con algún "no sabe" y % sin IRE de origen, por quintil de destino (T11) |
| `correlaciones_versiones_ire.csv` | Correlación ponderada entre versiones del índice en la cohorte 1 |
| `sessionInfo_01.txt` | Entorno de la corrida |

### Resultados de referencia (corrida del 29/09/2026)

Una corrida correcta debe reproducir estas cifras.

**Flujo de la muestra (T6):**

| Paso | n total | n cohorte 1 |
|---|---|---|
| Base original | 17,843 | 5,596 |
| Con `educ` | 17,551 | 5,458 |
| Con `padres_edu` | 16,304 | 5,109 |
| Con `region_14` (muestra CEEY) | 16,258 | 5,090 |
| Con IRE de origen, regla CEEY | 14,924 | 4,655 |
| Con IRE de origen, regla principal | 14,392 | 4,461 |
| Con IRE de origen imputado | — | 5,090 |

**Validación T3.** Resultado: cerrada.

| Indicador | Réplica | CEEY 2025 (publicado) |
|---|---|---|
| Fila Q1 (Q1…Q5) | 50.3 / 27.3 / 13.9 / 6.4 / 2.1 | 50 / 28 / 14 / 7 / 2 |
| Q5→Q5 | 50.7 | no publicado en total |
| Q1→Q1 hombres / mujeres | 48.8 / 51.3 | 49 / 51 |
| Q5→Q5 hombres / mujeres | 53.5 / 47.1 | 53 / 47 |
| Q1→Q5 hombres / mujeres | 3.3 / 1.3 | 3 / 1 |

Fuente de las cifras publicadas: presentación del Informe de Movilidad Social en México 2025 (CEEY, julio de 2025). Una réplica independiente en Python del MCA sobre la matriz indicadora coincide con el script en R hasta el decimal 12.

**Correlaciones ponderadas entre versiones, cohorte 1:**

| Par | Correlación |
|---|---|
| `irec_or_ceey` vs `irec_or_na` | 0.99999 |
| `irec_or_na` vs `irec_or_imp` | 0.99994 |
| `irec_act` vs `irec_act_sf` | 0.99999 |
| `irec_or_na` vs `irec_or_na_sf` | 0.99999 |

**Tasa de "no sabe" de origen por quintil de destino (cohorte 1):**

| Quintil de destino | Q1 | Q2 | Q3 | Q4 | Q5 |
|---|---|---|---|---|---|
| % con algún "no sabe" | 7.0 | 8.7 | 11.7 | 11.2 | 14.5 |

### Pendientes del script 01

- **Volver a correr el script con `NCP_MAX_CV = 10`.** En la corrida del 29/09/2026, `estim_ncpMCA` eligió ncp = 5, que era el tope anterior. Solo cambian `irec_or_imp` y sus posiciones; las cifras de referencia de arriba no cambian. Después de la corrida, actualizar el ncp elegido en esta sección.
- Fijar el entorno con `renv` (T8).

---

## Script 02. *(pendiente)*

Se documentará con la misma estructura: qué hace, insumos, parámetros, pasos, decisiones, salidas, resultados de referencia y pendientes.
