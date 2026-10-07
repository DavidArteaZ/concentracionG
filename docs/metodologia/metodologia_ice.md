# Metodología del Índice de Complejidad Económica (ICE) municipal

**Proyecto:** Movilidad social y complejidad económica en México
**Versión:** 0.5 (06/10/2026). Contiene los resultados de la primera ejecución completa de los módulos 01–07, el Módulo 08 (base `ecomplexity` y gráficas, refactorizadas el 06/10/2026), el apéndice en inglés y la revisión de literatura sobre ICE municipal en México. Documento vivo.
**Alcance:** construcción, diagnóstico y validación del ICE municipal (2003, 2008, 2013, 2018 y 2023) que entra como regresor en el modelo DML. La estimación del DML se documenta en `decisiones_metodologicas.md`.

---

## 1. Datos y fuentes

Todos los insumos crudos están en `data/raw/ice/` y no se modifican.

| Insumo | Archivo | Fuente | Contenido y notas |
|---|---|---|---|
| Censos Económicos por municipio y actividad | `saic_2003_2023/*.csv` (5 archivos) | INEGI, Sistema Automatizado de Información Censal (SAIC), serie *Censos Económicos 2024. Resultados definitivos*; consulta del 08/09/2026 | UE y PBT por municipio × rama/clase SCIAN; años de referencia 2003, 2008, 2013, 2018 y 2023. La serie viene homologada al SCIAN por INEGI. **Celda vacía = dato omitido por confidencialidad** (nota del propio archivo). Los archivos traen relleno de bytes nulos al final, que se elimina al leer. |
| Totales municipales de los Censos Económicos | `saic_totales_municipales.csv` | INEGI, SAIC, misma serie; consulta del 04/10/2026 | UE, H001A (personal ocupado total), H010A (personal remunerado), J000A (remuneraciones) y A131A (VACB) por municipio. Es el validador principal (Módulo 06). Tiene de 0 a 3 celdas suprimidas por año. |
| PIB per cápita municipal | `gdp_perCapita_1990_2022.csv` | Kummu, Kosonen y Masoumzadeh Sayyar (2025), *Scientific Data* 12:178, doi:10.1038/s41597-025-04487-x; datos en doi:10.5281/zenodo.10976733 | PIB per cápita PPP 1990–2022 en polígonos GADM nivel 2 (2,457 para México). **La variación dentro de cada estado es modelada** (ver §6). |
| Polígonos GADM | `gadm41_MEX_2/` | GADM v4.1 | 2,457 unidades, en WGS84. Los IDs siguen orden alfabético y **no** son claves INEGI. |
| Marco geoestadístico municipal | `00mun_2023/` | INEGI, Marco Geoestadístico 2023 | 2,478 polígonos en *Mexico ITRF2008 LCC*; incluye los 3 municipios creados en 2024 (24059, 25019, 25020), que no están en CUCG_2023. |
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
| `01_limpieza_saic.py` | Lee SAIC (quita los bytes nulos y los encabezados), clasifica cada celda como valor, cero o suprimida, verifica conteos y ramas por año y reasigna los municipios creados en 2024. Limpia los totales municipales y construye la remuneración media y el VACB por persona ocupada, ambos en log relativo al nacional. | `saic_largo.csv.gz`, `saic_totales_limpio.csv` |
| `02_ice.py` | Núcleo, RCA, PCI espectral, proyección del ICE, estandarización, diagnósticos, validación contra `ecomplexity` y variante con ramas comunes a todos los años | `ice_municipal.csv`, `pci_rama.csv`, `diagnosticos_espectrales.csv` |
| `03_diagnostico_variables.py` | Documenta por qué UE: censura del PBT condicional a presencia, condicionamiento espectral y degeneración del ICE con PBT | `tabla_ue_pbt.csv` |
| `04_sensibilidad.py` | Malla de umbrales, reglas de exclusión R1–R4, nivel clase, Fitness-Complexity y ramas comunes; impacto en entrevistados de EMOVI | ICE alternativos en formato largo y tabla de sensibilidad |
| `05_crosswalk_gadm_inegi.py` | Tabla puente GADM↔INEGI (por nombre, más verificación con población de localidades) y tabla padre–hijo de municipios creados entre 2003 y 2023 | `crosswalk_gadm_inegi.csv`, `municipios_padre_hijo.csv` |
| `06_validacion_externa.py` | Validación del ICE contra remuneración media y productividad (totales censales), con controles de escala y diversidad; PIB solo descriptivo; regla Rama vs. Clase | `validacion_*.csv`, `rama_vs_clase.csv` |
| `07_export_dml.py` | Base final para el DML: ICE base y alternativos, núcleo, escala y diversidad | `data/clean/ice/ice_para_dml.csv` |
| `export_ecomplexity.py` (Módulo 08, parte 1) | Base municipio × rama con las variables de `ecomplexity` para el ICE final, la proximidad entre ramas y un catálogo de nombres de rama. Se ejecuta desde `run_all` y desde el notebook. | `ecomplexity_rama_ue_<año>.csv.gz` (uno por año), `proximidad_ramas.csv.gz`, `catalogo_ramas.csv` |
| `anexo_tablas.py` | Tablas adicionales del Apéndice Metodológico: municipios por año con altas, bajas y motivos; ramas incluidas y excluidas; varianza del ICE explicada por la escala; validación con categorías de tamaño; concentración del PBT | `outputs/ice/anexo/*.csv` |
| `08_graficas.ipynb` (Módulo 08, parte 2) | Notebook con las gráficas del notebook original, actualizadas con los datos nuevos, organizadas por tipo y en ciclo por año | `figuras/ice/*.png` (57 figuras) + `figuras/ice/anexo/*.png` (2), `figuras/ice/tablas/*.csv` |

