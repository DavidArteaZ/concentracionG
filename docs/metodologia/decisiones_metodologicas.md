# Decisiones metodológicas

**Proyecto:** Movilidad social y complejidad económica: un estudio de las características económicas regionales que influyen en la movilidad inesperada en México.
**Última actualización:** 29 de septiembre de 2026. Se precisó el orden de D2 (T18 después de los cortes), se corrigieron los conteos de D11, se cerró T5, se cerró T3 y se adoptó D19 (antes P1: el quintil de origen para la heterogeneidad se calcula con el IRE imputado). *(28/09/2026: se agregaron D14–D18, T16–T18 y V1; se modificaron D6, D13, 4.1 y T14.)*
**Estado:** decisiones adoptadas por el equipo. Cada una indica qué se decidió, qué alternativas se descartaron y por qué, para poder defenderla ante revisores.

**Fuentes revisadas:**
- `codigo/R/01_generar_quintiles_ires_emovi.R`.
- `codigo/Informe de movilidad social en México 2025.do` (CEEY), sección 2023.
- `docs/documentacion/Diccionario ESRU EMOVI 2023.xlsx`.
- `data/raw/entrevistado_2023.dta`.

---

## 0. Diseño general

Se estima la asociación entre la complejidad económica (ICE) del municipio donde la persona vivía a los 14 años y su movilidad intergeneracional. Para aislar la parte del destino que no se explica por las condiciones de origen se usa **Double/Debiased Machine Learning (DML)** con un modelo parcialmente lineal (Chernozhukov et al., 2018):

$$Y_i = g(X_i) + \beta\, E_i + u_i, \qquad E_i = e(X_i) + v_i$$

donde:
- $Y_i$ es la posición de destino.
- $X_i$ son las circunstancias de origen.
- $E_i$ es el ICE del municipio de origen.
- $\beta$ es el parámetro de interés.

El análisis es **asociativo, no causal**, y así se redacta en todo el paper.

---

## Bloque 1. Datos y variable a predecir

### D1. Fuente de datos y versión del IRE

**Decisión:**
- Se usa **únicamente la ESRU-EMOVI 2023**. No se descarga ni se une la ESRU-EMOVI 2017.
- El Índice de Recursos Económicos (IRE) principal es el **IRE comparable**, calculado solo con los datos de 2023.
- El IRE no comparable de 2023 se usa como prueba de robustez.

**Por qué:**
- El paper es un corte transversal de 2023. Ninguna pregunta de investigación requiere comparar con 2017.
- "Comparable" no significa que se junten las encuestas. Significa que el índice de 2023 usa solo los activos que también se preguntaron en 2017. Por eso se puede calcular con la base de 2023 sola.
- Se prefiere la versión comparable porque es la que el CEEY usa en sus publicaciones (Informe de Movilidad Social en México 2025). Eso permite validar la construcción del índice contra cifras publicadas (tarea T3).
- La versión no comparable usa más información. Si los resultados cambian con ella, se reporta.

**Alternativa descartada:** usar el IRE no comparable como principal. Tiene documentación más débil y no se puede contrastar con cifras publicadas.

### D2. Definición del quintil (y percentil) de destino

**Decisión:**
- Especificación principal: la posición de destino se calcula **dentro de la cohorte de 25–34 años**. Primero se filtra la cohorte y luego se calculan los cortes ponderados con `factor`.
- Robustez: el quintil nacional con las 4 cohortes, como lo hace el CEEY. Ese quintil se calcula con las 4 cohortes y después se filtra la edad.

**Por qué:**
- El MCA se estima por separado en cada cohorte. En FactoMineR la escala de las coordenadas de cada cohorte depende de su propio eigenvalor, y no se ha validado que coincida con la escala que produce Stata.
- El quintil nacional junta las 4 cohortes, así que depende de esa escala no validada.
- Dentro de una sola cohorte, el ordenamiento de las personas no depende de la escala. Esto elimina el problema en lugar de solo documentarlo.
- La muestra de análisis es solo la cohorte 1, así que no se pierde información relevante.

**Costo aceptado:** las matrices de la especificación principal no se pueden comparar directamente con las del CEEY. Para eso sirve la versión nacional de robustez.

**Orden de los pasos:**
1. El IRE se calcula con la muestra del CEEY. Filtrar la edad antes o después del MCA da exactamente el mismo IRE para la cohorte 1, porque el MCA se estima por cohorte.
2. Los quintiles y percentiles siempre se calculan después del IRE.
3. Cualquier eliminación de observaciones posterior al cálculo de los cortes se reporta, porque deja de cumplirse que cada quintil contenga el 20% de la población.
4. *(29/09/2026)* Los cortes de destino se calculan sobre **toda** la cohorte 1 de la muestra CEEY, que es la población de referencia. La exclusión de quienes vivían en el extranjero o sin municipio a los 14 (T18, 37 casos) se hace **después**, en el script de la muestra de análisis, y se reporta la desviación del 20% por quintil.
5. Pesos: los MCA y todo lo que replica al CEEY (T3) usan `factor_ceey = round(factor)*10`; los percentiles y quintiles propios del proyecto usan `factor` sin redondear (T9).

### D3. Forma de la variable a predecir

**Decisión:**
- Principal: **percentil continuo ponderado del IRE de destino dentro de la cohorte**, en escala de 0 a 100. A los empates se les asigna el percentil promedio del grupo empatado.
- Robustez: quintil de destino, prediciendo las probabilidades de cada quintil y calculando $\hat{Y} = \sum_k k\,\hat{p}_k$.

