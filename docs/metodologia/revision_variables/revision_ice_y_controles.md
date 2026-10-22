# Escala del ICE y conjunto de controles X: revisión

**Fecha:** 21/10/2026. **Base revisada:** `ice_v2/data/clean/02_base_dml.csv` (n = 5,072) y `ice_v2/codigo/modelo/03_dml.py` (versión con `--ice`, D25).
**Código de los diagnósticos:** `dudas_variables/codigo/diag_colinealidad.py` y `diag_percentil_ice.py` (Python 3.13, numpy 2.5.3, pandas 3.0.5, scikit-learn 1.9.1; sin componentes aleatorios).
Los números de las secciones 2 y 3 que no vienen de `03_resultados*` son **diagnósticos lineales en muestra (MCO-FWL ponderado, SE agrupado solo por `cve_ice`)**, no estimaciones DML. Sirven para comparar escalas, no para reportar.

---

## 1. ¿El ICE entra "crudo"?

No. Hay dos estandarizaciones:

1. El ICE ya está estandarizado **por año entre municipios** (D15): es una posición relativa nacional.
2. En `03_dml.py`, `tratamiento()` lo vuelve a estandarizar **con los factores de expansión dentro de la muestra** (media 0, DE 1). Por eso β se lee "percentiles de destino por 1 DE de ICE entre las personas de la cohorte".

En la muestra, el ICE V1 tiene media ponderada 1.69 y DE 1.32 en unidades de (1): la cohorte viene de municipios más complejos que el municipio promedio, porque la población se concentra en ellos. Distribución: asimetría −0.59, concentrada arriba (P75 = 2.86, P90 = 3.19) con cola larga a la izquierda (P10 = −0.29, mínimo −2.56).

## 2. ¿Transformarlo a percentil?

### Riesgo crítico: búsqueda de especificación
Ya vimos los β y sus p con la escala en DE. Si ahora se cambia la escala principal, el cambio queda condicionado a los resultados. Cualquier transformación nueva va como **robustez declarada** y se reporta pase lo que pase, nunca como reemplazo de la principal.

### Qué cambia y qué no
- **Un cambio lineal (DE, ×10, etc.) no cambia nada sustantivo.** β se reescala y el z, el p y el MDE quedan idénticos.
- **El percentil es una transformación no lineal (rango). Cambia el estimando.** En el PLR, si el efecto no es lineal en D, β es un promedio ponderado de efectos marginales, con pesos proporcionales a la variación residual de D. El rango:
  - estira la parte alta (P75–P99 ocupa solo 0.6 unidades de ICE, pero 25 puntos de percentil);
  - comprime la cola izquierda (municipios rurales poco complejos), que hoy aporta mucha palanca.
- Por lo tanto, puede ayudar con el problema de influencia que ya encontramos (Puebla-Tlaxcala en V1, Cuautla en V2), pero también le da más peso a diferencias pequeñas de ICE entre zonas metropolitanas.

### Diagnóstico lineal (V1, X principal, mismo conjunto de 155 columnas)

| Escala de D | β | SE | t | R²(D\|X) |
|---|---|---|---|---|
| DE ponderada (actual) | 4.47 | 1.67 | 2.69 | 0.882 |
| Percentil entre personas, por 10 puntos | 1.40 | 0.53 | 2.63 | 0.865 |

La correlación entre las dos escalas es 0.98 y el t casi no cambia. Con la X actual, el percentil **no aporta información nueva ni precisión**. Lo único que cambia es la lectura.

### Ventajas reales del percentil
- Se lee como una **pendiente rango-rango** (Y ya es percentil), que es el lenguaje de la literatura de movilidad (Chetty et al., 2014): "subir 10 percentiles en el ICE de origen se asocia con +1.4 percentiles de destino".
- No depende de la escala de una medida sintética que no tiene unidades naturales.

### Costos
- **¿Percentil de qué distribución?** Entre personas de la muestra (lo que probé), el percentil depende de la muestra y se convierte en un regresor generado (pequeño, pero hay que declararlo). Entre municipios a nivel nacional, se lee "más complejo que el X% de los municipios", pero le da a un municipio de 2,000 habitantes el mismo peso que a la CDMX. Hay que elegir una y justificarla.
- **Empates y asignación por edad:** el ICE varía por municipio y año interpolado (2,369 valores únicos). Los empates se resuelven con rango medio; hay que fijar la regla.
- En V2 la concentración arriba es mayor (P75–P99 en 3.70–4.15), así que el problema de estirar diferencias pequeñas pesa más.
- Hay que reajustar e(X) completo (fase 1 y 2). No se puede reusar `predicciones_oof`.

### Recomendación
1. **Mantener DE como principal.**
2. Para la interpretación, que no cuesta nada, reportar el efecto de ir del **P25 al P75 de la distribución ponderada del ICE (1.70 DE)**: con β = 5.09, son ≈ 8.7 percentiles de destino; con el IC al 95% (−0.07 a 10.24 por DE), de −0.1 a 17.4. También P10–P90 (2.64 DE).
3. Si quieren la lectura rango-rango, agregarla como robustez pre-declarada en `decisiones_metodologicas.md` (D nueva), con percentil ponderado entre personas, rango medio para empates y el mismo pipeline de 20 repeticiones.

## 3. ¿Cuántos controles hay y si importan su número y su colinealidad?

