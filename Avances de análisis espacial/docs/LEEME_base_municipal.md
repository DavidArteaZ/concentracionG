# Base municipal de movilidad relativa por IRE y estructura productiva 2023

## Archivos para GeoDa

Abra `data/clean/municipios_mov_ice_2023.shp`. Sus archivos `.dbf`, `.shx`, `.prj`
y `.cpg` deben permanecer en la misma carpeta y conservar el mismo nombre base.
El archivo ZIP contiene ese conjunto, la tabla CSV y el diccionario de variables.
La tabla también se entrega en CSV y la base espacial en RDS.

Se mantienen los 2,478 municipios, el orden, las geometrías y la proyección del
shapefile original `data/raw/00mun.shp`. Los atributos originales `CVEGEO`,
`CVE_ENT`, `CVE_MUN` y `NOMGEO` se conservan. `CVEGEO` es la clave completa de
cinco dígitos; `CVE_MUN` es solo la parte municipal de tres dígitos.

## Definiciones acordadas

- Cohorte: personas de 25–34 años.
- Agregación de movilidad e ingreso: municipio de origen a los 14 años (`p20_COD`).
- Ponderador: `factor` original, sin redondear.
- Posiciones del IRE ya construidas: origen `pct_or_c1_ceey` y `q_or_c1_ceey`;
  destino `pct_act_c1` y `q_act_c1`.
- Se conserva la versión CEEY usada en las matrices previas del proyecto.
  El script de generación que está en `raw` también incluye las variantes
  `*_na` y `*_imp`; esta entrega no sustituye la versión seleccionada por ellas.
- Los percentiles y quintiles conservan su referencia nacional dentro de la
  cohorte. No se recalculan por municipio ni después de la unión cartográfica.
- Las posiciones de destino se atribuyen al municipio de origen incluso cuando
  la persona haya migrado posteriormente.

### Movilidad

Para cada promedio o proporción se utilizan los ponderadores de las observaciones
con las variables necesarias disponibles:

| Campo | Cálculo |
|---|---|
| `cam_pct` | Promedio ponderado de percentil de destino − percentil de origen |
| `asc_pct` | 100 × proporción ponderada con quintil de destino > quintil de origen |
| `des_pct` | 100 × proporción ponderada con quintil de destino < quintil de origen |
| `per_pct` | 100 × proporción ponderada con quintil de destino = quintil de origen |
| `mov_abs` | Promedio ponderado de la magnitud del cambio entre percentiles |
| `sal_q1` | Probabilidad ponderada de destino > Q1 entre quienes parten de Q1 |

`sal_q1` se expresa entre 0 y 1. `asc_pct`, `des_pct` y `per_pct` se expresan
entre 0 y 100. `cam_pct` y `mov_abs` están en puntos percentiles.
El nombre `mov_abs` refiere al valor absoluto del cambio **relativo de posición**;
no mide crecimiento absoluto de ingresos ni de riqueza.

### Ingreso

`ing_pc` es el promedio ponderado de `ingc_pc`, etiquetado en la fuente como
«Ingreso per cápita del hogar — imputado». No es ingreso laboral individual.
Se incluyen todas las personas de 25–34 años con ingreso disponible y municipio
de origen identificado, aunque no tengan ambos quintiles o percentiles del IRE.
No se realiza una nueva imputación de ingresos.

### ECI y unidades económicas

- `eci_2023`: columna `ice` de `ice_municipal.csv`, año 2023, especificación `base`.
  Coincide con `eci` del archivo por rama hasta su precisión de redondeo.
- `ue_2023`: suma de UE de los registros municipales de **Rama**, de cuatro dígitos,
  en `2023_SAIC_Exporta_202698_037586.csv`. No se suman las clases ni los agregados
  estatales para evitar doble conteo.
- `ue_top5`: UE en hasta cinco ramas presentes con mayor PCI disponible en cada
  municipio. Presente significa UE > 0. Se excluyen las ramas sin PCI del
  ordenamiento y se eligen hasta cinco de las restantes. Si hay menos de cinco,
  se utilizan las disponibles. No se exige RCA ≥ 1 ni `mcp = 1`.
- PCI: columna `pci` de `ecomplexity_rama_ue_2023.csv`. Ante empates exactos se
  utiliza el código de rama ascendente como desempate reproducible.
- `pct_top5`: `100 * ue_top5 / ue_2023`. El denominador incluye todas las ramas
  con UE, incluso aquellas sin PCI; el PCI solo interviene en la selección del top.
- `den_top5`: `ue_top5 / area_km2`.
- `area_km2`: superficie calculada con la geometría del shapefile en una proyección
  Albers equivalente sobre GRS80. La geometría guardada conserva la proyección
  LCC original del shapefile.

En tres claves municipales los totales de UE del archivo del ICE difieren de la
consulta SAIC. Se utilizan los conteos del SAIC tanto para numerador como para
denominador. Las diferencias se conservan en `diferencias_totales_ue_fuentes.csv`.

## Regla de datos faltantes

Cada cálculo utiliza solo las variables que necesita. Los valores faltantes se
ignoran al calcular sobre los datos disponibles, sin exigir que otras variables
estén completas. No se aplican mínimos de observaciones municipales.