**Por qué:**
- El percentil conserva información que el quintil desecha. Por ejemplo, las personas en los percentiles 39 y 41 quedan en quintiles distintos aunque están prácticamente en la misma posición.
- Conecta con la literatura de regresión rango-rango (Chetty et al., 2014; Delajara et al., 2020).
- Reduce el problema de que el desvío esté mecánicamente acotado en los extremos. Con quintiles, alguien de Q5 casi no puede superar su pronóstico.
- Los empates se manejan con el promedio porque el IRE se construye con variables binarias y puede tener valores repetidos. *(Nota 29/09/2026: en la cohorte 1 el IRE actual tiene 4,789 valores distintos entre 5,090 personas, así que los empates son pocos; la regla se mantiene por completitud.)*
- Si se usa un clasificador, el pronóstico debe ser el valor esperado y no la clase más probable (argmax). El residuo requiere una esperanza condicional.

### D4. Réplica del MCA del CEEY

**Decisión:** se mantiene la implementación en R con `FactoMineR::MCA`, con la **corrección de signo adaptativa** que ya está en `01_generar_quintiles_ires_emovi.R`. No se usará Stata ni se solicitarán al CEEY sus variables `ireccomp_*`.

**Por qué:**
- Es la opción viable con los recursos del equipo, que no tiene licencia de Stata.
- Con D2 (posición dentro de la cohorte), la diferencia de escala entre FactoMineR y Stata deja de afectar la variable a predecir.
- La diferencia de signo ya se corrigió. Con el `-1` fijo del .do, el índice quedaba invertido en las cohortes 2–4 del IRE actual y 2–3 del IRE de origen: la correlación con el número de activos era de alrededor de −0.99.

**Desviaciones respecto al .do que se reportan en el paper:**
1. FactoMineR estima el MCA sobre la matriz indicadora, mientras que el .do usa `mca ..., method(burt)`. El eje principal es el mismo; la escala puede diferir.
2. El signo se orienta para que el índice tenga correlación ponderada positiva con el número de activos. El .do multiplica siempre por −1.

**Riesgo residual:** no hay validación externa directa del índice. Se mitiga con la tarea T3, que replica la matriz de transición nacional publicada.

---

## Bloque 2. Estructura de la estimación

### D5. Estimación: DML en lugar de un residuo en dos etapas desconectadas

**Decisión:** DML en un modelo parcialmente lineal, con cross-fitting:
1. $\tilde{Y}_i = Y_i - \hat{m}(X_i)$, donde $\hat{m}$ predice el destino con el origen. $\tilde{Y}_i$ es el **desvío**.
2. $\tilde{E}_i = E_i - \hat{e}(X_i)$, donde $\hat{e}$ predice el ICE de origen con las mismas $X$ y los mismos pliegues.
3. Regresión por MCO de $\tilde{Y}$ sobre $\tilde{E}$, cuya pendiente es $\hat{\beta}$.

La implementación es el paquete `DoubleML` (en R o en Python).

**Por qué:** el diseño original, que regresa $Y - \hat{m}(X)$ sobre $E$ sin residualizar $E$, produce en el límite

$$\hat{\beta} \to \beta\,(1 - R^2_{E|X}).$$

Es decir, subestima $\beta$ en la proporción del ICE que explican las variables de origen. Esa proporción no es cero:
- Los hogares de origen con más activos se concentran en municipios más complejos.
- Quitar las variables municipales de $X$ no lo resuelve. Reduce $R^2_{E|X}$ pero no lo lleva a cero, y además introduce un sesgo por variable omitida si la región afecta el destino directamente.

DML corrige esto (teorema de Frisch–Waugh–Lovell con funciones auxiliares estimadas por ML). También da errores estándar válidos sin tener que hacer bootstrap de toda la cadena. Conserva la narrativa del "desvío": $\tilde{Y}$ es exactamente el desvío respecto al pronóstico de origen.

**Alternativas descartadas:**
- El residuo en dos etapas sin residualizar el ICE: está sesgado.
- Un solo modelo paramétrico (logit ordenado con ICE y controles): no capta relaciones no lineales entre las variables de origen. Se conserva solo como punto de comparación (D7).

**Advertencia:** el ICE del municipio de destino depende de si la persona migró, y migrar es parte del propio resultado de movilidad. No se trata como un tratamiento simétrico al ICE de origen (ver sección de pendientes).

### D6. Variables de condicionamiento $X$

**Decisión:**
- **Principal:** $X$ incluye:
  - Circunstancias del hogar de origen: activos (D10), hacinamiento (D12), IRE de origen como una variable más.
  - Circunstancias de la familia: D13.
  - Características individuales predeterminadas: sexo, **edad** (tarea T16) y características étnico-raciales según D13 y D17.
  - `region_14`.
  - Tipo de localidad a los 14 años (p21).
- **Robustez:** se agregan los servicios de la vivienda de origen (p26a agua, p26b electricidad, p26c baño) y los servicios del barrio a los 14 años (p33a–i).

**Por qué:** hay dos errores posibles:
- Si falta un confusor (algo que afecta tanto al ICE como al destino, como la región o el tamaño de la localidad), $\beta$ se sobreestima.
- Si se incluye un mediador del propio ICE, $\beta$ se subestima. Un municipio complejo tiene más infraestructura y por eso el hogar tiene servicios. Controlar por esos servicios descuenta parte del efecto antes de medirlo.

`region_14` y p21 son confusores claros. Los servicios de la vivienda y del barrio son ambiguos (pueden ser confusores o mediadores), por eso quedan como robustez. La diferencia entre ambas especificaciones acota el rango plausible de $\beta$.

**Exclusión obligatoria:** ninguna variable del hogar o de la persona en la actualidad entra en $X$ (tarea T4).

### D7. Algoritmo de las funciones auxiliares

