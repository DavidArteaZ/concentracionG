"""Módulo 03 — Por qué UE: censura del PBT y condicionamiento de la matriz.

Descriptivo (afirmación A2). No usa pruebas de normalidad.
1. Censura del PBT condicional a presencia (UE > 0), por año, sector y quintil
   de UE total del municipio.
2. ICE con PBT (celdas suprimidas = 0, como las trata ecomplexity) sobre el
   mismo núcleo que UE; comparación espectral y de degeneración.
3. ICE con PBT sin núcleo (todas las celdas), como en el notebook original.
Personal ocupado por rama no se calcula: la nota de INEGI aplica la
confidencialidad a todas las variables económicas.
Salidas: outputs/ice/tabla_ue_pbt.csv, 03_censura_pbt.csv
"""
import numpy as np
import pandas as pd

from . import config as C
from .utils import Log, asegurar_dirs, calcular_ice, matriz


def resumen(r, etiqueta, anio):
    d, m = r["diag"], r["mun"]
    core = m[m.en_nucleo]
    return {"anio": anio, "especificacion": etiqueta,
            "n_mun": d["n_mun_nucleo"], "n_ramas": d["n_ramas_nucleo"],
            "componentes": d["componentes"], "lambda2": d["lambda2"], "lambda3": d["lambda3"],
            "brecha_l2_l3": d["brecha_l2_l3"], "n_eig_mayor_0999": d["n_eig_mayor_0999"],
            "spearman_ice_diversidad": d["spearman_ice_diversidad"],
            "empates_pct": 100 * core.ice.round(8).duplicated(keep=False).mean(),
            "sd_ice_raw": core.ice_raw.std(), "max_abs_ice": core.ice.abs().max()}


def main():
    asegurar_dirs()
    log = Log("03_diagnostico_variables")
    largo = pd.read_csv(C.CLEAN / "saic_largo.csv.gz", dtype={"cve_mun": str, "codigo": str})
    rama = largo[largo.nivel == "rama"]
    ue = rama[rama.variable == "ue"].set_index(["anio", "cve_mun", "codigo"]).valor
    pbt = rama[rama.variable == "pbt"].set_index(["anio", "cve_mun", "codigo"])
    df = pbt[["estado_celda"]].join(ue.rename("ue")).reset_index()
    df = df[df.ue > 0]
    df["suprimida"] = df.estado_celda == "suprimida"
    df["sector"] = df.codigo.str[:2]
    tot = df.groupby(["anio", "cve_mun"]).ue.sum().rename("ue_mun").reset_index()
    tot["quintil_ue_mun"] = tot.groupby("anio").ue_mun.transform(
        lambda s: pd.qcut(s.rank(method="first"), 5, labels=[1, 2, 3, 4, 5]).astype(int))
    df = df.merge(tot, on=["anio", "cve_mun"])
    cens = []
    for by in ["anio", ["anio", "sector"], ["anio", "quintil_ue_mun"]]:
        t = df.groupby(by).suprimida.agg(["mean", "size"]).reset_index()
        t["desglose"] = by if isinstance(by, str) else by[1]
        cens.append(t)
    cens = pd.concat(cens)
    cens["pct_suprimida"] = 100 * cens["mean"]
    cens.drop(columns="mean").to_csv(C.OUT / "03_censura_pbt.csv", index=False)
    log("Censura del PBT | UE>0 (%), por año:")
    log(cens[cens.desglose == "anio"][["anio", "pct_suprimida", "size"]].round(1).to_string(index=False))
    q = cens[cens.desglose == "quintil_ue_mun"].pivot(index="quintil_ue_mun", columns="anio",
                                                        values="pct_suprimida").round(1)
    log("Por quintil de UE total del municipio (1 = más chicos):\n" + q.to_string())
    s = cens[cens.desglose == "sector"].pivot(index="sector", columns="anio",
                                               values="pct_suprimida").round(1)
    log("Por sector SCIAN (2 dígitos):\n" + s.to_string())

    filas = []
    for a in C.ANIOS:
        Xu = matriz(largo, a, var="ue")
        Xp = matriz(largo, a, var="pbt")  # suprimidas (NaN) -> 0 por fill_value; negativos -> 0
        ru = calcular_ice(Xu)
        fil, col = ru["nucleo"]
        filas.append(resumen(ru, "UE (núcleo)", a))
        Xp_core = Xp.reindex(index=fil, columns=col, fill_value=0)
        try:
            rp = calcular_ice(Xp_core, u_min=1e-9, d_min=1, p_min=1)
            filas.append(resumen(rp, "PBT (mismo núcleo)", a))
            # comparación en municipios comunes
            j = ru["mun"].set_index("cve_mun").ice.to_frame("ue").join(
                rp["mun"].set_index("cve_mun").ice.rename("pbt"), how="inner")
            filas[-1]["spearman_con_ue"] = j.ue.corr(j.pbt, method="spearman")
        except AssertionError as e:
            log(f"[{a}] PBT mismo núcleo: cálculo degenerado ({e})")
            filas.append({"anio": a, "especificacion": "PBT (mismo núcleo)", "error": str(e)})
        try:
            rf = calcular_ice(Xp, u_min=1e-9, d_min=1, p_min=1)
            filas.append(resumen(rf, "PBT (sin núcleo)", a))
        except AssertionError as e:
            log(f"[{a}] PBT sin núcleo: cálculo degenerado ({e})")
            filas.append({"anio": a, "especificacion": "PBT (sin núcleo)", "error": str(e)})
    tab = pd.DataFrame(filas)
    tab.to_csv(C.OUT / "tabla_ue_pbt.csv", index=False)
    pd.set_option("display.width", 200)
    log("\nComparación espectral y de degeneración:\n" + tab.round(4).to_string(index=False))
    log.close()


if __name__ == "__main__":
    main()