**Entorno de ejecución (04/10/2026):** Python 3.13.16, numpy 2.5.3, pandas 3.0.5, scipy 1.18.1, matplotlib 3.11.2, pyshp 3.1.6 y ecomplexity 0.5.3 (commit `554cc5d`). Está en `codigo/ice/environment.yml`. La corrida completa tarda unos 6 minutos. Los logs con todos los conteos están en `outputs/ice/logs/`.

**Desviaciones respecto al prompt:**
1. Las tablas intermedias se guardan en `.csv.gz` en lugar de parquet (no había `pyarrow`).
2. El cruce espacial se hace sin geopandas (localidades en WGS84 con `matplotlib.path`).
3. Fitness-Complexity usa como criterio de convergencia que el ranking no cambie durante 200 iteraciones (Tacchella no converge en valores con matrices no anidadas).
4. Las filas de datos esperadas por archivo SAIC son 3 menos que las que contaba el notebook original (este contaba la línea vacía, la nota y la línea final).
5. La base del Módulo 08 se entrega en **cinco archivos `.csv.gz`, uno por año** (3,286,998 filas en total; 12–13 MB cada uno). Un solo archivo pesaría unos 64 MB comprimido y excedería el límite de transferencia. Para unirlos: `pd.concat(pd.read_csv(f) for f in sorted(Path('data/clean/ice').glob('ecomplexity_rama_ue_*.csv.gz')))`.

---

## 3b. Resultados principales (corrida del 04/10/2026)

**Módulo 01.**
- UE nunca está suprimida.
- El PBT está suprimido en 65.6 / 64.2 / 62.8 / 61.8 / 60.7% de las celdas rama×municipio con UE > 0 (2003 a 2023).
- Municipios con datos: 2,447 / 2,455 / 2,456 / 2,465 / 2,469 (2023 ya con la reasignación de 2024).
- La UE total municipal coincide al 100% con la suma por rama.
- La remuneración media no se puede calcular en 462 municipio-año (personal remunerado igual a 0). Hay 89 VACB negativos.

**Módulo 02.**
- Núcleo: de 2,085 a 2,337 municipios y de 261 a 271 ramas; quedan fuera del núcleo entre 0.05 y 0.20% de las UE.
- La matriz es una sola componente conexa en todos los años: λ1 = 1; λ2 de 0.326 a 0.354; λ3 de 0.121 a 0.134.
- La correlación con `ecomplexity` es 1.000000 y la proyección reproduce exactamente el ICE del núcleo. Ningún municipio queda sin ICE.
- Spearman entre años: de 0.91 a 0.96. Con solo las ramas comunes: ≥ 0.9995.
- **El ICE está muy asociado con la escala:** en el núcleo, su Spearman con la diversidad es 0.89, con el log de UE de 0.85–0.87 y con el log de población de 0.78–0.82.
- Las ramas con mayor PCI son financieras o de baja ubicuidad (5221, 5225, 5222, 3341, 3346, 4811), con ubicuidad de 10 a 28. Las de menor PCI son textiles básicos, agua, panaderías y tortillerías, y abarrotes.