**Decisión:**
- $\hat{m}$ y $\hat{e}$ se estiman con **XGBoost** o **random forest**, eligiendo por el error fuera de pliegue (RMSE para el percentil y el ICE; log-loss para el quintil).
- Siempre se reporta como punto de comparación un **logit ordenado** (quintil) o una regresión lineal (percentil) con las mismas $X$.

**Por qué:**
- Los modelos de ML captan no linealidades e interacciones entre circunstancias sin tener que especificarlas a mano.
- Si el ML no mejora al modelo paramétrico fuera de muestra, la complejidad adicional no se justifica y se debe decir.
- Los hiperparámetros se ajustan con validación cruzada anidada (tarea T8).

### D8. Construcción de los pliegues de la validación cruzada

**Decisión:** pliegues **agrupados por municipio de origen** (`p20_COD`), con estratificación por posición de destino dentro de lo posible. Todas las observaciones de un municipio caen en el mismo pliegue.

**Por qué:**
- El ICE es una variable municipal.
- Si un mismo municipio aparece en entrenamiento y en prueba, $\hat{e}(X)$ puede "memorizar" el municipio a través de variables como la región o la localidad. Eso sobreajusta y hace que $\tilde{E}$ sea artificialmente pequeño, lo que distorsiona $\hat{\beta}$.
- Agrupar por municipio asegura que cada predicción fuera de pliegue sea de un municipio que el modelo no vio.

### D9. Variable dependiente de la etapa 2

**Decisión:**
- **Principal:** el desvío continuo $\tilde{Y}$, en percentiles. Un desvío de +12 significa que la persona llegó 12 percentiles más arriba de lo esperado dado su origen.
- $\hat{\beta}$ se interpreta como el cambio en percentiles de desvío asociado a una desviación estándar de ICE de origen no anticipada por las circunstancias de origen.
- **Robustez:** variables binarias de movilidad **definidas directamente con datos observados** (por ejemplo, 1 si el quintil de destino es mayor que el de origen, o 1 si alguien de origen Q1–Q2 llega a Q4–Q5), usadas como $Y$ dentro del mismo DML. Se reportan varios umbrales.

**Por qué:**
- El desvío continuo es el parámetro natural del modelo parcialmente lineal.
- La versión "1 si superó su pronóstico por +1 quintil" aplica un umbral a un residuo ya estimado. Eso no encaja en DML y su inferencia no es estándar. Definir la variable binaria con datos observados evita el problema.
- Reportar varios umbrales evita la sospecha de haber elegido el más favorable.

---

## Bloque 3. Construcción de variables

### D10. Conjunto de activos de origen

**Decisión:** se usa el **conjunto ampliado** de activos a los 14 años como predictores originales:
- Los 20 del IRE comparable.
- p25 (piso), p27 (tenencia), p28 (tipo de vivienda).
- p26c (baño), p29a–g (espacios de la vivienda).
- p31f, j, l, n, o (tostador, celular, internet, motocicleta, bicicleta).
- p32c, d, h–o (terreno, animales de trabajo o ganado, productos financieros).

Los servicios p26a, b, c siguen la regla de D6.

**Por qué:**
- El IRE comparable eliminó activos para poder comparar con 2017, una restricción que este proyecto no tiene (D1).
- Para una cohorte que tenía 14 años entre 2003 y 2012, activos como el celular, el internet y la computadora tienen variación útil.
- Los modelos de árboles no necesitan reducir las variables con un MCA. El índice resume todo en una sola dimensión y pierde información.
- El IRE de origen se incluye además como una variable más.

### D11. Tratamiento de "no sabe" y faltantes

**Decisión:**
- En los predictores, el "no sabe" (código 8) y los faltantes **se conservan como `NA`**. XGBoost los maneja de forma nativa. Para random forest (`ranger`) el "no sabe" se codifica como categoría propia y se agrega un indicador de faltante.
- **No se replica** la regla del CEEY de convertir el "no sabe" en 0 para tarjeta de crédito, ahorro y automóvil de origen.
- Las 435 personas de la cohorte 1 sin IRE de origen **se conservan**, con IRE de origen = `NA`.
- **Robustez:** IRE de origen imputado con `missMDA::imputeMCA` (Josse y Husson, 2016).
- El IRE de destino y los filtros previos al MCA siguen la muestra del CEEY (D4):
  - Se excluyen 138 casos sin `educ`, 387 sin educación de los padres y 21 sin `region_14`. *(Corrección 29/09/2026: esos conteos no son secuenciales. Aplicados en el orden del .do, en la cohorte 1 se pierden 138, 349 y 19; en la base completa, 292, 1,247 y 46. El flujo oficial es el que genera el script 01 en `data/clean/01_ire_resultados/flujo_muestra.csv`.)*
  - *(29/09/2026)* Con la regla principal ("no sabe" → `NA` en tarjeta y ahorro de origen), **629** de las 5,090 personas de la cohorte 1 no tienen IRE de origen, contra 435 con la regla del CEEY. Los faltantes se concentran en la cuenta de ahorro (362) y la tarjeta (274). Su percentil medio de destino es 55.7, contra 49.4 del resto, lo que confirma que no son una pérdida aleatoria. `p30` (autos de origen) no tiene código de "no sabe" (rango 0–20), así que la regla del automóvil no cambia nada.
  - *(29/09/2026)* El script 01 genera tres versiones del IRE de origen: `irec_or_ceey` (solo para T3), `irec_or_na` (principal) e `irec_or_imp` (robustez, solo cohorte 1).
  - Robustez: estimar el MCA sin los dos primeros filtros y conservar a esas personas con `NA`, reportando la correlación entre ambas versiones del índice.

