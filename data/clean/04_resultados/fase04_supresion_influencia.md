# Diagnóstico de supresión e influencia (corrida del 16/10/2026)

Script: `codigo/modelo/04_supresion_influencia.py`. Salidas: `data/clean/04_resultados/`. Usa las mismas 20 repeticiones, los mismos pliegues y XGBoost/XGBoost de la fase 2. Al inicio, el script verifica que reproduce exactamente la fase 2 (β y SE). **La especificación principal y la lectura fijada no cambian.** Esto es descriptivo.

## A1. Supresión: la escala condicional al ICE

Modelo auxiliar: Y = g(X sin escala) + b·ICE + γ·log_pob14 + u. La escala entra de forma lineal, no flexible como en la principal. Se ajustó una sola función auxiliar nueva, E[log_pob14 | X sin escala], con R² fuera de pliegue de 0.30.

| Término | Coef. | SE (2 dim.) | IC 95% | p |
|---|---|---|---|---|
| ICE dada la escala (por 1 DE de ICE) | 4.73 | 2.17 | [0.47, 8.99] | 0.029 |
| Escala dado el ICE (por 1 DE de log población) | −3.97 | 1.89 | [−7.67, −0.27] | 0.035 |

Descomposición exacta del β total, como mediana de las repeticiones:

**1.21 (total) = 4.73 (ICE dada la escala) + (−2.40 × 1.51) (escala × su relación con el ICE residual) = 4.73 − 3.60**

Lectura:
- Es supresión en sentido estricto, no solo colinealidad numérica. Dadas las circunstancias de origen, más complejidad se asocia con más movilidad, y más población (con la misma complejidad) se asocia con menos. Como los municipios complejos son también grandes (δ = 1.51), los dos efectos se cancelan en el total.
- El p de 0.029 corresponde a otra especificación, con la escala lineal. No sustituye al p = 0.053 de la principal, que es la que manda por la regla. Sirve para describir el mecanismo, no como resultado principal.
- El coeficiente negativo de la escala es un hallazgo en sí mismo. Debe defenderse: congestión, competencia y costo de vida, o bien efectos de composición (ver B1, Estado de México).

## A2. ICE residual por tamaño de municipio (especificación principal)

| Tamaño (Soloaga) | n | Municipios | Var(Ẽ) | % del denominador de β | β dentro del grupo | p |
|---|---|---|---|---|---|---|
| < 15 mil | 323 | 122 | 0.11 | 6% | 9.6 | 0.04 |
| 15–50 mil | 812 | 256 | 0.14 | 18% | 4.2 | 0.19 |
| 50–350 mil | 1,803 | 251 | 0.17 | 43% | 7.1 | 0.06 |
| ≥ 350 mil | 2,134 | 68 | 0.11 | 32% | 1.8 | 0.75 |
| Todas | 5,072 | 667 | 0.14 | 100% | 5.1 | 0.053 |

- La variación independiente del ICE está repartida entre tamaños: Var(Ẽ) va de 0.11 a 0.17. No depende de unos pocos municipios pequeños y atípicos; los menores de 15 mil aportan solo 6% del denominador.
- El β se apoya sobre todo en municipios de 50 a 350 mil habitantes. En las grandes ciudades (≥ 350 mil, 40% del peso muestral) es casi nulo y muy impreciso. Esto es heterogeneidad descriptiva, no una prueba formal (4.2).

## B1. Excluir un estado a la vez (32 corridas)

| | Principal (5.09) | Total (1.21) |
|---|---|---|
| Rango | 3.43 a 7.58 | 0.63 a 1.69 |
| Sin Puebla (21) | 3.43 (p = 0.15) | 0.63 |
| Sin Ciudad de México (09) | 3.91 (p = 0.14) | 0.78 |
| Sin Estado de México (15) | **7.58 (p = 0.002)** | 1.69 (p = 0.052) |
| Resto de los estados (29) | 4.39 a 5.74 | 0.99 a 1.66 |

- El signo es positivo en las 64 corridas. La magnitud depende de tres estados.
- La sensibilidad al Estado de México se concentra en un solo municipio (B3).

## B2. Excluir municipios con |Ẽ| más alto

| Exclusión | Principal | Total |
|---|---|---|
| 1% (7 municipios, 28 personas) | 5.28 (p = 0.056) | 1.22 |
| 5% (34 municipios, 176 personas) | 5.42 (p = 0.011) | 0.83 |

Los municipios con ICE más "inesperado" no generan el β condicional. Al quitarlos, el SE baja y β se mantiene.

## B3. Municipios más influyentes (β sin el municipio; funciones auxiliares fijas)

| Clave | n | Tamaño | Ẽ medio | β principal sin él | Cambio |
|---|---|---|---|---|---|
| 15031 | 20 | ≥ 350 mil | −1.07 | 7.06 | +1.98 |
| 21119 | 2 | 50–350 mil | +0.67 | 3.92 | −1.16 |
| 09004 | 6 | 50–350 mil | +0.58 | 4.58 | −0.51 |
| 09010 | 22 | ≥ 350 mil | +0.54 | 4.70 | −0.39 |

Las claves son INEGI. El script no tiene catálogo de nombres. Por la clave, 15031 sería Chimalhuacán y 21119 San Andrés Cholula; **falta verificarlo**. Un municipio con 20 personas mueve β en 2 puntos (40%). Sus residentes tienen un ICE muy bajo para su tamaño y, aun así, resultados de destino altos para lo que predice X. En el total, ningún municipio mueve β más de 0.33.

## Riesgos y lectura

1. **Fragilidad:** el β condicional es positivo en todas las exclusiones, pero su magnitud y su significancia dependen de pocos municipios del centro del país (Chimalhuacán, Cuajimalpa, Álvaro Obregón y uno de Puebla). Con p = 0.053, cualquier exclusión lo cruza en una u otra dirección. No debe reportarse ninguna de esas versiones como resultado; se reportan todas, como sensibilidad.
2. **La supresión es real en los datos y tiene interpretación económica,** pero la escala lineal (A1) es una simplificación. La versión flexible (la principal) es la que vale.
3. **Limitación de B:** las funciones auxiliares se ajustaron con todos los estados. El reajuste completo sin el Estado de México, Ciudad de México y Puebla (3 estados × 2 repeticiones, unos 25 minutos) confirmaría si la sensibilidad sobrevive al reajuste. Lo recomiendo solo para esos tres.