**Módulo 03.**
- La censura del PBT no es aleatoria: es de 93–97% en el quintil más chico de municipios y de 49–54% en el más grande.
- El ICE con PBT se degenera: en 2023 la matriz tiene 2 componentes (λ2 = 1, 99.96% de empates); en 2018, λ2 ≈ λ3 (0.439 vs. 0.429); hay valores extremos de 17 a 47 desviaciones estándar.
- Su correlación con el ICE de UE va de −0.79 a +0.79 según el año.

**Módulo 04.**
- Malla de 27 umbrales: Spearman con la base de 0.992 a 1.000.
- Exclusión de ramas: R1 y R3, ≥ 0.999; R2 y R4, de 0.996 a 0.998 (de 4 a 7% de los municipios cambia de quintil).
- Nivel clase: 0.97 (22–24% cambia de quintil). Fitness-Complexity: 0.95 (28–30% cambia de quintil).
- Entrevistados de la cohorte 1 fuera del núcleo: 32 (de 0.6 a 1.05% ponderado). Hay 15 sin ICE por la geografía de su año censal.
- 5211, 5232, 2121 y 2212 ya quedan fuera del núcleo por `P_MIN`.

**Módulo 05.**
- Cruce por nombre: 2,425 exactos y 24 por prefijo; 8 resueltos por población. Ninguno sin resolver.
- Relaciones: 2,390 son 1:1, 17 son 1:n, 19 son n:1 y 31 ambiguas. Solo hay 1 discrepancia entre nombre y población.
- Tabla padre–hijo: padre identificado para 28 de 29 municipios. Iliatenco (12081) queda sin emparejar.

**Módulo 06.**
- Niveles, columna (4) (escala + diversidad + FE de estado): β del ICE sobre la remuneración media relativa de 0.24 a 0.37, y sobre el VACB por persona ocupada relativo de 0.55 a 0.63, con p del wild bootstrap < 0.0001 en todos los años.
- El R² parcial del ICE baja de cerca de 0.35 (sin controles) a 0.06–0.09 (con controles).
- Crecimiento: el ICE predice mayor crecimiento posterior de la remuneración relativa (0.07 en 2003–2023; 0.15 en el panel de 5 años) y de la productividad (0.19; 0.23).
- Rama vs. Clase: diferencias de R² parcial de −0.007 (2003) y +0.005 (2013), con intervalos que incluyen el cero → **la base es Rama**.
- PIB de Kummu (descriptivo): correlación de 0.49–0.51.

**Módulo 07.**
- `ice_para_dml.csv`: 12,292 municipio-año con el ICE base y 33 especificaciones alternativas, `log_pob`, `log_ue_total`, `diversidad` y `en_nucleo`.

## 3c. Módulo 08 — Base `ecomplexity` y gráficas

### Parte 1: `export_ecomplexity.py` → `data/clean/ice/ecomplexity_rama_ue_<año>.csv.gz`

Una fila por municipio × rama × año, para todos los municipios (dentro y fuera del núcleo) y las ramas del núcleo de cada año. Columnas:

| Columna | Definición |
|---|---|
| `año` | Año de referencia censal (2003, 2008, 2013, 2018, 2023). |
| `clave_municipio`, `nom_municipio` | Clave INEGI de 5 dígitos. El nombre viene del Marco Geoestadístico 2023 y, si no está ahí, de CUCG_2003. |
| `rama` | Rama SCIAN (4 dígitos) del núcleo de ese año. |
| `rca`, `mcp` | RCA de Balassa con la estructura propia del municipio y el denominador nacional del núcleo; `mcp` = 1 si RCA ≥ 1. |
| `diversity` | Número de ramas del núcleo con `mcp` = 1 en el municipio. |
| `ubiquity` | Número de municipios del núcleo con `mcp` = 1 en la rama. |
| `eci` | ICE final; idéntico al de `ice_para_dml.csv` (se verifica con `assert`). |
| `pci` | PCI estandarizado con la media y la desviación estándar del ICE del núcleo. |
| `density` | Σ_p' mcp_cp' φ_pp' / Σ_p' φ_pp', con φ_pp' = min[P(p∣p'), P(p'∣p)] calculada con la M del núcleo. |
| `coi` | Σ_p (1 − mcp_cp) · density_cp · PCI_p, estandarizado con el núcleo. |
| `cog` | Fórmula de `ecomplexity`, dividida entre la desviación estándar del ICE del núcleo. |
| `en_nucleo` | Columna adicional: indica si el municipio pertenece al núcleo de estimación. |