**Por qué:**
- En la cohorte 1, después de los filtros del CEEY (n = 5,090), 435 personas no tienen IRE de origen. De ellas, 345 tienen un solo activo faltante, sobre todo la cuenta de ahorro (270 casos).
- No son una pérdida aleatoria: hoy están mejor que el resto (42% vs. 37% con computadora; escolaridad media de 2.98 vs. 2.80).
- Eliminarlas sesgaría la muestra hacia personas con menos movilidad ascendente.
- El "no sabe" probablemente dice algo del hogar de origen.
- Convertir el "no sabe" en 0 asume sin evidencia que el hogar no tenía el activo.
- Los activos actuales no tienen faltantes, así que la variable a predecir no se ve afectada.
- Los filtros previos al MCA se mantienen en la especificación principal para no apartarse más del método del CEEY (D4). La educación de los padres faltante probablemente también es informativa (padre ausente), y por eso se evalúa en robustez.

### D12. Hacinamiento

**Decisión:**
- En los predictores de origen se usan **p22 (personas), p23 (cuartos totales) y su cociente, como variables continuas**.
- El binario con corte en 2.5 solo se mantiene dentro del IRE, por fidelidad al método del CEEY.
- p22 = 999 ("no recuerda") se recodifica como `NA` (tarea T5).

**Por qué:**
- El corte en 2.5 desecha información, y los árboles encuentran sus propios cortes.
- Hay 2 casos con p22 = 999 que tanto el .do como el script original clasifican como hacinados. Es un error de codificación heredado.
- *(29/09/2026)* p22 = 999 también se recodifica como `NA` **dentro** del IRE de origen principal (desviación del .do que se reporta en T2). En la muestra CEEY solo hay 2 casos, en las cohortes 3 y 4; ninguno en la cohorte 1. La versión `irec_or_ceey` conserva la regla del .do.

### D13. Variables adicionales de origen

**Decisión:** se incluyen:

| Dimensión | Variables |
|---|---|
| Escolaridad de los padres | `educp` y `educm` por separado; p41–p44 |
| Ocupación de los padres a los 14 | `clasep`, `clasem`, p46, p49, p51, p55; p50 y p56 (afiliación a seguridad social) |
| Estructura del hogar | p39, p40, p57, p58, p45 |
| Características personales y étnico-raciales | `sexo`, `edad`, p111 (lengua indígena), p113* (colorímetro) |
| Territorio | `region_14`, p21 |

- **p110 (autoadscripción) y p112 (color de piel autopercibido)** no entran en la especificación principal; solo en robustez (ver D17). *Modificado el 28/09/2026: p112 estaba originalmente en la principal.*
- p19 y p20_COD se usan solo para unir con el ICE y para formar los pliegues. No son predictores.

**Por qué:**
- Son circunstancias predeterminadas que la literatura de desigualdad de oportunidades identifica como transmisoras de ventaja (Vélez-Grajales et al., 2018; Krozer y Estrada Aguilar, 2025).
- Separar `educp` y `educm` en lugar de usar solo el máximo conserva información.
- p50 y p56 aproximan la formalidad laboral de los padres, que es el contrafactual natural del mecanismo laboral.
- El colorímetro se mide en 2023, pero es una medición objetiva de una característica prácticamente fija, por lo que se trata como circunstancia. En cambio, las medidas autorreportadas (p110, p112) pueden responder al estatus actual (D17).
- La edad es necesaria por el efecto de ciclo de vida dentro de la cohorte y porque el año del ICE de origen depende de ella (D15).

---

## Bloque 4. Etapa 2: estimación principal, heterogeneidad y mecanismos

### 4.1 Estimación principal

$$\tilde{Y}_i = \beta\,\tilde{E}_i + \varepsilon_i$$

- Se estima con los residuos de DML (D5).
- Errores estándar del cross-fitting de DML con **agrupación en dos dimensiones: municipio de origen × UPM** (D16).
- Se reporta $\hat{\beta}$ con la especificación principal de $X$ y con la de robustez (D6).

### 4.2 Heterogeneidad (central para la pregunta de los "pisos pegajosos")

$$\tilde{Y}_i = \beta_0\,\tilde{E}_i + \sum_z \beta_z\,(\tilde{E}_i \times Z_{iz}) + \varepsilon_i$$

- $Z$ es una característica **predeterminada** que también forma parte de $X$: quintil de origen (principal; calculado con el IRE imputado, D19), sexo, región de origen y si la localidad de origen era rural.
- Equivale a la proyección lineal del efecto heterogéneo sobre $Z$ (Semenova y Chernozhukov, 2021).
- **Por qué es central:** la pregunta de investigación es si la complejidad ayuda a romper los "pisos pegajosos". La prueba directa es si la asociación con el ICE es mayor para quienes vienen de Q1–Q2.

### 4.3 Mecanismos (mediación)

**Mediadores candidatos.** Todos ocurren después de los 14 años, en el camino entre el ICE de origen y el destino:

| Mediador | Variables | Advertencia |
|---|---|---|
| Escolaridad alcanzada | `educ`, p9–p10 | Canal principal esperado |
| Empleo formal propio | p18_1–3 (IMSS, ISSSTE, Pemex/Defensa/Marina), p65 | La afiliación puede ser como beneficiario de un familiar. Hay que buscar en el diccionario una pregunta sobre prestaciones del propio empleo antes de usarla |
| Ocupación | `clase`, `cmo` | Solo existe para quien trabaja |
| Formalidad del municipio de origen | Derechohabiencia IMSS/ISSSTE/Pemex de Censos y Conteo (D18) | Contemporánea al ICE; la dirección de la relación es ambigua, por eso la lectura es contable |
| Premio a la especialización | Remuneración por trabajador y proporción de personal remunerado (Censos Económicos, D18) | Misma fuente que el ICE: parte de la correlación es mecánica |
| Migración a un municipio más complejo | 1 si el ICE del municipio de destino es mayor que el de origen, o el cambio en ICE (D14) | Es un mediador y a la vez parte del resultado; se interpreta con cautela |

