"""Módulo 08 (parte 1) — Base municipio x rama con las variables de ecomplexity.

Reproduce las variables del paquete ecomplexity para el ICE final (el mismo del
Módulo 07: UE, rama, núcleo U_MIN/D_MIN/P_MIN, PCI espectral y proyección):
  año, clave_municipio, nom_municipio, rama, diversity, ubiquity, mcp, eci, pci,
  density, coi, cog, rca
Definiciones (iguales a ecomplexity 0.5.3, salvo la proyección):
  - rca, mcp: para todos los municipios, sobre las ramas del núcleo, con el
    denominador nacional del núcleo (como en el Módulo 02).
  - ubiquity: número de municipios del núcleo con mcp = 1 (k_p del núcleo).
  - diversity: número de ramas del núcleo con mcp = 1 del municipio.
  - eci, pci: los del Módulo 02 (estandarizados con media y d.e. del ICE del núcleo).
  - proximidad: phi_pp' = min(P(p|p'), P(p'|p)) con la M del núcleo.
  - density_cp = sum_p' mcp_cp' phi_pp' / sum_p' phi_pp'.
  - coi_c = sum_p (1 - mcp_cp) density_cp pci_raw_p, estandarizado con media y
    d.e. del núcleo; cog como en ecomplexity, dividido entre la d.e. del ICE del núcleo.
Verificación: en el núcleo, density, coi y cog deben coincidir con ecomplexity
(corr >= 0.9999).
Salidas: data/clean/ice/ecomplexity_rama_ue_<año>.csv.gz (uno por año), proximidad_ramas.csv.gz,
         catalogo_ramas.csv
"""
import warnings

import numpy as np
import pandas as pd
import shapefile

from . import config as C
from .utils import Log, asegurar_dirs, calcular_ice, leer_saic, matriz, rca_binaria


def nombres_municipio():
    r = shapefile.Reader(str(C.INEGI_DBF).replace(".dbf", ".shp"), encoding="latin-1")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        n = pd.DataFrame([x.as_dict() for x in r.records()])
    nom = n.set_index("CVEGEO").NOMGEO
    c03 = pd.read_csv(C.CUCG[2003], dtype=str, usecols=["CVE_ENT", "CVE_MUN", "NOM_MUN"])
    c03 = c03.drop_duplicates(["CVE_ENT", "CVE_MUN"])
    nom03 = pd.Series(c03.NOM_MUN.values, index=c03.CVE_ENT + c03.CVE_MUN)
    return nom.combine_first(nom03)


def variables_anio(X, r):
    fil, col = r["nucleo"]
    M = r["M"]
    kp = M.sum(0)
    phi = M.T @ M / kp[None, :]
    np.fill_diagonal(phi, 0)
    phi = np.minimum(phi, phi.T)
    Xall = X.loc[:, col].to_numpy(float)
    den = X.loc[fil, col].to_numpy(float).sum(0) / X.loc[fil, col].to_numpy(float).sum()
    rca, Mall, _ = rca_binaria(Xall, den)
    dens = Mall @ (phi.T / phi.sum(1)[None, :])
    m = r["mun"].set_index("cve_mun").loc[X.index]
    p = r["prod"].set_index("rama").loc[col]
    en = m.en_nucleo.to_numpy()
    mu, sd = np.nanmean(m.ice_raw[en]), np.nanstd(m.ice_raw[en])
    pci_raw = p.pci_raw.to_numpy()
    coi = ((dens * (1 - Mall)) * pci_raw).sum(1)
    cog = (1 - Mall) * ((1 - Mall) @ (phi * (pci_raw / phi.sum(1))[:, None]))
    coi = (coi - coi[en].mean()) / coi[en].std()
    cog = cog / sd
    n, k = Mall.shape
    out = pd.DataFrame({
        "clave_municipio": np.repeat(X.index.to_numpy(), k),
        "rama": np.tile(np.asarray(col), n),
        "diversity": np.repeat(Mall.sum(1), k).astype(int),
        "ubiquity": np.tile(kp, n).astype(int),
        "mcp": Mall.ravel().astype(int),
        "eci": np.repeat(m.ice.to_numpy(), k),
        "pci": np.tile(p.pci.to_numpy(), n),
        "density": dens.ravel(), "coi": np.repeat(coi, k), "cog": cog.ravel(),
        "rca": rca.ravel(), "en_nucleo": np.repeat(en, k)})
    prox = pd.DataFrame(phi, index=pd.Index(col, name="rama_1"),
                        columns=pd.Index(col, name="rama_2"))
    return out, prox, (fil, col, M)


