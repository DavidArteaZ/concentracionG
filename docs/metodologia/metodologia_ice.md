# Metodología del Índice de Complejidad Económica (ICE) municipal

**Proyecto:** Movilidad social y complejidad económica en México
**Versión:** 0.1 (04/10/2026). Documento vivo: se actualiza al cerrar cada módulo. Las secciones marcadas *[pendiente]* se llenan con los resultados.
**Alcance:** construcción, diagnóstico y validación del ICE municipal (2003, 2008, 2013, 2018 y 2023) que entra como regresor en el modelo DML. La estimación del DML se documenta en `decisiones_metodologicas.md`.

---

## 1. Datos y fuentes

Todos los insumos crudos están en `data/raw/ice/` y no se modifican.

| Insumo | Archivo | Fuente | Contenido y notas |
|---|---|---|---|
| Censos Económicos por municipio y actividad | `saic_2003_2023/*.csv` (5 archivos) | INEGI, Sistema Automatizado de Información Censal (SAIC), serie *Censos Económicos 2024. Resultados definitivos*; consulta del 08/09/2026 | UE y PBT por municipio × rama/clase SCIAN; años de referencia 2003, 2008, 2013, 2018 y 2023. La serie viene homologada al SCIAN por INEGI. **Celda vacía = dato omitido por confidencialidad** (nota del propio archivo). Los archivos traen relleno de bytes nulos al final, que se elimina al leer. |
| Totales municipales de los Censos Económicos | `saic_totales_municipales/` *[pendiente de descarga]* | INEGI, SAIC | Personal ocupado, remuneraciones, VACB y UE a nivel total municipal. Es el validador principal (Módulo 06). |
| PIB per cápita municipal | `gdp_perCapita_1990_2022.csv` | Kummu, Kosonen y Masoumzadeh Sayyar (2025), *Scientific Data* 12:178, doi:10.1038/s41597-025-04487-x; datos en doi:10.5281/zenodo.10976733 | PIB per cápita PPP 1990–2022 en polígonos GADM nivel 2 (2,457 para México). **La variación dentro de cada estado es modelada** (ver §6). |
| Polígonos GADM | `gadm41_MEX_2/` | GADM v4.1 | 2,457 unidades, en WGS84. Los IDs siguen orden alfabético y **no** son claves INEGI. |
| Marco geoestadístico municipal | `00mun_2023/` | INEGI, Marco Geoestadístico 2023 | 2,478 polígonos en *Mexico ITRF2008 LCC*. |
| Catálogos de claves | `CUCG_2003.csv`, `CUCG_2023.csv` | INEGI, Catálogo Único de Claves Geoestadísticas | A nivel localidad, con coordenadas y población. Tienen 2,446 y 2,475 municipios. |
| Población municipal | `poblacion_municipal.csv` | INEGI (API: Censos y Conteos), completada con proyecciones de CONAPO; 2015 completo de CONAPO | 2000, 2005, 2010, 2015 y 2020, en la geografía de 2023 (2,475 municipios). |
| Municipios creados en 2024 | `municipios_nuevos_2024.csv` | Decretos de los congresos estatales (ver §5, D9) | Reasignación de 24059, 25019 y 25020. |
| Respuestas de ESRU-EMOVI | `data/raw/entrevistado_2023.dta` | CEEY | Solo para contar cuántos entrevistados quedan afectados por los filtros (`p20_COD`). |

**Descartados:**
- `muns_plus.csv`: sin fuente ni año, sin indicador de pobreza y con solo 30 de 570 municipios de Oaxaca.
- Personal ocupado por rama: la confidencialidad del INEGI aplica a todas las variables económicas, así que tendría la misma supresión que el PBT.

---

## 2. Metodología del ICE

### 2.1 Matriz de entrada
Para cada año t, X_cp = número de unidades económicas (UE) del municipio c en la rama p (SCIAN a 4 dígitos). UE es la única variable de SAIC sin supresión por confidencialidad (§5, D1).

### 2.2 Núcleo de estimación
El PCI se estima solo con municipios y ramas de tamaño suficiente:
- **Municipios:** UE totales ≥ 30 y al menos 5 ramas con UE > 0.
- **Ramas:** presentes (UE > 0) en al menos 10 municipios.

Se filtra primero municipios y luego ramas, y se itera hasta que no cambie nada. Los filtros usan tamaños crudos, no diversidad ni ubicuidad (que dependen del RCA).

### 2.3 Ventaja comparativa revelada y matriz binaria
Con los datos del núcleo:

RCA_cp = (X_cp / Σ_p X_cp) / (Σ_c X_cp / Σ_c Σ_p X_cp)

M_cp = 1 si RCA_cp ≥ 1; en otro caso, 0.

Diversidad: k_c = Σ_p M_cp. Ubicuidad: k_p = Σ_c M_cp.

### 2.4 Complejidad de las ramas (PCI)
Es el método de reflexiones de Hidalgo y Hausmann (2009), resuelto en forma espectral. Se toma la matriz simétrica

S = K_p^{-1/2} M' K_c^{-1} M K_p^{-1/2},

donde K_c y K_p son matrices diagonales con k_c y k_p. Sea v el eigenvector del segundo eigenvalor más grande de S. Entonces PCI_raw = K_p^{-1/2} v. Esta forma simétrica es matemáticamente equivalente al eigenvector de M̃_pp y numéricamente más estable.

**Signo:** se orienta para que el ICE del núcleo se correlacione positivamente con la diversidad.

### 2.5 Proyección del ICE a todos los municipios
Para cada municipio, esté o no en el núcleo, el RCA se calcula con su propia estructura en el numerador y las participaciones nacionales del núcleo en el denominador, solo sobre las ramas del núcleo. Luego:

ICE_raw_c = promedio del PCI_raw de las ramas con M_cp = 1.

En el núcleo, esto reproduce exactamente el eigenvector del ICE, porque k_c = M̃_cp · k_p. Los municipios sin ninguna rama del núcleo con M_cp = 1 quedan sin ICE (`NaN`) y se reportan.

### 2.6 Estandarización
Para cada año, ICE = (ICE_raw − media del núcleo) / desviación estándar del núcleo. Al PCI se le aplican la misma media y desviación (convención de Hidalgo y Hausmann). En consecuencia, **el ICE es una posición relativa dentro de cada año**, no un nivel comparable entre años.

### 2.7 Diagnósticos obligatorios en cada corrida
- Eigenvalores λ1 a λ5, brecha λ2 − λ3 y número de eigenvalores > 0.999.
- Componentes conexas del grafo municipio–rama. Si hay más de una, la ejecución se detiene.
- Correlación con el paquete `ecomplexity`: debe ser ≥ 0.9999.
- Spearman del ICE con la diversidad, con el log de UE totales y con el log de población.
- Empates exactos.

---

## 3. Scripts (`codigo/ice/`)

Todo se ejecuta con `python -m codigo.ice.run_all`. El notebook anterior (`complejidad_economica.ipynb`) queda reemplazado.

| Script | Qué hace | Salidas principales |
|---|---|---|
| `01_limpieza_saic.py` | Lee SAIC (quita los bytes nulos y los encabezados), clasifica cada celda como valor, cero o suprimida, verifica conteos y ramas por año y reasigna los municipios creados en 2024 | `data/clean/ice/saic_largo.parquet` |
| `02_ice.py` | Núcleo, RCA, PCI espectral, proyección del ICE, estandarización, diagnósticos, validación contra `ecomplexity` y variante con ramas comunes a todos los años | `ice_municipal.csv`, `pci_rama.csv`, `diagnosticos_espectrales.csv` |
| `03_diagnostico_variables.py` | Documenta por qué UE: censura del PBT condicional a presencia, condicionamiento espectral y degeneración del ICE con PBT | `tabla_ue_pbt.csv` |
| `04_sensibilidad.py` | Malla de umbrales, reglas de exclusión R1–R4, nivel clase, Fitness-Complexity y ramas comunes; impacto en entrevistados de EMOVI | ICE alternativos en formato largo y tabla de sensibilidad |
| `05_crosswalk_gadm_inegi.py` | Tabla puente GADM↔INEGI (por nombre, más verificación con población de localidades) y tabla padre–hijo de municipios creados entre 2003 y 2023 | `crosswalk_gadm_inegi.csv`, `municipios_padre_hijo.csv` |
| `06_validacion_externa.py` | Validación del ICE contra remuneración media y productividad (totales censales), con controles de escala y diversidad; PIB solo descriptivo; regla Rama vs. Clase | `validacion_*.csv`, `rama_vs_clase.csv` |
| `07_export_dml.py` | Base final para el DML: ICE base y alternativos, núcleo, escala y diversidad | `data/clean/ice/ice_para_dml.csv` |

*[pendiente: versiones de los paquetes, tiempos de ejecución y conteos de cada paso]*

---

## 4. Parámetros