**Verificación:** en el núcleo, `mcp`, `eci`, `pci`, `density`, `coi` y `cog` coinciden con `ecomplexity` 0.5.3 (correlación de 1.000000 en los cinco años). Fuera del núcleo, las variables son la proyección descrita en §2.5 y no existen en el paquete.

**Salidas auxiliares:**
- `proximidad_ramas.csv.gz`: φ entre pares de ramas, por año.
- `catalogo_ramas.csv`: nombres de las 279 ramas, tomados de los propios archivos SAIC.

### Parte 2: `codigo/ice/08_graficas.ipynb` → `figuras/ice/`

Cada tipo de gráfica tiene una función `graficar_*` (el diseño) y una celda de ejecución (años, municipios y periodos). Los textos comunes de fuente y notas, la paleta de regiones CEEY y la resolución (300 dpi) están en la celda de configuración.

| Código | Gráfica (origen en el notebook original) | Archivos |
|---|---|---|
| — | Tablas de los 10 municipios con mayor y menor ICE y de las 10 ramas con mayor y menor PCI, por año (celdas 23 y 25) | `tablas/ranking_municipios_ice.csv`, `tablas/ranking_ramas_pci.csv` |
| G01 | Distribución del ICE: histograma + KDE por año y curvas de todos los años (celdas 31–35 y 129) | 6 |
| G02 / G03 | Distancia–PCI de los 5 municipios con mayor y menor ICE, por año (celdas 50–61) | 10 |
| G04 / G05 | Las 5 ramas con mayor y menor PCI: barras y distancia de los municipios, por año (celdas 63–75) | 10 |
| G06 | Matriz de diversificación 2003–2023 para Monterrey (19039) y Santo Domingo Yodohino (20524) (celdas 77 y 79) | 2 |
| G07 | Violín del ICE por región CEEY, por año (celdas 80–81) | 5 |
| G08 | ICE vs. COI, Norte vs. Sur, por año (celda 82) | 5 |
| G09 | Matriz de transición nacional de quintiles: 2003–2023 y los cuatro periodos de 5 años (celda 83) | 5 |
| G10 | Matrices de transición por región CEEY, 2003–2023 (celda 84) | 1 |
| G11 | Mapa del ICE por año (celda 85) | 5 |
| G12–G14 | Mapas 2003–2023: variación del ICE, tipología de movilidad y salto de quintil (celdas 86–88) | 3 |
| G15 | Espacio-producto de las ramas por año (celdas 94–102) | 5 |

**Cambios respecto al notebook original:**
1. **No se reproducen** las gráficas de distribución PBT vs. UE y Rama vs. Clase con prueba de normalidad (D1) ni los diagramas de Taylor (D5).
2. **Mapas sin geopandas:** se dibujan con `pyshp` + `matplotlib` sobre el Marco Geoestadístico 2023, tomando uno de cada 3 vértices para acelerar (`SIMPLIFICAR`). La escala del ICE se trunca en ±3, y la de la variación en el percentil 99 de |ΔICE|.
3. **Espacio-producto:** el ERGM del notebook original (sin semilla; solo agregaba al azar enlaces con φ entre 0.35 y 0.65) se reemplaza por la regla estándar de Hidalgo et al. (2007): árbol de expansión máxima más los enlaces con φ ≥ 0.55. El layout usa una semilla fija. Las visualizaciones interactivas de `ipysigma` no se incluyen.
4. **Tipología de movilidad:** se conserva el orden de reglas del original (rezago Q1–Q2 → ascendente → descendente → liderazgo Q4–Q5 → Q3). Por ese orden, un municipio que pasa de Q4 a Q5 cuenta como "ascendente", no como "liderazgo".
5. Las notas al pie ahora declaran el núcleo, la estandarización relativa a cada año y que los municipios en gris o negro de los mapas son los que no tienen dato o se crearon después del año inicial. Los diagramas distancia–PCI listan en la nota a los municipios graficados.