**Regla que no se negocia:** los mediadores **nunca** entran en $X$ ni en las funciones auxiliares $\hat{m}$ y $\hat{e}$. Son variables posteriores al tratamiento ("bad controls"): incluirlas absorbe el efecto que se quiere medir y puede introducir sesgo por colisionador.

**Método principal: descomposición de Gelbach (2016) sobre los residuos de DML.**
1. Modelo base: $\tilde{Y}$ sobre $\tilde{E}$, que da $\hat{\beta}_{base}$ (sección 4.1).
2. Cada mediador $M_k$ se residualiza sobre $X$ con los mismos pliegues: $\tilde{M}_k = M_k - \hat{h}_k(X)$.
3. Modelo completo: $\tilde{Y}$ sobre $\tilde{E}$ y todos los $\tilde{M}_k$, que da $\hat{\beta}_{full}$ y los coeficientes $\hat{\gamma}_k$.
4. Para cada $k$, se regresa $\tilde{M}_k$ sobre $\tilde{E}$, lo que da $\hat{\delta}_k$.
5. $\hat{\beta}_{base} - \hat{\beta}_{full} = \sum_k \hat{\delta}_k\,\hat{\gamma}_k$. La contribución de cada mediador es $\hat{\delta}_k\hat{\gamma}_k$, y su proporción es $\hat{\delta}_k\hat{\gamma}_k / \hat{\beta}_{base}$.
6. Intervalos de confianza por bootstrap por conglomerados (municipio de origen) de los pasos 2 a 5.

**Por qué Gelbach:**
- A diferencia de agregar mediadores uno por uno (Baron–Kenny), la descomposición no depende del orden en que se agregan.
- Es coherente con el enfoque asociativo del paper. Se reporta como "X% de la asociación se explica por…", en términos contables, no causales.

**Robustez: mediación causal** con DML (Farbmacher et al., 2022) y análisis de sensibilidad al parámetro ρ (Imai, Keele y Tingley, 2010).
- Requiere ignorabilidad secuencial: que nada no observado afecte a la vez al mediador y al destino.
- La habilidad o las preferencias probablemente la violan, porque afectan tanto la escolaridad como el destino. Por eso esta estimación no es la principal y siempre se acompaña del análisis de sensibilidad.

**Tratamiento de quienes no trabajan:** en los mediadores laborales, "no trabaja" se codifica como una categoría del mediador en lugar de eliminar a esas personas. Se reporta cómo cambia la muestra.

**Limitación de poder estadístico:** con n ≈ 4,650 y el ICE variando solo entre municipios, los efectos indirectos y las interacciones tendrán intervalos amplios. Se reporta tal cual; no se eligen solo las especificaciones significativas.

---

## Tareas obligatorias (no son decisiones)

- **T1.** Volver a correr `01_generar_quintiles_ires_emovi.R` con la corrección de signo, regenerar el `.rds` y rehacer todo lo que dependa de él (incluido `02_limpieza_esru.R`).
- **T2.** Documentar en el paper las desviaciones respecto al .do del CEEY (D4).
- **T3.** Validación externa: con el quintil nacional de las 4 cohortes, replicar la matriz de transición nacional publicada por el CEEY (Q1→Q1 ≈ 50%, Q5→Q5 ≈ 51%). Si no se replica, no se avanza.
  - **Cerrada 29/09/2026.** El script 01 en R (n = 14,924) da la fila Q1 = 50.3 / 27.3 / 13.9 / 6.4 / 2.1 y Q5→Q5 = 50.7. Lo publicado por el CEEY (presentación del Informe 2025) es 50 / 28 / 14 / 7 / 2. Por sexo, la réplica da Q1→Q1 = 48.8 en hombres y 51.3 en mujeres (publicado: 49 y 51); Q5→Q5 = 53.5 y 47.1 (publicado: 53 y 47); Q1→Q5 = 3.3 y 1.3 (publicado: 3 y 1). Las diferencias de hasta 0.7 pp en Q1→Q2 y Q1→Q4 son compatibles con el redondeo y con la diferencia de escala indicadora/Burt (D4). Una réplica independiente en Python coincide con el R hasta el decimal 12.
- **T4.** Auditar que no haya fuga de información. Ninguna de estas variables puede entrar en $X$:
  - Activos y vivienda actuales: `ac1–ac16`, `hac`, p89, p94–p99, `tamhog`.
  - Características actuales de la persona: `educ`, p8–p18, p59 en adelante, `clase`, `cmo`, `ocup`, `ingc_pc`, p102, p103.
  - Autoubicación del hogar de origen, respondida hoy: p104.
  - Hogar y ubicación actuales: `jefe_hogar`, `region`, `entidad`, `rururb`.

  La lista queda escrita en el código como exclusión explícita.
- **T5.** Recodificar p22 = 999 como `NA`. Verificar si p99 = 8 automóviles (12 casos) es un código de no respuesta. **Cerrada 29/09/2026:** según el diccionario, p99 va de 0 a 13 sin código de no respuesta, así que p99 = 8 es un conteo válido. p22 = 999 se recodifica como `NA` (ver D12).
- **T6.** Reportar el flujo de la muestra: n después de cada filtro, pérdida por casos incompletos en el MCA y tasas de "no sabe" por cohorte y por posición de destino.
- **T7.** Si se usa un clasificador: $\hat{Y} = \sum_k k\,\hat{p}_k$, no la clase más probable.
- **T8.** Validación cruzada anidada si se ajustan hiperparámetros. Fijar semillas y registrar versiones (`sessionInfo()`, `renv.lock` o `requirements.txt`).
- **T9.** Usar el factor de expansión como peso en el entrenamiento, en la evaluación y en la etapa 2.
- **T10.** Reportar la comparación contra el logit ordenado o la regresión lineal (D7).
- **T11.** Pruebas contra sesgo de recuerdo:
  - Comparar las tasas de "no sabe" de origen por posición de destino.
  - Estimar un modelo solo con escolaridad y ocupación de los padres, que son menos sensibles al recuerdo.