def validar(X, fil, col, out, log, anio):
    from ecomplexity import ecomplexity
    sub = X.loc[fil, col].rename_axis(index="loc", columns="prod").stack().rename("val").reset_index()
    sub.columns = ["loc", "prod", "val"]
    sub["time"] = 0
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        e = ecomplexity(sub, {"time": "time", "loc": "loc", "prod": "prod", "val": "val"},
                        check_logsupermodularity=False, verbose=False)
    e = e.rename(columns={"loc": "clave_municipio", "prod": "rama"})
    j = out[out.en_nucleo].merge(e, on=["clave_municipio", "rama"], suffixes=("", "_pkg"))
    res = {}
    for v in ["mcp", "eci", "pci", "density", "cog"]:
        res[v] = np.corrcoef(j[v], j[f"{v}_pkg"])[0, 1]
    jj = j.drop_duplicates("clave_municipio")
    res["coi"] = np.corrcoef(jj.coi, jj.coi_pkg)[0, 1]
    log(f"[{anio}] corr con ecomplexity en el núcleo: " +
        ", ".join(f"{k} {v:.6f}" for k, v in res.items()))
    for k, v in res.items():
        assert v >= C.TOL_ECOMPLEXITY, f"{anio} {k}: {v}"


def main():
    asegurar_dirs()
    log = Log("08_export_ecomplexity")
    largo = pd.read_csv(C.CLEAN / "saic_largo.csv.gz", dtype={"cve_mun": str, "codigo": str})
    ice07 = pd.read_csv(C.CLEAN / "ice_para_dml.csv", dtype={"cve_mun": str})
    nom = nombres_municipio()
    partes, proxs = [], []
    for a in C.ANIOS:
        X = matriz(largo, a)
        X = X.loc[(X.sum(1) > 0).to_numpy(), (X.sum(0) > 0).to_numpy()]
        r = calcular_ice(X)
        out, prox, (fil, col, _) = variables_anio(X, r)
        validar(X, fil, col, out, log, a)
        chk = out.drop_duplicates("clave_municipio").merge(
            ice07[ice07.anio == a][["cve_mun", "ice"]], left_on="clave_municipio", right_on="cve_mun")
        assert np.allclose(chk.eci, chk.ice), "eci distinto del ICE del Módulo 07"
        out.insert(0, "año", a)
        partes.append(out)
        pl = prox.stack().rename("proximidad").reset_index()
        pl.columns = ["rama_1", "rama_2", "proximidad"]
        pl.insert(0, "año", a)
        proxs.append(pl[pl.rama_1 < pl.rama_2])
        log(f"[{a}] {out.clave_municipio.nunique()} municipios x {len(col)} ramas = {len(out):,} filas")
    df = pd.concat(partes, ignore_index=True)
    df["nom_municipio"] = df.clave_municipio.map(nom)
    log(f"Municipios sin nombre: {df.loc[df.nom_municipio.isna(), 'clave_municipio'].unique()}")
    cols = ["año", "clave_municipio", "nom_municipio", "rama", "diversity", "ubiquity", "mcp",
            "eci", "pci", "density", "coi", "cog", "rca", "en_nucleo"]
    # Un archivo por año (el archivo único pesaría ~64 MB comprimido); para unirlos:
    # pd.concat(pd.read_csv(f) for f in sorted(C.CLEAN.glob("ecomplexity_rama_ue_*.csv.gz")))
    for a, g in df[cols].groupby("año"):
        g.to_csv(C.CLEAN / f"ecomplexity_rama_ue_{a}.csv.gz", index=False, float_format="%.6g")
    pd.concat(proxs).to_csv(C.CLEAN / "proximidad_ramas.csv.gz", index=False, float_format="%.6g")
    # Catálogo de nombres de rama (de los propios archivos SAIC; prioridad al más reciente)
    noms = []
    for a in sorted(C.SAIC_FILES, reverse=True):
        t, _ = leer_saic(C.SAIC_DIR / C.SAIC_FILES[a])
        t = t.iloc[:, 3]
        t = t[t.str.match(r"^Rama \d{4} ")].drop_duplicates()
        noms.append(pd.DataFrame({"rama": t.str[5:9], "nombre_rama": t.str[10:].str.strip()}))
    noms = pd.concat(noms).drop_duplicates("rama")
    noms.to_csv(C.CLEAN / "catalogo_ramas.csv", index=False)
    log(f"catalogo_ramas.csv: {len(noms)} ramas")
    log(f"Guardado ecomplexity_rama_ue_<año>.csv.gz (5 archivos): {len(df):,} filas; proximidad_ramas.csv.gz")
    log.close()


if __name__ == "__main__":
    main()
