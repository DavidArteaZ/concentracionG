"""
Asigna a poblacion_municipal.csv la población total 2015 de las proyecciones
de CONAPO (pobproy_conapo.csv), sumando hombres y mujeres por municipio.

Uso:
    python asignar_2015_conapo.py
"""
import csv
from collections import defaultdict

ANIO = "2015"
PROYECCIONES = "pobproy_conapo.csv"
DESTINO = "poblacion_municipal.csv"

# Suma HOMBRES + MUJERES de 2015 por municipio; la CLAVE de las entidades
# 1 a 9 viene sin el 0 inicial (1001 -> 01001).
pob_2015 = defaultdict(int)
with open(PROYECCIONES, encoding="utf-8-sig") as f:
    for row in csv.DictReader(f):
        if row["ANO"].strip() == ANIO:
            pob_2015[row["CLAVE"].strip().zfill(5)] += int(float(row["POB_TOTAL"]))

with open(DESTINO, encoding="utf-8") as f:
    filas = list(csv.DictReader(f))
    columnas = list(filas[0].keys())

sin_dato = []
for fila in filas:
    valor = pob_2015.get(fila["CVEGEO"])
    if valor is None:
        sin_dato.append(fila["CVEGEO"])
    else:
        fila[ANIO] = valor

with open(DESTINO, "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=columnas)
    w.writeheader()
    w.writerows(filas)

print(f"Asignados: {len(filas) - len(sin_dato)}/{len(filas)}. "
      f"Sin proyección {ANIO}: {sin_dato or 'ninguno'}")