- **T12.** Reportar que los dos índices de hacinamiento no son comparables: el de destino divide entre cuartos para dormir (p89) y el de origen entre cuartos totales contando la cocina (p23).
- **T13.** Interpretar la importancia de las variables con permutación o SHAP agrupados, no con la importancia nativa del algoritmo.
- **T14.** Errores estándar agrupados en dos dimensiones (municipio de origen × UPM) en todas las estimaciones de la etapa 2 (D16).
- **T15.** Mantener un lenguaje asociativo, no causal, en todo el texto.
- **T16.** Incluir `edad` en $X$ (D13, D15). Dentro de la cohorte de 25–34 hay un efecto de ciclo de vida sobre los activos, y el año del ICE de origen depende de la edad. Sin ella, $\tilde{E}$ absorbería diferencias de edad.
- **T17.** Homologar los códigos municipales (`p20_COD` y el municipio actual de `ESRU_mun.dta`) al mismo marco geoestadístico de los ICE antes de unir, considerando los municipios creados entre 2003 y 2023. Reportar cuántas observaciones no se pudieron unir y cómo se resolvió cada caso.
- **T18.** Excluir a quienes a los 14 años vivían en el extranjero o no especificaron municipio (`p20_COD` = 33333 o 99999; 37 casos en la cohorte 1). No tienen ICE de origen. Se reportan en el flujo de la muestra (T6).

---

## Bloque 5. Decisiones adoptadas el 28/09/2026

### D14. Migración

**Datos:** `ESRU_mun.dta` contiene el municipio de residencia actual. En la cohorte 1, 1,545 de 5,559 personas con municipio de origen válido (27.8%; 30.1% ponderado) viven hoy en un municipio distinto al de los 14 años; 524 cambiaron de estado.

**Decisión:**
- **Principal:** el tratamiento es solo el ICE del municipio de origen, independientemente de mudanzas posteriores (estimando de "exposición en la infancia"). La migración **no** se controla en $X$.
- **Mecanismo:** la migración entra como mediador en la descomposición de Gelbach (sección 4.3): 1 si la persona vive hoy en un municipio con mayor ICE que el de origen, o el cambio en ICE.
- **Robustez:** estimación en la submuestra de quienes no migraron, reportada explícitamente como condicionada a una variable posterior al tratamiento.
- **ICE de destino:** solo descriptivo. No se usa como tratamiento ni en interacciones.

**Por qué:**
- El ICE a los 14 años es anterior a cualquier decisión de mudarse, así que su asociación con el destino tiene una interpretación limpia (análoga al enfoque de "lugar en la infancia" de Chetty et al., 2014).
- Controlar por migración, o interactuar el ICE con ser migrante, condiciona a un resultado posterior al tratamiento. Quienes migran difieren por selección (ambición, redes, habilidad), así que esos coeficientes no tienen interpretación limpia.
- El ICE de destino es elegido por la persona y puede haber causalidad inversa (quien consigue un buen empleo se muda a un municipio más complejo). El "premio de migrar hacia mayor complejidad" planteado en el documento de contexto **no se identifica** con este diseño, y así se declara en el paper.

**Amenaza a la validez externa:** la muestra se levantó en los lugares de residencia actual dentro de México. Quienes emigraron al extranjero no están, y probablemente provienen desproporcionadamente de municipios de bajo ICE. Se discute en el paper.

### D15. Año del ICE de origen

**Datos:** la cohorte (25–34 años en 2023) cumplió 14 años entre 2003 y 2012. El año exacto es $2023 - \text{edad} + 14$, con ±1 según la fecha de nacimiento. Los ICE disponibles son 2003, 2008 y 2013.

**Decisión:**
- **Principal:** interpolación lineal del ICE al año exacto en que la persona tenía 14: $ICE_{t} = ICE_{t_0} + \frac{t - t_0}{t_1 - t_0}(ICE_{t_1} - ICE_{t_0})$ entre los años censales adyacentes.
- **Robustez:** (a) ICE del año censal más cercano; (b) ICE de 2003 para todos.
- Esta decisión está **sujeta a la verificación V1**.

**Por qué:**
- Asignar el año más cercano introduce un error de medición en escalones de hasta 2.5 años, que tiende a subestimar el efecto. La interpolación lo reduce y no requiere extrapolar, porque todos los años caen dentro de 2003–2013.
- El ICE está estandarizado cada año, así que la interpolación opera sobre posiciones relativas, lo cual es coherente.
- El ICE de 2003 para todos es anterior al tratamiento para toda la cohorte, pero para los más jóvenes se mide hasta 9 años antes de que cumplieran 14. Tiene más error y por eso queda como robustez.
- Como el año del ICE depende de la edad, la edad debe estar en $X$ (T16).

### D16. Agrupación de los errores estándar

**Datos:** en la cohorte 1 hay 688 municipios de origen (mediana de 4 personas por municipio; 182 municipios con una sola persona). El diseño muestral tiene 1,322 UPM y 5 estratos, ubicados en 503 municipios de residencia actual.