| Parámetro | Valor base | Malla de sensibilidad |
|---|---|---|
| `U_MIN` (UE totales del municipio) | 30 | 10, 30, 100 |
| `D_MIN` (ramas con UE > 0) | 5 | 3, 5, 10 |
| `P_MIN` (municipios con UE > 0 por rama) | 10 | 5, 10, 20 |
| Umbral de RCA | 1 | — |
| Nivel SCIAN | Rama (4 dígitos) | Clase (6 dígitos) |
| Semilla | 20261003 | — |

---

## 5. Decisiones y sus implicaciones

| # | Decisión | Alternativa descartada | Por qué | Implicación |
|---|---|---|---|---|
| D1 | Usar UE como variable | PBT; personal ocupado | El PBT está suprimido en 61–66% de las celdas con UE > 0 (y personal ocupado tendría la misma supresión). La supresión convierte esas celdas en ceros y fragmenta la matriz. | El ICE mide especialización en **número de establecimientos**, no en producción. Sobrerrepresenta sectores fragmentados (comercio) y subrepresenta los concentrados (manufactura en plantas grandes). Se declara como limitación. |
| D2 | Estimar el PCI en un núcleo y proyectar el ICE a todos | Eliminar municipios chicos | Un RCA con pocas UE es ruido. Eliminar municipios sacaría de la muestra a entrevistados de municipios rurales y pobres, lo que se correlaciona con el resultado. | Nadie pierde el ICE por ser chico, salvo los municipios sin ninguna rama del núcleo con M_cp = 1, que se reportan. El ICE de los municipios fuera del núcleo es una proyección: se reporta su peso en la muestra de EMOVI. |
| D3 | Umbrales base 30 / 5 / 10 | Otros valores | Propuesta inicial | Su respaldo es la malla de sensibilidad (A5), no un argumento teórico. |
| D4 | Exclusión de ramas solo como robustez: R1 (5211, 5232, 2111), R2 (subsector 221), R3 (sector 21, panel aparte), R4 = R1 + R2 + R3 | Excluirlas en la especificación base; una lista armada a mano | Son ramas cuya ubicación no refleja capacidades locales (mandato, red de infraestructura o geología). Excluirlas en la base sería discrecional. | Funcionan como prueba de falsación de A3 y A5. Si β cambia mucho al excluirlas, la relación pasa en parte por la presencia institucional y hay que reportarlo. |
| D5 | Rama como especificación base, salvo que Clase gane bajo la regla fijada de antemano (Módulo 06.7) | Elegir con el diagrama de Taylor | El diagrama de Taylor no informa nada con un solo regresor, y el cruce con el PIB estaba mal | La elección se puede defender ante un revisor. Clase siempre se reporta como robustez. |
| D6 | Estandarizar dentro de cada año | ICE en niveles comparables entre años | Convención estándar; el espacio de ramas cambia con la cobertura | La interpolación de D15 combina posiciones relativas, y así se declara. La variante con ramas comunes acota el problema. |
| D7 | Cruce GADM↔INEGI por nombre, verificado con población de localidades | Índice de GADM (el error original); centroides | GADM ordena estados y municipios alfabéticamente. La población es lo relevante para una variable per cápita. | Corrige la validación previa, que unía el ICE con el PIB de otros municipios. |
| D8 | PIB de Kummu et al. solo como descriptivo | Usarlo como validador de A3 | Dentro de cada estado, el PIB municipal se predice con urbanización y tiempo de viaje (de 2015) | A3 se valida con los totales censales (remuneración media y productividad). La relación con el PIB no se interpreta como evidencia de sofisticación. |
| D9 | Municipios creados en 2024 en SAIC 2023: 24059 → 24028 y 25019 → 25006 (decretos); 25020 → 25011 (Guasave, aportante principal de cuatro) | Dejarlos separados | ESRU-EMOVI, CUCG_2023 y el marco de 2023 no tienen esas claves | Solo afecta al ICE 2023, que no entra en la interpolación principal. Robustez: ICE 2023 sin 25020. |
| D10 | Municipios sin ninguna rama del núcleo con M_cp = 1: sin ICE | Imputarles el mínimo | Imputar inventa información | Se reporta cuántos entrevistados afecta. |
| — | **Diferidas:** el papel de la validación externa en el paper (texto principal o anexo) y la asignación de ICE a municipios creados después de que el entrevistado tenía 14 años | — | Pertenecen a otra etapa | El código produce los insumos (tablas de validación y tabla padre–hijo) sin resolverlas. |

---

## 6. Limitaciones conocidas

