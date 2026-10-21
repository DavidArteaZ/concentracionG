# Copia compatible con GeoDa: faltantes de todas las columnas

Abra `data/clean/municipios_mov_ice_2023_geoda.geojson` en GeoDa mediante **File > Open**.
Es la misma base municipal, con los mismos campos, valores, ceros y 2,478 municipios.
Conserva las geometrías y la proyección originales. Esta copia no necesita unir
la tabla auxiliar ni recodificar columnas manualmente.

## Qué se corrigió

El lector de columnas decimales de GeoDa 1.22.1 comprueba si un campo está
establecido (`IsFieldSet`), pero no distingue siempre un valor nulo explícito.
Así, un faltante numérico del DBF puede entrar como cero. En el GeoJSON compatible,
las propiedades faltantes se omiten por municipio: no se sustituyen por valores
numéricos. El lector las identifica como campos no establecidos y GeoDa puede
marcarlas como *undefined*.

La regla se aplicó a todas las columnas. Los atributos con dato conservan su valor
y los ceros reales permanecen como cero. El diccionario de la base anterior sigue
siendo válido. No se recalculó ningún indicador.

Por ejemplo, para `asc_pct` deben reconocerse 1,822 municipios como *undefined*,
228 como cero válido y 428 con valores positivos. Los cuantiles se calculan sobre
los 656 valores disponibles. Puede seguir habiendo categorías vacías por empates:
los ceros válidos representan el 34.8 % de los valores disponibles de esa variable.

## Verificación

Se comprobó cada campo con la biblioteca GDAL 3.13.1 incluida en la instalación
local de GeoDa y con la misma prueba `IsFieldSet` utilizada por su lector.
`verificacion_lector_geoda.json` conserva los resultados por columna. También se
verificó en R que las claves, los valores, los faltantes, las geometrías y la
proyección coinciden con la base original. No se controló la interfaz de GeoDa.

## Próximas generaciones de la base

`scripts/01_construir_base_municipal.R` incorpora ahora esta exportación mediante
`scripts/exportar_geojson_geoda.R`. Al generar una nueva base, ambos scripts deben
estar juntos en `scripts`. La salida incluye el shapefile y el GeoJSON compatible;
para explorar en esta versión de GeoDa, utilice el GeoJSON.

El shapefile anterior se conserva como otra salida de la base. Su lectura de
faltantes depende del software; no debe confundirse con la copia compatible con
GeoDa. El ZIP anterior contiene el shapefile; el nuevo ZIP terminado en `_geoda`
contiene el GeoJSON compatible.

Referencias técnicas: código oficial de GeoDa, `DataViewer/OGRColumn.cpp`,
constructor `OGRColumnDouble(OGRLayerProxy*, int)`; documentación de GDAL,
«RFC 67: Null values in OGR»:
https://gdal.org/en/stable/development/rfc/rfc67_nullfieldvalues.html


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
