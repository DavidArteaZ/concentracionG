"""
Descarga la población total municipal (2000, 2005, 2010, 2015, 2020)
desde la API del Banco de Indicadores de INEGI.

Uso:
    python poblacion_municipal_api.py catalogo_municipios.csv

El catálogo debe tener las columnas CVE_ENT y CVE_MUN (por ejemplo, el
Catálogo Único de Claves Geoestadísticas de INEGI, o un ITER filtrado).
Los encabezados se aceptan sin importar mayúsculas/minúsculas o espacios.
Salida: poblacion_municipal.csv (una fila por municipio, una columna por año).
"""
import csv
import sys
import time

import requests

TOKEN = "ebd80600-b237-4a96-953f-905cf86aa0e6"   # se obtiene gratis registrándote en INEGI
INDICADOR = "1002000001"       # Población total
ANIOS = ["2000", "2005", "2010", "2015", "2020"]
URL = ("https://www.inegi.org.mx/app/api/indicadores/desarrolladores/jsonxml/"
       "INDICATOR/{ind}/es/{geo}/false/BISE/2.0/{token}?type=json")


def clave_bise(ent, mun):
    # Área geográfica del BISE a nivel municipal: entidad(2) + municipio(3).
    # Ej. Guadalajara (14 039) -> 14039.
    return f"{int(ent):02d}{int(mun):03d}"


def poblacion(geo, sesion):
    try:
        r = sesion.get(URL.format(ind=INDICADOR, geo=geo, token=TOKEN), timeout=30)
    except requests.RequestException as e:
        print(f"\n[AVISO] {geo}: fallo de conexión: {e}", file=sys.stderr)
        return {}
    if r.status_code != 200:
        print(f"\n[AVISO] {geo}: HTTP {r.status_code}: {r.text[:200]}", file=sys.stderr)
        return {}
    try:
        obs = r.json()["Series"][0]["OBSERVATIONS"]
    except (ValueError, KeyError, IndexError):
        print(f"\n[AVISO] {geo}: respuesta sin datos: {r.text[:200]}", file=sys.stderr)
        return {}
    if not obs:
        print(f"\n[AVISO] {geo}: la serie no tiene observaciones", file=sys.stderr)
    return {o["TIME_PERIOD"][:4]: str(int(float(o["OBS_VALUE"]))) for o in obs if o["OBS_VALUE"]}


def leer_municipios(catalogo):
    with open(catalogo, encoding="utf-8-sig") as f:
        lector = csv.reader(f)
        encabezados = [h.strip().upper() for h in next(lector)]
        for col in ("CVE_ENT", "CVE_MUN"):
            if col not in encabezados:
                sys.exit(f"El catálogo no tiene la columna {col}. Encabezados: {encabezados}")
        i_ent, i_mun = encabezados.index("CVE_ENT"), encabezados.index("CVE_MUN")
        return {(int(row[i_ent]), int(row[i_mun])) for row in lector if row}


def main(catalogo):
    municipios = sorted(leer_municipios(catalogo))
    total, fallidos = len(municipios), 0

    sesion = requests.Session()
    with open("poblacion_municipal.csv", "w", newline="", encoding="utf-8") as out:
        w = csv.writer(out)
        w.writerow(["CVEGEO"] + ANIOS)
        for n, (ent, mun) in enumerate(municipios, 1):
            geo = clave_bise(ent, mun)
            datos = poblacion(geo, sesion)
            fallidos += not datos
            w.writerow([geo] + [datos.get(a, "") for a in ANIOS])
            print(f"\r{n}/{total} municipios ({n * 100 // total}%) - fallidos: {fallidos}",
                  end="", flush=True)
            time.sleep(0.2)  # para no saturar la API
    print(f"\nListo: {total - fallidos} con datos, {fallidos} sin datos.")


if __name__ == "__main__":
    main(sys.argv[1])