- Un dato faltante no invalida el cálculo de todo el municipio.
- Si no hay ningún dato utilizable para un indicador, el resultado es `NA`.
- Si no puede calcularse su denominador, o es cero, la razón es `NA`.
- Los ceros válidos se conservan. Por ejemplo, si hay personas con origen Q1 y
  ninguna sale de él, `sal_q1` es 0; si no hay personas con origen Q1, es `NA`.
- Las ramas sin PCI se excluyen únicamente del ordenamiento del top, no del
  total de unidades económicas.
- Si una clave no encuentra coincidencia en el shapefile, no se asigna a otro
  municipio automáticamente. La clave `03030` aparece en los datos individuales
  pero no en este shapefile; queda registrada en `claves_sin_geometria.csv`.
- El CSV escribe los faltantes como `NA`. En el shapefile se guardan como nulos
  numéricos y se verificó que al volver a leerlo siguen siendo valores faltantes.

## Reproducción y trazabilidad

Desde la carpeta del proyecto, ejecutar:

```r
Rscript scripts/01_construir_base_municipal.R
```

También se pueden indicar explícitamente la raíz del proyecto, la ruta de la
base IRE y una carpeta de salida alternativa:

```r
Rscript scripts/01_construir_base_municipal.R "/ruta/proyecto" "/ruta/base_IRE.rds" "/ruta/salida"
```

El script conserva las entradas y se detiene si ya existen archivos de salida
con el mismo nombre. Para una nueva ejecución utilice otra carpeta de salida.
La ruta predeterminada del RDS corresponde al archivo del proyecto utilizado
para las matrices previas y está escrita en el script. Puede sustituirse por
el segundo argumento si el archivo cambia de ubicación.

`fuentes_y_huellas.csv` registra rutas y huellas MD5 de las entradas.
`detalle_top5_ramas_2023.csv` permite identificar las ramas y UE seleccionadas en
cada municipio. `ramas_sin_pci_2023.csv` registra las ramas omitidas del ordenamiento.
El diccionario CSV detalla los campos y sus unidades.

La verificación comprobó que se conservan las claves, las geometrías, la
proyección y los nulos después de escribir y volver a leer el shapefile; también
que ascenso + descenso + permanencia = 100 %, que la probabilidad de salida
está entre 0 y 1 y que las UE del top no exceden el total municipal.


## Nueva columna: porcentaje en el top 5 nacional (2023)

`pct_top5n` = 100 × unidades económicas del municipio en las cinco ramas con mayor PCI nacional disponible / `ue_2023`. Se utiliza la misma lista fija de ramas para todos los municipios, ordenada por PCI descendente y código SCIAN ascendente en caso de empate. Las ramas son 5225, 5221, 4811, 5222 y 3341. El archivo `top5_nacional_ramas_2023.csv` identifica los nombres y PCI.

Un municipio con datos de UE y ninguna de estas ramas recibe 0. Cuando falta el total municipal o no es positivo, el resultado es NA. La columna conserva escala 0–100. El top se refiere al PCI estimado en el universo mexicano del archivo disponible, no a un índice mundial. `pct_top5` sigue siendo la medida basada en el top municipal. La marca `na_pct5n` de la tabla auxiliar indica si falta la nueva variable.

Esta actualización no vuelve a crear los paquetes ZIP que se hayan eliminado.


## Porcentaje en el top 10 nacional (2023)

`pct_top10n` = 100 × unidades económicas municipales en las diez ramas de mayor PCI nacional disponible / `ue_2023`. La lista fija es 5225, 5221, 4811, 5222, 3341, 5132, 6117, 4882, 3336 y 3342. Se ordenan por PCI descendente y código de rama ascendente como desempate. `top10_nacional_ramas_2023.csv` documenta sus nombres y PCI; `numerador_top10_nacional_2023.csv` conserva el numerador por municipio.

La escala es 0–100. Los municipios con datos económicos y sin esas ramas reciben 0; si no existe denominador positivo disponible, NA. La marca auxiliar es `na_pct10n`. Por construcción, `pct_top10n` es mayor o igual a `pct_top5n`. `pct_top5` conserva su definición de top municipal.


## Las cuatro medidas de concentracion en ramas complejas

| Columna | Referencia |
|---|---|
| `pct_top5` | Hasta cinco ramas presentes de mayor PCI disponible de cada municipio |
| `pct_top5n` | Las cinco ramas de mayor PCI nacional disponible; lista fija |
| `pct_top10` | Hasta diez ramas presentes de mayor PCI disponible de cada municipio |
| `pct_top10n` | Las diez ramas de mayor PCI nacional disponible; lista fija |

En todos los casos, el porcentaje es 100 × UE en las ramas seleccionadas / `ue_2023`. Los top municipales excluyen las ramas sin PCI del ordenamiento; si hay menos ramas que el numero indicado se usan las disponibles. Los empates de PCI se resuelven por codigo SCIAN ascendente. El detalle del top 10 municipal esta en `detalle_top10_ramas_2023.csv`, y su numerador en `numerador_top10_municipal_2023.csv`. La marca auxiliar de faltantes para `pct_top10` es `na_top10`.

Se conservan los ceros validos y se utiliza NA cuando no hay datos utilizables o denominador positivo. Las cuatro columnas estan en escala 0–100. Las relaciones verificadas son `pct_top5 <= pct_top10`, `pct_top5n <= pct_top10n`, `pct_top5n <= pct_top5` y `pct_top10n <= pct_top10`.
