"""
Rellena las celdas vacías de poblacion_municipal.csv con la población total
de las proyecciones de CONAPO (pobproy_conapo.csv), sumando hombres y mujeres.
Solo toca celdas vacías; los datos de INEGI existentes se conservan.

Uso:
    python rellenar_vacios_conapo.py
"""
import csv
from collections import defaultdict

PROYECCIONES = "pobproy_conapo.csv"
DESTINO = "poblacion_municipal.csv"

with open(DESTINO, encoding="utf-8") as f:
    filas = list(csv.DictReader(f))
    columnas = list(filas[0].keys())
anios = set(columnas[1:])

# (CVEGEO, año) -> HOMBRES + MUJERES; la CLAVE de las entidades 1 a 9
# viene sin el 0 inicial (1001 -> 01001).
conapo = defaultdict(int)
with open(PROYECCIONES, encoding="utf-8-sig") as f:
    for row in csv.DictReader(f):
        anio = row["ANO"].strip()
        if anio in anios:
            conapo[row["CLAVE"].strip().zfill(5), anio] += int(float(row["POB_TOTAL"]))

rellenadas, sin_correspondencia = [], []
for fila in filas:
    for anio in columnas[1:]:
        if fila[anio].strip():
            continue
        clave = (fila["CVEGEO"], anio)
        if clave in conapo:
            fila[anio] = conapo[clave]
            rellenadas.append(clave)
        else:
            sin_correspondencia.append(clave)

with open(DESTINO, "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=columnas)
    w.writeheader()
    w.writerows(filas)

print(f"Celdas rellenadas: {len(rellenadas)} -> {rellenadas}")
print(f"Celdas vacías sin correspondencia en CONAPO: {sin_correspondencia or 'ninguna'}")