1. **Cobertura de los Censos Económicos:** no incluyen la agricultura (del sector 11 solo aparecen 1125, 1141 y 115x), el gobierno ni el comercio ambulante. En los municipios rurales, el ICE describe una parte de su economía.
2. **UE no mide tamaño:** un establecimiento de una persona pesa lo mismo que una planta grande (D1).
3. **Cambios en el espacio de ramas:** respecto a la unión de todos los años, 2003 no tiene 1151, 1152, 1153, 4861, 5232, 5622 ni 5629; 2008 no tiene 5622 ni 5629; 2013 no tiene 4861, 5622 ni 5629; 2018 y 2023 no tienen 4861. La causa es la cobertura del censo.
4. **Geografía cambiante:** SAIC usa la geografía de cada levantamiento. Hay 29 municipios creados entre 2003 y 2023 y 3 en 2024. Algunos municipios no tienen UE en ciertos años (por ejemplo, 07006, 07010, 07011 y 07036 en 2023).
5. **El PIB municipal es modelado** (D8). Su validación oficial a nivel municipal es de 43 unidades europeas.
6. **Validador principal de la misma fuente:** la remuneración media y la productividad vienen de los mismos censos que el ICE. Son variables distintas, pero comparten la cobertura.

---

## 7. Afirmaciones que pueden salir del ICE

Solo se sostienen si los resultados de los módulos las respaldan; el estado de cada una se llena al ejecutar.

| Afirmación | Evidencia que la respalda | Estado |
|---|---|---|
| **A1.** El ICE se calcula sobre una matriz bien condicionada y no depende de municipios o ramas con muy pocas observaciones | Módulo 02: una sola componente conexa, brecha espectral clara y núcleo documentado | *[pendiente]* |
| **A2.** UE es la variable adecuada porque es la única sin supresión por confidencialidad | Módulo 03: censura del PBT de 61–66% condicional a presencia (ya verificada en los datos crudos), comparación espectral | Censura verificada; diagnóstico espectral *[pendiente]* |
| **A3.** El ICE se asocia con el desarrollo municipal más allá de la escala y de la diversidad simple | Módulo 06: β del ICE y su R² parcial con controles de UE totales, población, diversidad y efectos fijos de estado, sobre remuneración media y productividad | *[pendiente; requiere los totales municipales]* |
| **A4.** La elección Rama/Clase sigue una regla fijada de antemano | Módulo 06.7 | *[pendiente]* |
| **A5.** Los resultados no dependen de los umbrales ni de las ramas institucionales | Módulo 04: Spearman, cambios de quintil y β del DML con cada alternativa | *[pendiente]* |

**Lo que el ICE no permite afirmar:**
- Que la complejidad **cause** el desarrollo o la movilidad. El ICE es descriptivo; la identificación es tarea del DML y tiene sus propios supuestos.
- Que un municipio "subió" o "bajó" de complejidad en términos absolutos. El ICE es relativo a cada año (D6); las comparaciones entre años son de posición.
- Que el ICE mida producción, valor agregado o productividad. Mide la estructura de especialización en establecimientos.
- Que el ICE describa toda la economía de un municipio rural (limitación 1).
- Cualquier cosa basada en el PIB municipal dentro de un estado (D8).
- Cualquier resultado del notebook anterior basado en PBT, en el diagrama de Taylor o en el cruce GADM original.

---

## 8. Estado y pendientes

- [x] Insumos revisados (04/10/2026): codificación de la confidencialidad, conteos, ramas por año, coincidencia GID_2–PIB, catálogos y población.
- [x] Decisiones D1–D10 tomadas.
- [ ] Descarga de los totales municipales de SAIC (validador principal).
- [ ] Módulos 01–07.
- [ ] Actualizar §3, §6 y §7 con los resultados.

**Referencias**
- Hidalgo, C. A., y Hausmann, R. (2009). The building blocks of economic complexity. *PNAS*, 106(26), 10570–10575.
- Tacchella, A., Cristelli, M., Caldarelli, G., Gabrielli, A., y Pietronero, L. (2012). A new metrics for countries' fitness and products' complexity. *Scientific Reports*, 2, 723.
- Kummu, M., Kosonen, M., y Masoumzadeh Sayyar, S. (2025). Downscaled gridded global dataset for gross domestic product (GDP) per capita PPP over 1990–2022. *Scientific Data*, 12, 178.
- Hartmann, D., Guevara, M. R., Jara-Figueroa, C., Aristarán, M., e Hidalgo, C. A. (2017). Linking economic complexity, institutions, and income inequality. *World Development*, 93, 75–93.
