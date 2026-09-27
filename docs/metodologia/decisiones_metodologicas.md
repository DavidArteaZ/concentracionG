# Decisiones metodológicas

**Proyecto:** Movilidad social y complejidad económica: un estudio de las características económicas regionales que influyen en la movilidad inesperada en México.
**Última actualización:** 26 de septiembre de 2026.
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

### D3. Forma de la variable a predecir

**Decisión:**
- Principal: **percentil continuo ponderado del IRE de destino dentro de la cohorte**, en escala de 0 a 100. A los empates se les asigna el percentil promedio del grupo empatado.
- Robustez: quintil de destino, prediciendo las probabilidades de cada quintil y calculando $\hat{Y} = \sum_k k\,\hat{p}_k$.

**Por qué:**
- El percentil conserva información que el quintil desecha. Por ejemplo, las personas en los percentiles 39 y 41 quedan en quintiles distintos aunque están prácticamente en la misma posición.
- Conecta con la literatura de regresión rango-rango (Chetty et al., 2014; Delajara et al., 2020).
- Reduce el problema de que el desvío esté mecánicamente acotado en los extremos. Con quintiles, alguien de Q5 casi no puede superar su pronóstico.
- Los empates se manejan con el promedio porque el IRE se construye con variables binarias y tiene pocos valores distintos.
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
  - Características individuales predeterminadas: sexo y características étnico-raciales.
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
  - Se excluyen 138 casos sin `educ`, 387 sin educación de los padres y 21 sin `region_14`.
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

### D13. Variables adicionales de origen

**Decisión:** se incluyen:

| Dimensión | Variables |
|---|---|
| Escolaridad de los padres | `educp` y `educm` por separado; p41–p44 |
| Ocupación de los padres a los 14 | `clasep`, `clasem`, p46, p49, p51, p55; p50 y p56 (afiliación a seguridad social) |
| Estructura del hogar | p39, p40, p57, p58, p45 |
| Características personales y étnico-raciales | `sexo`, p111, p112, p113* (colorímetro) |
| Territorio | `region_14`, p21 |

- **p110** queda pendiente hasta revisar sus categorías.
- p19 y p20_COD se usan solo para unir con el ICE y para formar los pliegues. No son predictores.

**Por qué:**
- Son circunstancias predeterminadas que la literatura de desigualdad de oportunidades identifica como transmisoras de ventaja (Vélez-Grajales et al., 2018; Krozer y Estrada Aguilar, 2025).
- Separar `educp` y `educm` en lugar de usar solo el máximo conserva información.
- p50 y p56 aproximan la formalidad laboral de los padres, que es el contrafactual natural del mecanismo laboral.
- El colorímetro se mide en 2023, pero es una característica prácticamente fija, por lo que se trata como circunstancia.

---

## Bloque 4. Etapa 2: estimación principal, heterogeneidad y mecanismos

### 4.1 Estimación principal

$$\tilde{Y}_i = \beta\,\tilde{E}_i + \varepsilon_i$$

- Se estima con los residuos de DML (D5).
- Errores estándar del cross-fitting de DML, **agrupados por municipio de origen**. El ICE varía solo entre municipios, así que las observaciones de un mismo municipio no son independientes.
- Se reporta $\hat{\beta}$ con la especificación principal de $X$ y con la de robustez (D6).

### 4.2 Heterogeneidad (central para la pregunta de los "pisos pegajosos")

$$\tilde{Y}_i = \beta_0\,\tilde{E}_i + \sum_z \beta_z\,(\tilde{E}_i \times Z_{iz}) + \varepsilon_i$$

- $Z$ es una característica **predeterminada** que también forma parte de $X$: quintil de origen (principal), sexo, región de origen y si la localidad de origen era rural.
- Equivale a la proyección lineal del efecto heterogéneo sobre $Z$ (Semenova y Chernozhukov, 2021).
- **Por qué es central:** la pregunta de investigación es si la complejidad ayuda a romper los "pisos pegajosos". La prueba directa es si la asociación con el ICE es mayor para quienes vienen de Q1–Q2.

### 4.3 Mecanismos (mediación)

**Mediadores candidatos.** Todos ocurren después de los 14 años, en el camino entre el ICE de origen y el destino:

| Mediador | Variables | Advertencia |
|---|---|---|
| Escolaridad alcanzada | `educ`, p9–p10 | Canal principal esperado |
| Empleo formal propio | p18_1–3 (IMSS, ISSSTE, Pemex/Defensa/Marina), p65 | La afiliación puede ser como beneficiario de un familiar. Hay que buscar en el diccionario una pregunta sobre prestaciones del propio empleo antes de usarla |
| Ocupación | `clase`, `cmo` | Solo existe para quien trabaja |
| Formalidad del municipio de origen | Fuente externa (por ejemplo, puestos registrados en el IMSS por municipio) | Hay que confirmar disponibilidad municipal para 2003–2012 |
| Migración a un municipio más complejo | Diferencia entre ICE de destino y de origen | Es un mediador y a la vez parte del resultado; se interpreta con cautela |

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
- **T4.** Auditar que no haya fuga de información. Ninguna de estas variables puede entrar en $X$:
  - Activos y vivienda actuales: `ac1–ac16`, `hac`, p89, p94–p99, `tamhog`.
  - Características actuales de la persona: `educ`, p8–p18, p59 en adelante, `clase`, `cmo`, `ocup`, `ingc_pc`, p102, p103.
  - Autoubicación del hogar de origen, respondida hoy: p104.
  - Hogar y ubicación actuales: `jefe_hogar`, `region`, `entidad`, `rururb`.

  La lista queda escrita en el código como exclusión explícita.
- **T5.** Recodificar p22 = 999 como `NA`. Verificar si p99 = 8 automóviles (12 casos) es un código de no respuesta.
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
- **T14.** Errores estándar agrupados por municipio de origen en todas las estimaciones de la etapa 2.
- **T15.** Mantener un lenguaje asociativo, no causal, en todo el texto.

---

## Decisiones pendientes (aún no discutidas)

- **P1.** Especificación de la migración: si se incluye la interacción ICE de origen × migrante o ICE de destino × migrante, y cómo tratar la selección de quienes migran.
- **P2.** Asignación del año del ICE de origen: el año censal más cercano a cuando la persona tenía 14 años, interpolación, o promedio del periodo de la infancia.
- **P3.** Nivel de agrupación de los errores si se incluye el ICE de destino (municipio de origen, de destino o agrupación en dos dimensiones).
- **P4.** Revisar las categorías de p110 y decidir si se incluye.
- **P5.** Confirmar la fuente de formalidad municipal para 2003–2012.

---

## Referencias

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
