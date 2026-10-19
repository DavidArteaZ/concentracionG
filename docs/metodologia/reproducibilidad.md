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
| `codigo/ice_v1/` | Pipeline del ICE municipal (V1); datos en `data/raw/ice_v1/`, `data/clean/ice_v1/` y `outputs/ice_v1/` |
| `codigo/ice_v2/` | ICE por zona metropolitana (V2, D25); datos en `data/raw/ice_v2/`, `data/clean/ice_v2/` y `outputs/ice_v2/` |
| `codigo/modelo/` | DML en Python (`03_dml.py`, `04_supresion_influencia.py`, `05_robustez.py`) |
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
| `NCP_MAX_CV` | 19 | Tope de búsqueda de ncp (acotado a J − K − 1 = 19 con 20 activos binarios) |
| `TOL_PARSIMONIA_CV` | 0.01 | Regla de parsimonia, fijada ex ante el 13/10/2026: ncp = menor valor con error de CV ≤ 1.01 × mínimo |
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
   - `missMDA::estim_ncpMCA` calcula el error de validación cruzada K-fold para ncp de 0 a `NCP_MAX_CV` (`NBSIM_CV` repeticiones, 5% de faltantes simulados, **sin ponderar**: la función no acepta `row.w`). El ncp se elige con la regla de parsimonia (`TOL_PARSIMONIA_CV`), no con el argmin. La curva se guarda en `curva_cv_ncp_or_imp.csv`.
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
| `diagnostico_mca.csv` | Por versión y cohorte: n, primer eigenvalor, % de inercia, ncp de la imputación, correlación con los activos, signo aplicado y, en `or_imp`, el argmin y el tope de la validación cruzada |
| `curva_cv_ncp_or_imp.csv` | Error de validación cruzada por ncp (0–19), relativo al mínimo, y ncp elegido |
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

- ~~Volver a correr el script con `NCP_MAX_CV = 10`.~~ **Cerrada 13/10/2026.** Con tope 5 y tope 10 el argmin cayó en el tope (ncp = 5 y ncp = 10). Con tope 19 vuelve a caer en el tope: la curva de error no tiene mínimo interior. El error baja 21% de ncp = 0 a 1 y 4% de 1 a 3; de 7 a 19 baja menos de 1% (0.11157 contra 0.11058) y no es monótono entre 14 y 19. Con la regla de parsimonia de 1%, **ncp = 7**. Correlación ponderada `irec_or_na` vs `irec_or_imp` = 0.999945 (antes 0.999946). La matriz T3 no cambia.
- Pendiente: sensibilidad del quintil `q_or_c1_imp` a ncp ∈ {3, 7, 19} (porcentaje de personas que cambian de quintil). Se espera trivial, pero un revisor puede pedirlo.
- Fijar el entorno con `renv` (T8).

---

## Script 02. `codigo/R/02_preparar_base_dml.R`

**Qué hace:** arma la base del DML a partir del `.rds` del script 01. No recalcula el IRE, los percentiles ni el ICE.

### Insumos

- `data/clean/01_generar_ires_quintiles_esru.rds` (script 01).
- `data/clean/ice_v1/ice_para_dml.csv` y `data/clean/ice_v1/municipios_padre_hijo.csv` (`codigo/ice_v1`, módulos 07 y 05).
- `data/clean/ice_v2/ice_zm_para_dml.csv` y `data/clean/ice_v2/pob_unidad_conapo.csv` (`codigo/ice_v2`, módulo 02; D25).
- `data/raw/pobproy_conapo.csv` (CONAPO, población municipal por sexo y año, 1990–2040).
- `data/raw/ice_v1/poblacion_municipal.csv` (censos INEGI 2000, 2005, 2010; robustez).
- `data/raw/ESRU_mun.dta` (municipio actual, CEEY, D22).

### Pasos

