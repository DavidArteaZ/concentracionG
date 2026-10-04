"""Configuración común del pipeline del ICE municipal.

Todas las rutas son relativas a la raíz del repositorio. Ver
docs/metodologia/metodologia_ice.md para la justificación de cada parámetro.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

RAW = ROOT / "data" / "raw" / "ice"
RAW_EMOVI = ROOT / "data" / "raw" / "entrevistado_2023.dta"
CLEAN = ROOT / "data" / "clean" / "ice"
OUT = ROOT / "outputs" / "ice"
LOGS = OUT / "logs"

SAIC_DIR = RAW / "saic_2003_2023"
SAIC_FILES = {
    2003: "2003_SAIC_Exporta_202698_0140579.csv",
    2008: "2008_SAIC_Exporta_202698_0928702.csv",
    2013: "2013_SAIC_Exporta_202698_0748203.csv",
    2018: "2018_SAIC_Exporta_202698_0546677.csv",
    2023: "2023_SAIC_Exporta_202698_037586.csv",
}
SAIC_TOTALES = RAW / "saic_totales_municipales.csv"
NUEVOS_2024 = RAW / "municipios_nuevos_2024.csv"
GDP = RAW / "gdp_perCapita_1990_2022.csv"
GADM_SHP = RAW / "gadm41_MEX_2" / "gadm41_MEX_2.shp"
INEGI_DBF = RAW / "00mun_2023" / "00mun.dbf"
CUCG = {2003: RAW / "CUCG_2003.csv", 2023: RAW / "CUCG_2023.csv"}
POBLACION = RAW / "poblacion_municipal.csv"

ANIOS = [2003, 2008, 2013, 2018, 2023]

# Filas de datos esperadas por archivo SAIC (incluye agregados nacionales/estatales).
# El notebook original contaba 3 filas más (línea vacía, nota al pie y línea final).
SAIC_FILAS_ESPERADAS = {2003: 369_650, 2008: 428_340, 2013: 466_912,
                        2018: 510_663, 2023: 544_999}

# Ramas ausentes por año respecto a la unión 2003-2023 (verificado 04/10/2026)
RAMAS_AUSENTES = {
    2003: {"1151", "1152", "1153", "4861", "5232", "5622", "5629"},
    2008: {"5622", "5629"},
    2013: {"4861", "5622", "5629"},
    2018: {"4861"},
    2023: {"4861"},
}

# Núcleo de estimación (decisión D3)
U_MIN = 30   # UE totales del municipio
D_MIN = 5    # ramas con UE > 0 en el municipio
P_MIN = 10   # municipios con UE > 0 en la rama
RCA_UMBRAL = 1.0

GRID_U = [10, 30, 100]
GRID_D = [3, 5, 10]
GRID_P = [5, 10, 20]

# Reglas de exclusión de ramas (decisión D4), solo robustez
def _r1(r):
    return r in {"5211", "5232", "2111"}

def _r2(r):
    return r.startswith("221")

def _r3(r):
    return r.startswith("21")

REGLAS_EXCLUSION = {
    "R1": _r1,
    "R2": _r2,
    "R3": _r3,
    "R4": lambda r: _r1(r) or _r2(r) or _r3(r),
}

SEED = 20261003
B_WILD = 9_999        # réplicas wild cluster bootstrap
B_PAIRS = 1_999       # réplicas bootstrap por estado (regla Rama vs. Clase)
CONLEY_KM = 100

TOL_ECOMPLEXITY = 0.9999
TOL_PROYECCION = 0.9999

ENTIDADES = {
    "Aguascalientes": "01", "Baja California": "02", "Baja California Sur": "03",
    "Campeche": "04", "Coahuila": "05", "Colima": "06", "Chiapas": "07",
    "Chihuahua": "08", "Distrito Federal": "09", "Durango": "10",
    "Guanajuato": "11", "Guerrero": "12", "Hidalgo": "13", "Jalisco": "14",
    "México": "15", "Michoacán": "16", "Morelos": "17", "Nayarit": "18",
    "Nuevo León": "19", "Oaxaca": "20", "Puebla": "21", "Querétaro": "22",
    "Quintana Roo": "23", "San Luis Potosí": "24", "Sinaloa": "25",
    "Sonora": "26", "Tabasco": "27", "Tamaulipas": "28", "Tlaxcala": "29",
    "Veracruz": "30", "Yucatán": "31", "Zacatecas": "32",
}
