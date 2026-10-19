"""Configuración del ICE V2 (por zona metropolitana, decisión D25).

Todas las rutas son relativas a la raíz del repositorio. El ICE V2 usa el mismo
algoritmo y los mismos parámetros que V1 (codigo/ice_v1/config.py); aquí solo
se definen las delimitaciones y las rutas propias de V2.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

V1_DIR = ROOT / "codigo" / "ice_v1"          # código de V1 (se carga por ruta, ver _v1.py)
RAW_V1 = ROOT / "data" / "raw" / "ice_v1"
CLEAN_V1 = ROOT / "data" / "clean" / "ice_v1"
RAW = ROOT / "data" / "raw" / "ice_v2"
CLEAN = ROOT / "data" / "clean" / "ice_v2"
OUT = ROOT / "outputs" / "ice_v2"
LOGS = OUT / "logs"

CONAPO = ROOT / "data" / "raw" / "pobproy_conapo.csv"
BASE_DML = ROOT / "data" / "clean" / "02_base_dml.csv"   # solo para diagnósticos (03)

# Delimitaciones (archivos entregados por David el 17/10/2026)
#  - 2010: Delimitación de las zonas metropolitanas de México 2010, Anexo
#    estadístico, Cuadro A1 (SEDESOL-CONAPO-INEGI). PDF; se lee con pdftotext
#    (poppler: `conda install -c conda-forge poppler`).
#  - 2020: Metrópolis de México 2020 (SEDATU-CONAPO-INEGI), tabla por municipio.
DELIM_PDF_2010 = RAW / "delimitacion_ZM_2010.pdf"
DELIM_XLSX_2020 = RAW / "delimitacion_ZM_2020.xlsx"

# Totales publicados que la lectura debe reproducir exactamente.
ESPERADO_2010 = {"zm": 59, "municipios": 367, "poblacion": 63_836_779}
ESPERADO_2020 = {"unidades": 92, "municipios": 421,
                 "por_tipo": {"Zona metropolitana": (48, 345),
                              "Metrópoli municipal": (22, 22),
                              "Zona conurbada": (22, 54)}}

# D25, regla de geografía 3: en 2020 cuentan las tres categorías.
TIPOS_2020 = ["Zona metropolitana", "Metrópoli municipal", "Zona conurbada"]

DELIMITACIONES = ["zm2010", "zm2020"]
ANIO_DELIM = {"zm2010": 2010, "zm2020": 2020}

# D25, regla de geografía 1. Municipios hijos (municipios_padre_hijo.csv) que NO
# están en la delimitación y cuyo padre SÍ está. Para cada uno se declara si el
# hijo existía en la geografía del censo de la delimitación:
#   False -> no existía (se creó después): hereda la unidad del padre.
#   True  -> sí existía y la delimitación lo dejó fuera: queda como unidad propia.
# Si aparece un caso no listado, 02_ice_zm.py se detiene.
HIJO_EXISTIA = {
    "zm2010": {
        "02007": False,  # San Felipe (de Mexicali), creado en 2020
        "23011": False,  # Puerto Morelos (de Benito Juárez), creado en 2015
        "24059": False,  # Villa de Pozos (de San Luis Potosí), creado en 2024
    },
    "zm2020": {
        "02006": False,  # San Quintín (de Ensenada): no está en el Censo 2020
        "02007": False,  # San Felipe (de Mexicali): no está en el Censo 2020
        "23009": True,   # Tulum (de Solidaridad), creado en 2008
        "23010": True,   # Bacalar (de Othón P. Blanco), creado en 2011
        "23011": True,   # Puerto Morelos (de Benito Juárez), creado en 2015
        "24059": False,  # Villa de Pozos, creado en 2024
        "25019": False,  # Eldorado (de Culiacán), creado en 2024
    },
}

# Años de población CONAPO que se exportan por unidad (cubre anio14 = 2003-2012).
ANIOS_POB = range(2000, 2024)

TOL_IDENTIDAD = 1e-8   # prueba de identidad contra ice_municipal.csv (V1)
