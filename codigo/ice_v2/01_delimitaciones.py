"""V2 — Módulo 01: lectura de las delimitaciones metropolitanas 2010 y 2020 (D25).

Uso (desde la raíz del repositorio):  python codigo/ice_v2/01_delimitaciones.py

Entradas: data/raw/ice_v2/delimitacion_ZM_2010.pdf (Cuadro A1)
          data/raw/ice_v2/delimitacion_ZM_2020.xlsx
Salidas:  data/clean/ice_v2/delimitacion_zm2010.csv, delimitacion_zm2020.csv
          (cve_mun, unidad, nom_unidad, tipo, ...)
La lectura se valida contra los totales publicados (config_v2.ESPERADO_*) y
contra la población municipal 2010 de data/raw/ice_v1/poblacion_municipal.csv.
"""
import re
import subprocess

import pandas as pd

import config_v2 as C2
from _v1 import cargar

_, U = cargar()

RX_ZM = re.compile(r"^\s*(\d+) (Zona metropolitana del? .*?)(?:\s{2,}(\d{1,3}(?: \d{3})+|\d{1,3}))?\s*$")
RX_POB = re.compile(r"\s*\d{1,3}(?: \d{3})+\s*")
# Fila municipal: núm., clave (4-5 dígitos), nombre (puede venir partido en dos
# renglones, uno antes y otro después de la fila), población 2010, MC y CF.
RX_MUN = re.compile(r"^ *(\d{1,3}) +(\d{4,5}) +(?:(\S.*?[A-Za-zÁÉÍÓÚáéíóúñÑüÜ.)]))?\s{2,}"
                    r"(\d{1,3}(?: \d{3})*)\s+([01])\s+([01])\s")


def leer_2010(log):
    txt = subprocess.run(["pdftotext", "-layout", str(C2.DELIM_PDF_2010), "-"],
                         capture_output=True, text=True, encoding="utf-8", check=True).stdout
    lineas = txt.split("\n")
    filas, enc, zm, pend = [], {}, None, None
    for k, l in enumerate(lineas):
        m = RX_ZM.match(l)
        if m:
            zm = int(m.group(1))
            enc[zm] = {"nom": m.group(2).strip(), "pob": m.group(3)}
            pend = zm if m.group(3) is None else None
            continue
        if pend and RX_POB.fullmatch(l):          # población de la ZM en otro renglón
            enc[pend]["pob"] = l.strip()
            continue
        if pend and l.strip() and not re.match(r"^ *\d", l):   # nombre de la ZM partido
            enc[pend]["nom"] += " " + l.strip()
            continue
        m = RX_MUN.match(l)
        if m:
            pend = None
            nom = m.group(3)
            if nom is None:
                nom = f"{lineas[k - 1].strip()} {lineas[k + 1].strip()}"
            filas.append({"cve_mun": m.group(2).zfill(5), "zm": zm, "nom_mun": nom.strip(),
                          "pob2010": int(m.group(4).replace(" ", "")),
                          "mc": int(m.group(5)), "cf": int(m.group(6))})
    d = pd.DataFrame(filas)
    h = pd.DataFrame(enc).T
    h["pob"] = h.pob.str.replace(" ", "").astype(int)
    h["nom"] = h.nom.str.replace("- ", "-", regex=False)

    # Validaciones contra los totales del propio cuadro y los publicados
    chk = d.groupby("zm").pob2010.sum().to_frame().join(h.pob)
    assert (chk.pob2010 == chk.pob).all(), chk[chk.pob2010 != chk.pob]
    e = C2.ESPERADO_2010
    assert d.zm.nunique() == e["zm"] and len(d) == e["municipios"], (d.zm.nunique(), len(d))
    assert d.pob2010.sum() == e["poblacion"], d.pob2010.sum()
    assert not d.cve_mun.duplicated().any()

    pob = pd.read_csv(C2.RAW_V1 / "poblacion_municipal.csv", dtype={"CVEGEO": str}).set_index("CVEGEO")
    assert d.cve_mun.isin(pob.index).all(), d.loc[~d.cve_mun.isin(pob.index)]
    dif = d[d.pob2010 != d.cve_mun.map(pob["2010"])]
    log(f"2010: {d.zm.nunique()} ZM, {len(d)} municipios, población {d.pob2010.sum():,}")
    log(f"2010: municipios cuya población del cuadro difiere de poblacion_municipal.csv: {len(dif)}")
    for r in dif.itertuples():
        log(f"      {r.cve_mun} {r.nom_mun}: cuadro {r.pob2010:,} vs. archivo {pob.loc[r.cve_mun, '2010']:,}")
    # La diferencia conocida (Nextlalpan, Tultepec, Tultitlán) suma cero entre
    # los tres y no cambia la pertenencia: los tres están en el Valle de México.
    if len(dif):
        log(f"      suma de diferencias: {(dif.pob2010 - dif.cve_mun.map(pob['2010'])).sum():,}; "
            f"ZM: {sorted(dif.zm.unique().tolist())}")

    d["unidad"] = "ZM10_" + d.zm.astype(str).str.zfill(2)
    d["nom_unidad"] = d.zm.map(h.nom)
    d["tipo"] = "Zona metropolitana"
    return d[["cve_mun", "unidad", "nom_unidad", "tipo", "nom_mun", "pob2010", "mc", "cf"]]