**Para regenerar:** después de `run_all`, abrir el notebook y ejecutar todas las celdas (unos 2 minutos). Con `REGENERAR_BASE = True` vuelve a calcular la base `ecomplexity`.

**Refactorización del 06/10/2026 (reglas de diseño):**
- **Idioma:** `IDIOMA = "en"` (por defecto, para el artículo en inglés) o `"es"`; todos los textos pasan por `T(es, en)`. Los nombres de rama en inglés están en `codigo/ice/catalogo_ramas_en.csv` (279 ramas; traducción propia de los títulos SCIAN con terminología NAICS). Abreviaturas en inglés: ECI, PCI, COI, COG, RCA.
- **`finalizar(fig, titulo, pie, ref=None, ...)`:** centra el título sobre el eje de simetría de la figura y lo envuelve a su ancho; alinea la fuente/notas a la izquierda del contenido y las envuelve con `textwrap`, reduciendo el ancho hasta que el texto renderizado mide como máximo el ancho de gráfica + leyenda + barra de color (nunca se corta). El recorte de la imagen es simétrico respecto a `ref` (los ejes principales o todo el contenido), por lo que la gráfica queda centrada. `guardar()` usa ese recorte.
- **Tamaños:** título base 13 pt × 1.1 = 14.3 pt; G10 título 32 pt (2 × 16) y fuente 14.25 pt (1.5 × 9.5); mapas G11–G14 título 26 pt (2 × 13).
- **G01:** eje Y común a los cinco años (`ylim_distribucion()`: máximo del histograma de densidad y del KDE).
- **G02/G03:** eje Y común (`YLIM_PCI`, rango del PCI en todos los años); barra de color con `Normalize` lineal (colormap secuencial viridis), marcas equiespaciadas, `extend="max"`. G02: 0 a `VMAX_RCA_TOP` (percentil 95 del RCA de los cinco municipios con mayor ICE, máximo entre años, redondeado hacia arriba; = 9) con línea roja en RCA = 1. G03: 0.0 a 1.0.
- **G04/G05:** etiquetas de rama envueltas a 30 caracteres (sin truncar); etiquetas de ubicuidad dentro de la caja (`textos_dentro()` amplía el eje X si alguna se sale); orden de la leyenda igual al de las barras; nota al pie con separación 1.5 × la estándar.
- **G07/G08:** centrados sobre los ejes; en G08 la leyenda pasa debajo de la gráfica.
- **G09/G10:** eje Y de Q5 (arriba) a Q1 (abajo), eje X de Q1 a Q5. G10 usa una sola barra de color compartida y paneles del mismo tamaño.
- **Mapas:** polígonos centrados (`set_aspect("equal", anchor="C")`, márgenes de 0.5% y recorte simétrico respecto a los ejes del mapa).
- **A01:** ejes y leyenda explícitos ("Reference year (census round)", etiquetas de quintil con tamaño del municipio).

## 3d. Apéndice Metodológico (`docs/anexo_ice.docx`) y análisis de escala

**Versión vigente (06/10/2026): en inglés**, 38 páginas, 9 figuras, 2 mapas, 2 matrices y 10 tablas. Título: *Methodological Appendix — A Municipal Economic Complexity Index for Mexico, 2003–2023: Construction, Validation and Spatial Patterns*. Cambios respecto a la versión en español del 04/10: (1) la tabla de fuentes se convirtió en párrafos; (2) se eliminó toda mención a ESRU-EMOVI, cohortes, la edad de 14 años, la migración y el modelo de movilidad (el texto es un análisis económico y espacial); (3) la sección 3.4 explica qué es un eigenvector de M̃, por qué se descarta el primero (eigenvalor trivial 1, vector constante por ser M̃ estocástica por filas) y por qué el segundo ordena la complejidad (componente no trivial de decaimiento más lento de las reflexiones; relajación del normalized cut, Mealy et al., 2019), y las condiciones de conexidad y brecha λ2–λ3; (4) la sección 5.1 quedó sin referencias a entregas previas ni a criterios descartados; (5) nueva sección 1.1 con antecedentes de ICE subnacional en México y la contribución; (6) correcciones de una revisión independiente: máximo |ICE| con PBT de 7 a 47 d.e. (no 17), R² parcial 0.06–0.08, censura del sector 22 de 98–100%, 99.95% de empates en 2023, malla de umbrales = 26 alternativas + base, p ≤ 0.0001 (mínimo alcanzable con B = 9,999).