### Conteo
- **83 variables** con rol `X_principal` en `diccionario_variables_02.csv`: 33 binarias, 15 nominales, 10 ordinales, 12 continuas (incluye `log_pob14`; en V2 se sustituye por `log_pob14_zm*`).
- Después de convertir las nominales en dummies (con dummy de faltante): **155 columnas** (`entorno_fase1.json`, `n_x`).
- En la regresión lineal, el imputador agrega indicadores de faltante: **214 columnas, de rango 198**. Hay 16 columnas perfectamente redundantes, sobre todo los indicadores de faltante del colorímetro (p113*), que son idénticos entre sí.
- Además de X principal, hay 15 en `X_robustez`.

### ¿Importa que sean muchas? No por el número, sí por otras dos razones
- p/n ≈ 155/5,072 ≈ 3%. DML está diseñado para X de dimensión alta: el cross-fitting evita el sesgo por sobreajuste de las funciones auxiliares, y XGBoost y RF regularizan. El número de controles, por sí solo, no es un problema.
- **Lo que sí importa es cuánto explica X al ICE.** Ese es el "VIF" relevante, y se reduce a uno solo: el del tratamiento.

### El VIF que les sugirieron: dónde sí aplica y dónde no
- El VIF_j = 1/(1 − R²_j) mide cuánto se infla la varianza del coeficiente de la variable j por su correlación con las demás.
- **Para los controles es irrelevante.** No interpretamos sus coeficientes, y por Frisch-Waugh-Lovell la colinealidad *entre controles* no sesga β ni infla su varianza. Para los árboles, la colinealidad solo reparte la importancia entre variables parecidas; la predicción no cambia.
- **Para el tratamiento es central.** VIF_D = 1/(1 − R²(e)). Con los R² fuera de pliegue de XGBoost:

| Versión | R² e(X) | VIF_D | Variación de D no explicada por X |
|---|---|---|---|
| V1 | 0.86 | ≈ 7 | 14% |
| V2 ZM2010 | 0.90 | ≈ 10 | 10% |
| V2 ZM2020 | 0.92 | ≈ 12.5 | 8% |

β se identifica solo con esa variación residual. Esto explica en buena parte la potencia baja. Es el VIF que vale la pena reportar en el paper.

Para la descripción: entre controles hay 16 columnas con VIF > 10 y 35 pares con |r| > 0.8. Casi todos son indicadores de faltante que coinciden (p42a/p43a, clasem/p55/p56) o un índice junto a sus componentes (`irec_or_na` y `q_or_c1_imp`, r = 0.90). El número de condición es ≈ 3.8 × 10⁶, por la redundancia perfecta.

### Riesgo crítico: no seleccionar controles por VIF
- Quitar un confusor porque es colineal reintroduce sesgo por variable omitida. La colinealidad se paga con varianza; omitir un confusor se paga con sesgo.
- Seleccionar con los datos y después estimar en la misma muestra rompe la inferencia (problema post-selección).
- La selección de X se hace **por el rol causal de cada variable** (D6), no por estadísticos de correlación.

### Lo que sí hay que cuestionar de X (por rol causal, no por número)
1. **Posibles controles malos (mediadores) en la X principal.** La ocupación, la clase y la formalidad de los padres a los 14 años (`clasep`, `clasem`, p46, p49, p51, p55, p50, p56) se miden al mismo tiempo que el tratamiento. La estructura productiva del municipio es persistente y determina en parte qué empleos tienen los padres. Si es así, controlar por ellos le quita a β el canal "complejidad → empleo de los padres → hijos". El propio D13 los justifica como "contrafactual natural del mecanismo laboral". Entonces el β principal es la asociación **más allá de la ocupación de los padres**. Hay que redactarlo así, o hacer una especificación sin ese bloque para acotar el rango (análogo a lo que D6 hizo con los servicios).
2. **Amplificación de sesgo.** Variables que predicen mucho el ICE pero no afectan Y (casi instrumentos) reducen la variación residual sin quitar confusión, y pueden **amplificar** el sesgo por confusores no observados (Pearl, 2010; Middleton et al., 2016). Los candidatos son la escala (`log_pob14`), la región y el tipo de localidad. No significa quitarlos, porque son confusores plausibles. Significa reportar la sensibilidad.
3. **Redundancia mecánica en la lineal.** Las 16 columnas redundantes no afectan las predicciones (lstsq usa pseudo-inversa), pero conviene eliminar en `matriz_x` los indicadores de faltante duplicados. Es un cambio cosmético y no altera β.

### Pruebas que propongo (sin cambiar la X principal)
- **Reportar VIF_D** (tabla de arriba) en la sección de identificación.
- **Sensibilidad a confusión no observada para DML:** Chernozhukov, Cinelli, Newey, Sharma y Syrgkanis (2022, "Long Story Short"). Usar como referencia bloques observados (padres, región, escala): ¿cuánta confusión adicional, comparada con la de esos bloques, haría que β = 0?
- **Especificaciones por bloques, declaradas antes de verlas:** (a) X mínima: solo predeterminadas, sin la ocupación de los padres; (b) X principal; (c) X principal + `X_robustez`. Así se acota β entre "sin mediadores dudosos" y "todo".

## 4. Pendiente de información
- Para que la especificación sin ocupación de los padres esté bien definida, falta confirmar la fecha de referencia de p46–p56 en el cuestionario EMOVI (¿"cuando tenías 14 años"?) y si p50/p56 son formalidad del jefe o de cada padre. No lo pude verificar con los archivos del proyecto.
- Los cambios al 02 y al 03 son del hilo "ICE por zona metropolitana". Aquí no se editó ninguno de los dos scripts.