**Decisión:**
- **Principal:** agrupación en dos dimensiones, municipio de origen × UPM (Cameron, Gelbach y Miller, 2011), con la estructura de datos agrupados de `DoubleML`.
- **Robustez:** (a) solo municipio de origen; (b) estado de origen (32 grupos) con wild cluster bootstrap.
- Los pliegues de la validación cruzada (D8) usan la misma estructura de grupos.

**Por qué:**
- Según Abadie et al. (2023), se agrupa al nivel donde se asigna el tratamiento (el ICE, asignado por municipio de origen) y al nivel del diseño muestral (UPM). Aquí aplican ambos y no están anidados, porque los migrantes cruzan de un municipio de origen a una UPM en otro municipio.
- Con 688 y 1,322 grupos hay suficientes para la agrupación en dos dimensiones.
- La agrupación por estado capta la correlación espacial entre municipios vecinos. Con solo 32 grupos requiere wild cluster bootstrap.

### D17. Autoadscripción étnico-racial (p110) y color de piel autopercibido (p112)

**Datos:** categorías de p110 en la cohorte 1: Negra (61), Indígena (386), Blanca (371), Mestiza (3,099), Ninguna (1,679).

**Decisión:**
- **Principal:** solo medidas menos sensibles al estatus actual: p113* (colorímetro) y p111 (habla lengua indígena).
- **Robustez:** se agregan p110 y p112. En p110, la categoría "Negra" (61 casos) se agrupa con otra por su tamaño, y se documenta con cuál.
- Esto modifica D13, donde p112 estaba en la especificación principal.

**Por qué:**
- p110 y p112 se preguntan hoy, y la autoidentificación étnico-racial en México responde al nivel socioeconómico: las personas de mayor estatus tienden menos a identificarse como indígenas o de piel oscura (Villarreal, 2014).
- Usarlas como circunstancias de origen puede introducir el destino como predictor.
- El colorímetro es una medición objetiva, y hablar una lengua indígena es poco sensible al estatus actual.

### D18. Fuente de formalidad municipal

**Decisión:**
- **Principal:** porcentaje de población derechohabiente de IMSS, ISSSTE y Pemex/Defensa/Marina por municipio, del Censo 2000, Conteo 2005 y Censo 2010 (en 2010 se excluye el Seguro Popular), interpolado al año en que la persona tenía 14, igual que en D15.
- **Robustez:** trabajadores asegurados en el IMSS por municipio (disponibles a nivel municipal desde 1998), divididos entre la población del municipio.
- **Mecanismo aparte ("premio a la especialización"):** remuneración por trabajador y proporción de personal remunerado de los Censos Económicos.

**Por qué:**
- La derechohabiencia se mide por lugar de residencia, que coincide con dónde creció la persona, y cubre el periodo 2003–2012 con interpolación. Su limitación es que incluye a familiares beneficiarios.
- En los datos del IMSS hay que verificar si el municipio corresponde a donde está registrado el patrón y no al lugar de trabajo o residencia. Si es así, las empresas registradas en otro municipio distorsionan el dato. Por eso queda como robustez.
- La medida de los Censos Económicos comparte fuente con el ICE, así que parte de su correlación con el ICE es mecánica. Se declara al reportarla.

---

## Bloque 6. Decisiones adoptadas el 29/09/2026

### D19. Quintil de origen para la heterogeneidad (antes P1)

**Decisión:**
- **Principal:** $Z$ = quintil de origen dentro de la cohorte 1 calculado con el IRE de origen imputado (`q_or_c1_imp`, a partir de `irec_or_imp`). Nadie queda fuera del análisis de heterogeneidad.
- **Robustez:** el mismo análisis con `q_or_c1_na` (629 personas fuera) y con `q_or_c1_ceey` (435 fuera).
- **Qué se imputa:** solo las respuestas faltantes ("no sabe") de los activos de origen, con `missMDA::imputeMCA`. Cada respuesta faltante se sustituye por una probabilidad estimada a partir de las respuestas observadas de la persona y de la estructura de asociación entre activos en la cohorte. El índice se estima después sobre la tabla completa. La mayoría de las 629 personas tiene un solo activo faltante (cuenta de ahorro o tarjeta de crédito de los padres).
- **Implicación para $X$:** la sección 4.2 exige que $Z$ forme parte de $X$. Por eso $X$ incluye `q_or_c1_imp`. Los activos de origen siguen entrando con `NA` (D10, D11), y el IRE de origen que entra como una variable más sigue siendo `irec_or_na` (D11).
- **Requisito previo:** volver a correr el script 01 con `NCP_MAX_CV = 10`. En la primera corrida, `estim_ncpMCA` eligió ncp = 5, que era el tope de búsqueda.

**Por qué:**
- La tasa de "no sabe" crece con la posición de destino (7.0% en Q1 contra 14.5% en Q5). Excluir a esas personas eliminaría de forma desproporcionada a quienes ascendieron y sesgaría la interacción de "pisos pegajosos".
- La imputación afecta solo a la pieza faltante del índice. El resto sale de respuestas observadas.

**Antecedentes (texto original de P1):**


**Problema que resolvía:** con la regla principal de D11, 629 personas de la cohorte 1 (12.4%) no tienen IRE de origen y, por lo tanto, tampoco quintil de origen. Si $Z$ = quintil de origen usa `irec_or_na`, la interacción principal de los "pisos pegajosos" se estima sin ellas, y ya se sabe que no son aleatorias (percentil medio de destino 55.7 contra 49.4).

**Opciones consideradas:**
- (a) $Z$ a partir de `irec_or_imp` (nadie queda fuera); `irec_or_na` y `irec_or_ceey` como robustez.
- (b) $Z$ a partir de `irec_or_ceey` (435 fuera).
- (c) Una categoría propia "sin quintil de origen" en $Z$.