1. Muestra: `muestra_ceey` y cohorte 1 (5,090) → sin `p20_COD` = 33333/99999 (T18; 16) → sin `p20_COD` = 03030 (2; no existe en BCS; ambas personas viven hoy en 14030 Chapala) = **5,072**.
2. D21: los municipios sin ICE en algún año censal (02006, 07123, 07124; 8 personas) reciben la clave del padre (`cve_ice`) para ICE, población, pliegues y agrupación.
3. D15: `anio14 = 2023 − edad + 14`; `ice14` interpolado entre 2003/2008/2013; `ice14_cercano`, `ice14_2003` y las 33 especificaciones alternativas (`ice14_<esp>`) interpoladas.
4. D20 (modificada el 13/10/2026): `log_pob14` = log de la población CONAPO del año exacto a los 14. Robustez: `log_pob14_censo` (censos interpolados en log; 2011–2012 con 2010), `log_ue14`, `tam_soloaga14`.
4b. D25 (17/10/2026): para cada delimitación (`zm2010`, `zm2020`), `unidad_<d>` (ZM o municipio no metropolitano de `cve_ice`; se verifica que no cambie entre t0 y t1), `icezm14_<año>` (ICE V2 interpolado como en D15), `log_pob14_<d>` (log de la población CONAPO de la unidad en el año a los 14) y `en_nucleo14_<d>`. En el diccionario tienen roles propios (`tratamiento_v2`, `escala_v2`, `grupo_v2`), así que 03–05 de V1 no las usan. Las columnas de V1 de la base no cambian (verificado celda por celda contra la base del 13/10/2026).
5. "No sabe" → `NA` con una tabla explícita de códigos por variable (`codigos_no_sabe.csv`). No hay regla general de 8: en p28 el 8 y el 9 son categorías, en p42 el 8 es un nivel educativo. `p46 = 99` (no documentado) → `NA`. Sí/No → 1/0. Los `NA` por pase de pregunta (p. ej. p42 si el padre no asistió) se dejan como `NA`.
6. Roles y tipos en `diccionario_variables_02.csv`. X principal sin agua (`ac_or6_na`) ni electricidad (`ac_or10_na`) ni p26c (D6); siguen dentro de `irec_or_na`. Auditoría T4 con `stop()`.
7. Y de robustez (D9), Z (4.2), mediadores (4.3) y migración (D14).

### Salidas

`data/clean/02_base_dml.csv` (NA = celda vacía) y `.rds`; `data/clean/02_resultados/`: `flujo_muestra_02.csv`, `municipios_padre_asignados.csv`, `codigos_no_sabe.csv`, `reparto_quintiles_02.csv`, `faltantes_x.csv`, `resumen_02.csv`, `distribucion_edad.csv`, `diccionario_variables_02.csv`, `sessionInfo_02.txt`.

### Resultados de referencia (13/10/2026)

- n = 5,072; 667 municipios de origen (`cve_ice`); 1,308 UPM; 38 personas fuera del núcleo del ICE en t0 o t1.
- Desviación del 20% por quintil tras las exclusiones: ≤ 0.13 pp (`q_act_c1` y `q_or_c1_imp`).
- R² ponderado de `ice14` sobre `log_pob14`: 0.833. Lineal sobre toda la X principal: 0.88; sin escala: 0.48.
- Correlación `log_pob14` (CONAPO) vs `log_pob14_censo`: 0.9997.
- La corrida en Windows (R 4.3.2) y una corrida en Linux (R 4.3.3, mismas versiones de dplyr y haven) dan la base idéntica celda por celda.
- D25 (17/10/2026): 534 unidades de origen con `zm2010` y 533 con `zm2020`; R² ponderado de `icezm14_2010` sobre `log_pob14_zm2010`: 0.803 (`zm2020`: 0.803); correlación ponderada `ice14`–`icezm14_2010`: 0.897.

### Pendientes y advertencias

- **Edad:** 1,147 personas con 25 años contra ~450 por edad en el resto (18.5% ponderado); exceso también en 30. Los pesos reproducen los grupos quinquenales (25–29: 48.7% vs. 51% CONAPO 2023), no la edad simple. Robustez: `ice14_2003` y excluir edad = 25.
- Correr el script en una sesión de R nueva (la `sessionInfo` de la primera corrida muestra missMDA y FactoMineR cargados de la sesión del script 01).