def leer_2020(log):
    z = pd.read_excel(C2.DELIM_XLSX_2020, dtype=str)
    assert {"CVEGEO", "CVE_ZONA", "NOM_ZM", "TIPOMET", "NOMGEO"} <= set(z.columns), z.columns
    assert z.CVEGEO.str.fullmatch(r"\d{5}").all() and not z.CVEGEO.duplicated().any()
    e = C2.ESPERADO_2020
    assert z.CVE_ZONA.nunique() == e["unidades"] and len(z) == e["municipios"]
    t = z.groupby("TIPOMET").agg(u=("CVE_ZONA", "nunique"), m=("CVEGEO", "size"))
    for tipo, (u, m) in e["por_tipo"].items():
        assert (t.loc[tipo, "u"], t.loc[tipo, "m"]) == (u, m), (tipo, t.loc[tipo].tolist())
    assert (z.groupby("CVE_ZONA").TIPOMET.nunique() == 1).all()
    z = z[z.TIPOMET.isin(C2.TIPOS_2020)]
    pob = pd.read_csv(C2.RAW_V1 / "poblacion_municipal.csv", dtype={"CVEGEO": str}).set_index("CVEGEO")
    assert z.CVEGEO.isin(pob.index).all()
    log(f"2020: {z.CVE_ZONA.nunique()} unidades, {len(z)} municipios; por tipo:\n" + t.to_string())
    out = pd.DataFrame({"cve_mun": z.CVEGEO, "unidad": "ZM20_" + z.CVE_ZONA, "nom_unidad": z.NOM_ZM,
                        "tipo": z.TIPOMET, "nom_mun": z.NOMGEO})
    return out


def main():
    for d in (C2.CLEAN, C2.OUT, C2.LOGS):
        d.mkdir(parents=True, exist_ok=True)
    U.C.LOGS = C2.LOGS            # la bitácora de V2 va a outputs/ice_v2/logs
    log = U.Log("v2_01_delimitaciones")
    d10, d20 = leer_2010(log), leer_2020(log)
    d10.to_csv(C2.CLEAN / "delimitacion_zm2010.csv", index=False)
    d20.to_csv(C2.CLEAN / "delimitacion_zm2020.csv", index=False)
    s10, s20 = set(d10.cve_mun), set(d20.cve_mun)
    log(f"Municipios en 2010 y no en 2020: {len(s10 - s20)}; en 2020 y no en 2010: {len(s20 - s10)}")
    m = d10.merge(d20, on="cve_mun", suffixes=("_10", "_20"))
    log(f"ZM 2010 repartidas en más de una unidad 2020: "
        f"{(m.groupby('unidad_10').unidad_20.nunique() > 1).sum()}; "
        f"unidades 2020 que juntan más de una ZM 2010: "
        f"{(m.groupby('unidad_20').unidad_10.nunique() > 1).sum()}")
    log.close()


if __name__ == "__main__":
    main()
