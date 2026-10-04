"""Módulo 05 — Tabla puente GADM <-> INEGI y tabla padre-hijo de municipios.

1. Cruce por nombre (principal): entidad por diccionario explícito NAME_1 ->
   CVE_ENT (nunca el índice de GADM); nombre normalizado exacto y, si no,
   prefijo único (GADM trunca a 32 caracteres).
2. Verificación espacial por población: cada localidad activa de CUCG_2023
   (WGS84) se asigna al polígono GADM que la contiene; se calculan
   share_pob_inegi (proporción de la población del municipio INEGI dentro del
   polígono GADM) y share_pob_gadm (proporción de la población del polígono
   que pertenece al municipio INEGI).
3. Correcciones manuales en data/raw/ice/crosswalk_overrides.csv (si existe).
4. Tabla padre-hijo: municipios de CUCG_2023 ausentes en CUCG_2003, más los
   creados en 2024; padre = municipio de 2003 con más población de las
   localidades emparejadas (coordenadas a <= 100 m y mismo nombre).
5. Centroide poblacional de cada municipio (para errores de Conley).
Salidas: data/clean/ice/crosswalk_gadm_inegi.csv, municipios_padre_hijo.csv,
         centroides_municipales.csv; outputs/ice/crosswalk_revision.csv
"""
import numpy as np
import pandas as pd
import shapefile
from matplotlib.path import Path
from scipy.spatial import cKDTree

from . import config as C
from .utils import Log, asegurar_dirs, norm_nombre


def leer_localidades(anio, solo_activas=True):
    c = pd.read_csv(C.CUCG[anio], dtype=str,
                    usecols=["CVE_ENT", "CVE_MUN", "NOM_LOC", "Estatus", "LAT_DECIMAL",
                             "LON_DECIMAL", "POB_TOTAL"])
    if solo_activas:
        c = c[c.Estatus.isna()]
    c["cve_mun"] = c.CVE_ENT + c.CVE_MUN
    c["lat"] = pd.to_numeric(c.LAT_DECIMAL, errors="coerce")
    c["lon"] = pd.to_numeric(c.LON_DECIMAL, errors="coerce")
    c["pob"] = pd.to_numeric(c.POB_TOTAL, errors="coerce").fillna(0)
    c["nom"] = c.NOM_LOC.map(norm_nombre)
    return c.dropna(subset=["lat", "lon"]).reset_index(drop=True)


def punto_en_poligono(shapes, lon, lat):
    """Índice del polígono que contiene cada punto (-1 si ninguno). Regla par-impar
    entre partes (agujeros y partes disjuntas)."""
    asig = np.full(len(lon), -1)
    pts = np.c_[lon, lat]
    for k, s in enumerate(shapes):
        x0, y0, x1, y1 = s.bbox
        cand = np.where((lon >= x0) & (lon <= x1) & (lat >= y0) & (lat <= y1) & (asig < 0))[0]
        if len(cand) == 0:
            continue
        dentro = np.zeros(len(cand), bool)
        partes = list(s.parts) + [len(s.points)]
        P = np.asarray(s.points)
        for a, b in zip(partes[:-1], partes[1:]):
            dentro ^= Path(P[a:b]).contains_points(pts[cand])
        asig[cand[dentro]] = k
    return asig