**Antecedentes (sección 1.1):** el ICE municipal con conteos de unidades económicas **no es nuevo**. Gómez-Zaldívar, Gómez-Zaldívar y Carrillo Ramírez (2024, *Investigaciones Regionales* 59, doi 10.38191/iirr-jorr.24.018) lo calculan con conteos de establecimientos del DENUE (2014 y 2019); Gómez Zaldívar y Gómez Zaldívar (2026, *Investigaciones Regionales*, doi 10.38191/iirr-jorr.26.005) con UE de los Censos 2004 y 2019, solo manufactura a 4 dígitos (86 grupos, 2,459 municipios). Con otras variables: Gómez-Zaldívar y Gómez-Zaldívar (2023, *RRS* 53(1)), personal ocupado y producción/valor agregado por trabajador, Censos 2009–2019 (solo 1,490 municipios en 2019 por confidencialidad); González Sierra et al. (2023, *REMEF* 18(2)), PBT por persona ocupada, SAIC 2018. Estatal: Chávez et al. (2017, *RRS* 47(2)). La contribución propia: serie homogénea de cinco censos con todos los sectores, núcleo + proyección, diagnóstico espectral de la censura, descomposición de escala con validación, y variables completas del espacio-producto verificadas contra *py-ecomplexity*.

Se apoya en `anexo_tablas.py`, que agrega estos resultados:

- **Escala (respuesta a la crítica de Soloaga):** la escala y la diversidad explican una parte muy grande de la varianza del ICE. R² con log de población: 0.69–0.72. Agregando log de UE: 0.75–0.80. Agregando diversidad: 0.85–0.88. Agregando efectos fijos de estado: 0.88–0.90. Con categorías de tamaño (<15 mil, 15–50 mil, 50–350 mil, ≥350 mil habitantes): 0.66–0.69. El componente del ICE independiente de la escala es solo 10–12% de su varianza, aunque dentro de cada categoría de tamaño el ICE tiene una desviación estándar de 0.45–0.80.
- **Ese componente predice la remuneración media:** con categorías de tamaño, log de población, log de UE, diversidad y efectos fijos de estado, β = 0.25–0.40, con p ≤ 0.0001 en todos los años.
- **El ICE no sustituye al ingreso:** su correlación con el log de la remuneración media relativa es de 0.57–0.61.
- **Implicación para el modelo de movilidad (no se menciona en el apéndice):** la identificación depende del componente independiente de la escala. La especificación con `log_pob` es la prueba directa de la crítica y condiciona la potencia estadística.
- **Concentración del PBT observado:** el 1% de municipios con más PBT concentra entre 51 y 63% (contra 24–29% en el caso de las UE). Entre 9 y 21% de los municipios no tiene ninguna celda de PBT observada. Es un factor que amplifica el colapso de la matriz; la causa principal es la censura.
- **Municipios sin UE en el censo:** Nicolás Ruíz en 2003. En 2023, seis municipios de Chiapas: Amatenango de la Frontera, Bejucal de Ocampo, Bella Vista, La Grandeza, Capitán Luis Ángel Vidal y Honduras de la Sierra.
- **Figuras propias del anexo:** `figuras/ice/anexo/A01_censura_pbt_por_quintil.png` y `A02_espectro_ue_vs_pbt.png`, generadas en la sección 12 del notebook.

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
| D9 | Municipios creados en 2024 en SAIC 2023: 24059 → 24028 y 25019 → 25006 (decretos); 25020 → 25011 (Guasave, aportante principal de cuatro) | Dejarlos separados | ESRU-EMOVI y CUCG_2023 no tienen esas claves (el marco geoestadístico 2023 sí; en los mapas aparecen sin dato) | Solo afecta al ICE 2023, que no entra en la interpolación principal. Robustez: ICE 2023 sin 25020. |
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
7. **Selección en la validación:** los 462 municipio-año sin personal remunerado (mediana de 18 UE; 71% fuera del núcleo) no entran en la regresión de remuneración media.
8. **Error de medición en las regresiones de crecimiento:** si y₀ se mide con error, el ICE puede absorber parte de la reversión a la media; los β de crecimiento se presentan como asociación.
9. **El ICE es casi colineal con la diversidad** (Spearman de 0.89). Por eso A3 se evalúa con la diversidad como control explícito.