**Dato relevante (29/09/2026, corrida del script 01):** la tasa de "no sabe" en algún activo de origen crece con la posición de destino: 7.0% en Q1, 8.7% en Q2, 11.7% en Q3, 11.2% en Q4 y 14.5% en Q5 (cohorte 1, ponderado). La falta de IRE de origen sigue el mismo patrón (7.0% en Q1 contra 12.3% en Q5). Excluir a estas personas de $Z$ elimina de forma desproporcionada a quienes ascendieron, lo que refuerza la opción (a). También es evidencia relevante para T11: el "no sabe" se concentra en productos financieros de los padres (cuenta de ahorro y tarjeta), cuya tenencia probablemente desconocía el hijo a los 14 años.

**Nota sobre la versión imputada:** en la primera corrida, `estim_ncpMCA` eligió ncp = 5, que era el tope de búsqueda. El tope se subió a 10 (`NCP_MAX_CV`); hay que volver a correr el script antes de usar `irec_or_imp`.

**Dato relevante:** entre quienes tienen ambas versiones, la correlación entre `irec_or_ceey` e `irec_or_na` es de 0.99999, así que la elección decide quién entra y no cómo se ordena a las personas.

---

## Verificaciones pendientes

### V1. Homologación del SCIAN entre años del ICE

**Qué hay que verificar:** si las ramas de los Censos Económicos se homologaron entre las versiones del SCIAN (2002, 2007, 2013, 2018, 2023) antes de calcular el ICE de cada año.

**Por qué importa:**
- Si no se homologaron, cada año del ICE se calcula sobre un conjunto distinto de actividades.
- El ICE de cada año, visto por separado, sigue siendo válido como posición relativa dentro de ese año.
- Lo que deja de estar bien definido es la **interpolación entre años** (D15, principal) y cualquier comparación entre años, como la matriz de transición municipal 2003–2023 del primer avance.

**Diagnóstico rápido:** listar los códigos de rama usados en cada año y comparar los conjuntos. Si difieren en número o en códigos, no hubo homologación.

**Protocolo mientras tanto:**
1. Se continúa con el código y los modelos asumiendo que la homologación está bien hecha.
2. El ICE se lee desde **un solo archivo**, generado por un solo script. Ningún script posterior calcula ni modifica el ICE, y ningún resultado depende de valores copiados a mano.
3. Todo el proceso (unión con ICE → funciones auxiliares de DML con ajuste de hiperparámetros → etapa 2 → mecanismos → tablas y figuras) se puede volver a correr de principio a fin con un solo comando y semillas fijas (T8).
4. **Ningún resultado se redacta como definitivo** en el paper hasta cerrar V1.

**Si resulta que no se homologó:**
1. Se homologan las ramas con las tablas de correspondencia SCIAN del INEGI, se recalcula el ICE y se vuelve a correr todo el proceso sin cambios.
2. Si la homologación no es factible, la especificación principal de D15 pasa a ser la **robustez (a)**: ICE del año censal más cercano. Como cada persona recibe el ICE de un solo año, no mezcla clasificaciones distintas.
3. Se documenta el cambio y la razón en este archivo.

---

## Referencias

- Abadie, A., Athey, S., Imbens, G. W., & Wooldridge, J. M. (2023). When should you adjust standard errors for clustering? *Quarterly Journal of Economics*, 138(1), 1–35.
- Cameron, A. C., Gelbach, J. B., & Miller, D. L. (2011). Robust inference with multiway clustering. *Journal of Business & Economic Statistics*, 29(2), 238–249.
- Villarreal, A. (2014). Ethnic identification and its consequences for measuring inequality in Mexico. *American Sociological Review*, 79(4), 775–806.

- Chernozhukov, V., Chetverikov, D., Demirer, M., Duflo, E., Hansen, C., Newey, W., & Robins, J. (2018). Double/debiased machine learning for treatment and structural parameters. *The Econometrics Journal*, 21(1), C1–C68.
- Chetty, R., Hendren, N., Kline, P., & Saez, E. (2014). Where is the land of opportunity? The geography of intergenerational mobility in the United States. *Quarterly Journal of Economics*, 129(4), 1553–1623.
- Delajara, M., Campos-Vázquez, R. M., & Vélez-Grajales, R. (2020). *Social Mobility in Mexico. What Can We Learn from Its Regional Variation?* CEEY.
- Farbmacher, H., Huber, M., Lafférs, L., Langen, H., & Spindler, M. (2022). Causal mediation analysis with double machine learning. *The Econometrics Journal*, 25(2), 277–300.
- Gelbach, J. B. (2016). When do covariates matter? And which ones, and how much? *Journal of Labor Economics*, 34(2), 509–543.
- Imai, K., Keele, L., & Tingley, D. (2010). A general approach to causal mediation analysis. *Psychological Methods*, 15(4), 309–334.
- Josse, J., & Husson, F. (2016). missMDA: A package for handling missing values in multivariate data analysis. *Journal of Statistical Software*, 70(1), 1–31.
- Krozer, A., & Estrada Aguilar, L. A. (2025). *Características étnico-raciales y desigualdad de oportunidades en México.* CEEY.
- Monroy-Gómez-Franco, L. A., & Vélez Grajales, R. (2025). *Informe de movilidad social en México 2025.* CEEY.
- Semenova, V., & Chernozhukov, V. (2021). Debiased machine learning of conditional average treatment effects and other causal functions. *The Econometrics Journal*, 24(2), 264–289.
- Vélez Grajales, R., Monroy-Gómez-Franco, L. A., & Yalonetzky, G. (2018). *Inequality of Opportunity in Mexico.* CEEY.