---

## ICE V2 por zona metropolitana. `codigo/ice_v2/` (D25)

**Qué hace:** recalcula el ICE con cada zona metropolitana como una sola unidad de la red, con el mismo algoritmo y los mismos parámetros que V1. Las funciones de V1 se cargan por ruta (`_v1.py`), no se copian.

### Orden de ejecución (desde la raíz)

1. `python -m codigo.ice_v1.run_all`, o como mínimo el módulo 01 de V1, que genera `data/clean/ice_v1/saic_largo.csv.gz`.
2. `python codigo/ice_v2/01_delimitaciones.py`. Requiere `pdftotext` (poppler; en Windows: `conda install -c conda-forge poppler`).
3. `python codigo/ice_v2/02_ice_zm.py`.
4. `python codigo/ice_v2/03_diagnosticos_persona.py` (vista previa; requiere la base del script 02).
5. `Rscript codigo/R/02_preparar_base_dml.R`.
6. `python codigo/modelo/03_dml.py --fase 1 --ice v2_zm2010`, luego `--fase 2 --ice v2_zm2010`. Lo mismo con `v2_zm2020`.

### Insumos

- `data/raw/ice_v2/delimitacion_ZM_2010.pdf`: Cuadro A1 de *Delimitación de las zonas metropolitanas de México 2010*.
- `data/raw/ice_v2/delimitacion_ZM_2020.xlsx`: *Metrópolis de México 2020*.
- La URL y la fecha de consulta de ambos archivos están pendientes.
- De V1: `saic_largo.csv.gz`, `municipios_padre_hijo.csv`, `ice_municipal.csv` (para la prueba de identidad) y `poblacion_municipal.csv`. Además, `data/raw/pobproy_conapo.csv`.

### Verificaciones que detienen el código

- La lectura de 2010 debe dar 59 ZM, 367 municipios y 63,836,779 habitantes, y cada ZM debe sumar la población que reporta el cuadro.
- La de 2020 debe dar 92 unidades y 421 municipios, con los conteos por tipo.
- Todo hijo fuera de la delimitación con padre dentro debe estar declarado en `HIJO_EXISTIA`.
- El núcleo de cada año y especificación debe ser conexo.
- **Prueba de identidad:** con unidades de un municipio se reproduce `ice_municipal.csv` (máx. |Δ| < 1e-8; observado: 1.8e-14).

### Salidas

- `data/clean/ice_v2/`: `delimitacion_zm2010.csv`, `delimitacion_zm2020.csv`, `unidades_zm.csv`, `ice_zm_unidad.csv`, `pci_rama_zm.csv`, `ice_zm_para_dml.csv` y `pob_unidad_conapo.csv`.
- `outputs/ice_v2/`: `diagnosticos_zm.csv`, `diagnosticos_persona_zm.csv`, `unidades_muestra_zm.csv` y `logs/`.

### DML con V2 (`03_dml.py --ice`)

- `v2_zm2010` y `v2_zm2020` cambian solo tres cosas:
  - el tratamiento (`icezm14_<año>`, estandarizado con pesos);
  - la escala en X de la especificación principal (`log_pob14_<d>` en lugar de `log_pob14`; la total no lleva ninguna);
  - el grupo de pliegues y de agrupación (`unidad_<d>` × UPM).
- Escriben en `data/clean/03_resultados_ice_v2_<d>/`, nunca en `03_resultados/`. `entorno_fase1.json` registra la versión, el tratamiento, los grupos y las variables agregadas o quitadas.
- `--ice v1` (la opción por omisión) reproduce V1: la repetición 0 de la fase 1 coincide con la corrida del 15/10/2026 (máx. |Δ| en predicciones de 5e-14).
- 04 y 05 siguen leyendo solo `03_resultados/` (V1).