---

## 7. Afirmaciones que pueden salir del ICE

Solo se sostienen si los resultados de los módulos las respaldan; el estado de cada una se llena al ejecutar.

| Afirmación | Evidencia que la respalda | Estado |
|---|---|---|
| **A1.** El ICE se calcula sobre una matriz bien condicionada y no depende de municipios o ramas con muy pocas observaciones | Módulo 02: una sola componente conexa, brecha espectral clara y núcleo documentado | **Respaldada.** Una componente; λ2 − λ3 ≈ 0.21 en todos los años; umbrales sin efecto relevante (Spearman ≥ 0.992). |
| **A2.** UE es la variable adecuada porque es la única sin supresión por confidencialidad | Módulo 03: censura del PBT de 61–66% condicional a presencia, comparación espectral | **Respaldada.** La censura es no aleatoria (93–97% en municipios chicos) y el ICE con PBT se degenera (componentes desconectadas, λ2 ≈ λ3, signo inestable). |
| **A3.** El ICE se asocia con el desarrollo municipal más allá de la escala y de la diversidad simple | Módulo 06: β del ICE y su R² parcial con controles de UE totales, población, diversidad y efectos fijos de estado, sobre remuneración media y productividad | **Respaldada, con salvedades.** β > 0 y p < 0.0001 en todos los años con todos los controles; R² parcial de 6 a 9%. Salvedades: misma fuente que el ICE, se excluyen los municipios sin empleo asalariado y es asociación, no causalidad. |
| **A4.** La elección Rama/Clase sigue una regla fijada de antemano | Módulo 06.7 | **Respaldada.** La regla no favorece a Clase (ambos intervalos incluyen el cero); la base es Rama. |
| **A5.** Los resultados no dependen de los umbrales ni de las ramas institucionales | Módulo 04: Spearman, cambios de quintil y β del DML con cada alternativa | **Respaldada a nivel del ICE** para los umbrales y R1–R4. Frente a Clase y Fitness (22–30% de cambios de quintil), queda **pendiente** de volver a estimar β en el DML. |

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
- [x] Descarga y limpieza de los totales municipales de SAIC.
- [x] Módulos 01–07 ejecutados (04/10/2026).
- [x] Módulo 08: base `ecomplexity` y 57 gráficas actualizadas (04/10/2026).
- [x] Apéndice Metodológico del ICE (`docs/anexo_ice.docx`) y tablas de `anexo_tablas.py` (04/10/2026).
- [ ] Revisión manual de `outputs/ice/crosswalk_revision.csv` (99 casos, ninguno bloqueante).
- [ ] Asignar el padre de Iliatenco (12081); el emparejamiento automático falló.
- [ ] Volver a estimar β del DML con cada ICE alternativo (A5 frente a Clase y Fitness).
- [ ] Decisiones diferidas: papel de la validación en el paper y asignación de ICE a municipios creados después de los 14 años.

**Referencias**
- Hidalgo, C. A., y Hausmann, R. (2009). The building blocks of economic complexity. *PNAS*, 106(26), 10570–10575.
- Tacchella, A., Cristelli, M., Caldarelli, G., Gabrielli, A., y Pietronero, L. (2012). A new metrics for countries' fitness and products' complexity. *Scientific Reports*, 2, 723.
- Kummu, M., Kosonen, M., y Masoumzadeh Sayyar, S. (2025). Downscaled gridded global dataset for gross domestic product (GDP) per capita PPP over 1990–2022. *Scientific Data*, 12, 178.
- Hidalgo, C. A., Klinger, B., Barabási, A.-L., y Hausmann, R. (2007). The product space conditions the development of nations. *Science*, 317(5837), 482–487.
- Hartmann, D., Guevara, M. R., Jara-Figueroa, C., Aristarán, M., e Hidalgo, C. A. (2017). Linking economic complexity, institutions, and income inequality. *World Development*, 93, 75–93.