def main():
    asegurar_dirs()
    log = Log("05_crosswalk_gadm_inegi")
    r = shapefile.Reader(str(C.GADM_SHP), encoding="utf-8")
    g = pd.DataFrame([rec.as_dict() for rec in r.records()])
    shapes = r.shapes()
    gdp = pd.read_csv(C.GDP, usecols=["GID_2", "NAME_2"])
    assert set(g.GID_2) == set(gdp.GID_2) and len(g) == 2457, "GID_2 de PIB y GADM no coinciden"
    log(f"GADM: {len(g)} polígonos; GID_2 coinciden 1:1 con el CSV de PIB")
    inegi = pd.DataFrame([rec.as_dict() for rec in shapefile.Reader(
        str(C.INEGI_DBF).replace(".dbf", ".shp"), encoding="latin-1").records()])
    inegi["cve_mun"] = inegi.CVEGEO
    log(f"INEGI 2023: {len(inegi)} municipios")

    g["cve_ent"] = g.NAME_1.map(C.ENTIDADES)
    assert g.cve_ent.notna().all(), g.loc[g.cve_ent.isna(), "NAME_1"].unique()
    g["n"] = g.NAME_2.map(norm_nombre)
    inegi["n"] = inegi.NOMGEO.map(norm_nombre)

    # 1. Nombre exacto y prefijo único
    ex = g.merge(inegi[["CVE_ENT", "n", "cve_mun"]], left_on=["cve_ent", "n"],
                 right_on=["CVE_ENT", "n"], how="left")
    assert not ex.GID_2.duplicated().any(), "nombres duplicados dentro de una entidad"
    g["cve_nombre"] = ex.cve_mun.values
    g["metodo"] = np.where(g.cve_nombre.notna(), "exacto", "")
    usados = set(g.cve_nombre.dropna())
    for i in g.index[g.cve_nombre.isna()]:
        cand = inegi[(inegi.CVE_ENT == g.at[i, "cve_ent"]) & ~inegi.cve_mun.isin(usados)
                     & inegi.n.str.startswith(g.at[i, "n"])]
        if len(cand) == 1:
            g.at[i, "cve_nombre"] = cand.cve_mun.iat[0]
            g.at[i, "metodo"] = "prefijo"
            usados.add(cand.cve_mun.iat[0])
    log(f"Cruce por nombre: exacto {(g.metodo == 'exacto').sum()}, prefijo "
        f"{(g.metodo == 'prefijo').sum()}, sin resolver {(g.metodo == '').sum()}")

    # 2. Verificación espacial con población de localidades
    loc = leer_localidades(2023)
    loc["gadm"] = punto_en_poligono(shapes, loc.lon.to_numpy(), loc.lat.to_numpy())
    sin = (loc.gadm < 0)
    log(f"Localidades activas: {len(loc):,}; fuera de todo polígono GADM: {sin.sum():,} "
        f"({100 * loc.pob[sin].sum() / loc.pob.sum():.3f}% de la población)")
    loc["w"] = loc.pob + 1  # +1 para que municipios sin población registrada pesen
    loc = loc[~sin]
    loc["GID_2"] = g.GID_2.to_numpy()[loc.gadm]
    t = loc.groupby(["GID_2", "cve_mun"]).w.sum().rename("w").reset_index()
    t["share_pob_gadm"] = t.w / t.groupby("GID_2").w.transform("sum")
    t["share_pob_inegi"] = t.w / t.groupby("cve_mun").w.transform("sum")
    dom = t.sort_values("share_pob_gadm", ascending=False).drop_duplicates("GID_2")
    dom = dom.rename(columns={"cve_mun": "cve_espacial"})[["GID_2", "cve_espacial",
                                                            "share_pob_gadm", "share_pob_inegi"]]
    g = g.merge(dom, on="GID_2", how="left")
    # hijos completos dentro del polígono (para 1:n)
    hijos = t[(t.share_pob_inegi >= 0.5)].groupby("GID_2").cve_mun.agg(list)
    g["inegi_contenidos"] = g.GID_2.map(hijos)
    partidos = t[t.share_pob_inegi < 0.9].cve_mun.unique()

    # 3. Asignación final
    g["cve_mun"] = g.cve_nombre
    m_esp = g.cve_mun.isna() & (g.share_pob_gadm >= 0.5)
    g.loc[m_esp, "cve_mun"] = g.loc[m_esp, "cve_espacial"]
    g.loc[m_esp, "metodo"] = "espacial"
    ov_path = C.RAW / "crosswalk_overrides.csv"
    if ov_path.exists():
        ov = pd.read_csv(ov_path, dtype=str)
        for _, o in ov.iterrows():
            g.loc[g.GID_2 == o.GID_2, ["cve_mun", "metodo"]] = [o.cve_mun, "override"]
        log(f"Overrides aplicados: {len(ov)}")
    # métricas de la asignación final
    tt = t.set_index(["GID_2", "cve_mun"])
    idx = list(zip(g.GID_2, g.cve_mun.fillna("")))
    g["share_pob_gadm_final"] = [tt.share_pob_gadm.get(k, 0.0) for k in idx]
    g["share_pob_inegi_final"] = [tt.share_pob_inegi.get(k, 0.0) for k in idx]
    n_hijos = g.inegi_contenidos.map(lambda x: len(x) if isinstance(x, list) else 0)
    g["tipo_relacion"] = np.select(
        [g.cve_mun.isna(),
         n_hijos >= 2,
         g.cve_mun.isin(partidos) & (g.share_pob_inegi_final < 0.9),
         (g.share_pob_gadm_final >= 0.9) & (g.share_pob_inegi_final >= 0.9)],
        ["sin_resolver", "1:n", "n:1", "1:1"], "ambiguo")
    g["discrepancia_nombre_espacial"] = g.cve_nombre.notna() & (g.cve_nombre != g.cve_espacial)
    dup = g.cve_mun.dropna().duplicated(keep=False)
    log("Tipo de relación: " + g.tipo_relacion.value_counts().to_string().replace("\n", " | "))
    log(f"Discrepancias nombre vs. espacial: {g.discrepancia_nombre_espacial.sum()}; "
        f"claves INEGI asignadas a más de un GADM: {dup.sum()}")
    no_res = (g.tipo_relacion == "sin_resolver").mean()
    assert no_res <= 0.02, f"{100 * no_res:.1f}% sin resolver: revisar antes de seguir"
    inegi_sin = sorted(set(inegi.cve_mun) - set(g.cve_mun.dropna()))
    log(f"Municipios INEGI 2023 sin polígono GADM asignado: {len(inegi_sin)}")

    rev = g[(g.metodo != "exacto") | (g.tipo_relacion != "1:1") | g.discrepancia_nombre_espacial | dup]
    cols = ["GID_2", "NAME_1", "NAME_2", "cve_nombre", "cve_espacial", "cve_mun", "metodo",
            "tipo_relacion", "share_pob_gadm_final", "share_pob_inegi_final", "inegi_contenidos",
            "discrepancia_nombre_espacial"]
    rev = rev[cols].merge(inegi[["cve_mun", "NOMGEO"]], on="cve_mun", how="left")
    rev.to_csv(C.OUT / "crosswalk_revision.csv", index=False)
    log(f"Casos para revisión manual: {len(rev)} (outputs/ice/crosswalk_revision.csv)")
    log(rev[rev.metodo != "exacto"][["NAME_2", "cve_mun", "NOMGEO", "metodo", "tipo_relacion"]]
        .to_string(index=False))
    out = g[["GID_2", "NAME_1", "NAME_2", "cve_mun", "metodo", "tipo_relacion",
             "share_pob_gadm_final", "share_pob_inegi_final", "discrepancia_nombre_espacial"]]
    out = out.rename(columns={"share_pob_gadm_final": "share_pob_gadm",
                              "share_pob_inegi_final": "share_pob_inegi"})
    out.to_csv(C.CLEAN / "crosswalk_gadm_inegi.csv", index=False)

    # 4. Tabla padre-hijo
    l03 = leer_localidades(2003, solo_activas=False)
    l23 = leer_localidades(2023, solo_activas=False)
    nuevos = sorted(set(l23.cve_mun) - set(l03.cve_mun))
    log(f"\nMunicipios en CUCG_2023 ausentes en CUCG_2003: {len(nuevos)}")
    km = 111.32
    def xy(d):
        return np.c_[d.lat * km, d.lon * km * np.cos(np.deg2rad(d.lat))]
    arbol = cKDTree(xy(l03))
    filas = []
    for cm in nuevos:
        h = l23[l23.cve_mun == cm]
        dist, j = arbol.query(xy(h), k=5, distance_upper_bound=0.1)
        emp = []
        for ii in range(len(h)):
            for dd, jj in zip(dist[ii], j[ii]):
                if np.isfinite(dd) and l03.nom.iat[jj] == h.nom.iat[ii]:
                    emp.append((l03.cve_mun.iat[jj], h.pob.iat[ii] + 1))
                    break
        if not emp:
            filas.append({"cve_mun_hijo": cm, "cve_mun_padre": None, "share_pob_padre": np.nan,
                          "localidades_emparejadas": 0, "localidades_hijo": len(h)})
            continue
        e = pd.DataFrame(emp, columns=["padre", "w"]).groupby("padre").w.sum()
        filas.append({"cve_mun_hijo": cm, "cve_mun_padre": e.idxmax(),
                      "share_pob_padre": e.max() / e.sum(), "otros_padres": " ".join(
                          p for p in e.index if p != e.idxmax()),
                      "localidades_emparejadas": len(emp), "localidades_hijo": len(h)})
    ph = pd.DataFrame(filas)
    ph["fuente"] = "CUCG 2003 vs 2023 (localidades a <=100 m con mismo nombre)"
    n24 = pd.read_csv(C.NUEVOS_2024, dtype=str)
    ph = pd.concat([ph, pd.DataFrame({"cve_mun_hijo": n24.cve_mun_nuevo,
                                      "cve_mun_padre": n24.cve_mun_origen,
                                      "fuente": "decreto (municipios_nuevos_2024.csv)"})])
    nom = inegi.set_index("cve_mun").NOMGEO
    ph["nombre_hijo"], ph["nombre_padre"] = ph.cve_mun_hijo.map(nom), ph.cve_mun_padre.map(nom)
    ph.to_csv(C.CLEAN / "municipios_padre_hijo.csv", index=False)
    log(ph[["cve_mun_hijo", "nombre_hijo", "cve_mun_padre", "nombre_padre", "share_pob_padre",
            "otros_padres", "localidades_emparejadas", "localidades_hijo"]].round(3).to_string(index=False))

    # 5. Centroide poblacional
    a = leer_localidades(2023)
    a["w"] = a.pob + 1
    cen = a.groupby("cve_mun").apply(lambda d: pd.Series({
        "lat": np.average(d.lat, weights=d.w), "lon": np.average(d.lon, weights=d.w)}),
        include_groups=False).reset_index()
    cen.to_csv(C.CLEAN / "centroides_municipales.csv", index=False)
    log(f"\nCentroides poblacionales: {len(cen)} municipios")
    log.close()


if __name__ == "__main__":
    main()
