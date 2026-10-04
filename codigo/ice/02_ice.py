"""Módulo 02 — Cálculo del ICE (núcleo + PCI espectral + proyección).

Especificación base: UE, rama, M_cp = RCA >= 1, un cálculo por año, núcleo
U_MIN/D_MIN/P_MIN (config). Variante 'ramas_comunes': solo ramas presentes en
los cinco años. Validación contra el paquete ecomplexity en el núcleo.
Salidas: data/clean/ice/ice_municipal.csv, pci_rama.csv;
         outputs/ice/diagnosticos_espectrales.csv, 02_exclusiones_nucleo_estado.csv
"""
import warnings

import numpy as np
import pandas as pd

from . import config as C
from .utils import Log, asegurar_dirs, calcular_ice, matriz, poblacion_censal


def validar_ecomplexity(X, fil, col, ice_core, log):
    from ecomplexity import ecomplexity
    sub = X.loc[fil, col].stack().rename("val").reset_index()
    sub.columns = ["loc", "prod", "val"]
    sub["time"] = 0
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        res = ecomplexity(sub, {"time": "time", "loc": "loc", "prod": "prod", "val": "val"},
                          check_logsupermodularity=False, verbose=False)
    e = res.drop_duplicates("loc").set_index("loc").eci.reindex(ice_core.index)
    return np.corrcoef(e.to_numpy(float), ice_core.to_numpy(float))[0, 1]


def main():
    asegurar_dirs()
    log = Log("02_ice")
    largo = pd.read_csv(C.CLEAN / "saic_largo.csv.gz", dtype={"cve_mun": str, "codigo": str})
    pob = poblacion_censal()
    log(f"Parámetros del núcleo: U_MIN={C.U_MIN}, D_MIN={C.D_MIN}, P_MIN={C.P_MIN}")
    comunes = None
    mats = {a: matriz(largo, a) for a in C.ANIOS}
    comunes = sorted(set.intersection(*[set(m.columns) for m in mats.values()]))
    log(f"Ramas comunes a los cinco años: {len(comunes)}")

    muns, prods, diags, excl = [], [], [], []
    for esp, cols in [("base", None), ("ramas_comunes", comunes)]:
        for a in C.ANIOS:
            X = mats[a] if cols is None else mats[a][cols]
            r = calcular_ice(X)
            d = r["diag"]
            m = r["mun"].merge(pob[pob.anio == a][["cve_mun", "log_pob"]], on="cve_mun", how="left")
            core = m[m.en_nucleo]
            d["spearman_ice_logpob"] = core.ice.corr(core.log_pob, method="spearman")
            d["n_sin_poblacion"] = int(m.log_pob.isna().sum())
            fil, col = r["nucleo"]
            if esp == "base":
                d["corr_ecomplexity"] = validar_ecomplexity(
                    X, fil, col, m.set_index("cve_mun").loc[fil, "ice"], log)
                assert d["corr_ecomplexity"] >= C.TOL_ECOMPLEXITY, d["corr_ecomplexity"]
                e = m.assign(ent=m.cve_mun.str[:2]).groupby("ent").agg(
                    municipios=("cve_mun", "size"), fuera_nucleo=("en_nucleo", lambda s: (~s).sum()),
                    ue_fuera=("ue_total", lambda s: s[~m.loc[s.index, "en_nucleo"]].sum()))
                e["anio"] = a
                excl.append(e.reset_index())
            assert d["componentes"] == 1, f"{esp} {a}: núcleo con {d['componentes']} componentes"
            d.update({"anio": a, "especificacion": esp})
            diags.append(d)
            m["anio"], m["especificacion"] = a, esp
            muns.append(m)
            p = r["prod"].assign(anio=a, especificacion=esp)
            prods.append(p)
            ue_fuera = m.loc[~m.en_nucleo, "ue_total"].sum() / m.ue_total.sum()
            log(f"[{esp} {a}] núcleo: {d['n_mun_nucleo']}/{d['n_mun_total']} municipios, "
                f"{d['n_ramas_nucleo']}/{d['n_ramas_total']} ramas ({d['iter_nucleo']} iter.); "
                f"UE fuera del núcleo {100*ue_fuera:.2f}%; ICE NaN: {d['n_ice_nan']}")
            log(f"      λ1..λ5 = {', '.join(f'{d[f'lambda{i}']:.4f}' for i in range(1, 6))}; "
                f"brecha λ2-λ3 = {d['brecha_l2_l3']:.4f}; eig>0.999: {d['n_eig_mayor_0999']}; "
                f"componentes: {d['componentes']}")
            log(f"      Spearman ICE~diversidad {d['spearman_ice_diversidad']:.3f}, ~log UE "
                f"{d['spearman_ice_logue']:.3f}, ~log pob {d['spearman_ice_logpob']:.3f}; "
                f"empates {d['empates_ice_pct']:.2f}%; corr proyección {d['corr_proyeccion_nucleo']:.6f}"
                + (f"; corr ecomplexity {d['corr_ecomplexity']:.6f}" if esp == "base" else ""))

    muns = pd.concat(muns, ignore_index=True)
    cols_out = ["anio", "cve_mun", "especificacion", "en_nucleo", "ue_total", "ramas_presentes",
                "diversidad", "ice", "ice_raw", "motivo_na"]
    muns[cols_out].to_csv(C.CLEAN / "ice_municipal.csv", index=False)
    pd.concat(prods).to_csv(C.CLEAN / "pci_rama.csv", index=False)
    diag = pd.DataFrame(diags)
    diag.to_csv(C.OUT / "diagnosticos_espectrales.csv", index=False)
    pd.concat(excl).to_csv(C.OUT / "02_exclusiones_nucleo_estado.csv", index=False)

    b = muns[muns.especificacion == "base"]
    w = b.pivot(index="cve_mun", columns="anio", values="ice")
    log("\nSpearman del ICE base entre años:\n" + w.corr(method="spearman").round(3).to_string())
    rc = muns.pivot_table(index=["anio", "cve_mun"], columns="especificacion", values="ice")
    log("Spearman base vs. ramas comunes por año: " + ", ".join(
        f"{a}: {g.base.corr(g.ramas_comunes, method='spearman'):.4f}"
        for a, g in rc.groupby(level=0)))
    pc = pd.concat(prods)
    pc = pc[pc.especificacion == "base"]
    for a in [2003, 2013, 2023]:
        t = pc[pc.anio == a].sort_values("pci")
        log(f"\n{a} — 5 ramas de mayor PCI: " + ", ".join(
            f"{r.rama} ({r.pci:.2f}, ubic. {r.ubicuidad})" for r in t.tail(5)[::-1].itertuples()))
        log(f"{a} — 5 ramas de menor PCI: " + ", ".join(
            f"{r.rama} ({r.pci:.2f}, ubic. {r.ubicuidad})" for r in t.head(5).itertuples()))
    log.close()


if __name__ == "__main__":
    main()
