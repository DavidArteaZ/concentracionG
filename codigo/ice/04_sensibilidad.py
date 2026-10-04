"""Módulo 04 — Sensibilidad del ICE (afirmación A5).

Alternativas contra la base (U_MIN=30, D_MIN=5, P_MIN=10, rama, eigenvector):
  a. malla de umbrales U x D x P
  b. reglas de exclusión de ramas R1, R2, R3 (panel aparte), R4
  c. nivel clase
  d. Fitness-Complexity (Tacchella et al., 2012) en el mismo núcleo
  e. ramas comunes a los cinco años (del Módulo 02)
Métricas por año: Spearman con la base, % de municipios que cambian de quintil,
municipios fuera del núcleo / sin ICE, y entrevistados de la cohorte 1 de
ESRU-EMOVI cuyo municipio a los 14 años queda fuera del núcleo o sin ICE.
Salidas: data/clean/ice/ice_alternativas.csv.gz; outputs/ice/04_sensibilidad.csv,
         04_redundancia_reglas.csv
"""
import itertools

import numpy as np
import pandas as pd

from . import config as C
from .utils import Log, asegurar_dirs, calcular_ice, emovi_cohorte1, matriz


def metricas(alt, base, emovi, anio):
    j = base.set_index("cve_mun")[["ice"]].join(alt.set_index("cve_mun")[["ice"]],
                                                rsuffix="_alt", how="inner").dropna()
    qb = pd.qcut(j.ice, 5, labels=False)
    qa = pd.qcut(j.ice_alt, 5, labels=False)
    e = emovi[emovi.anio_ice == anio]
    a = alt.set_index("cve_mun")
    en_tabla = e.cve_mun.isin(a.index)
    fuera = en_tabla & ~e.cve_mun.map(a.en_nucleo).fillna(False).astype(bool)
    sin_ice = ~en_tabla | e.cve_mun.map(a.ice).isna()
    return {"spearman_base": j.ice.corr(j.ice_alt, method="spearman"),
            "pct_cambia_quintil": 100 * (qb != qa).mean(),
            "mun_fuera_nucleo": int((~alt.en_nucleo).sum()),
            "mun_sin_ice": int(alt.ice.isna().sum()),
            "emovi_n": len(e), "emovi_fuera_nucleo": int(fuera.sum()),
            "emovi_sin_ice": int(sin_ice.sum()),
            "emovi_fuera_nucleo_pct_pond": (100 * e.factor[fuera].sum() / e.factor.sum()) if len(e) else np.nan}


def main():
    asegurar_dirs()
    log = Log("04_sensibilidad")
    largo = pd.read_csv(C.CLEAN / "saic_largo.csv.gz", dtype={"cve_mun": str, "codigo": str})
    ice02 = pd.read_csv(C.CLEAN / "ice_municipal.csv", dtype={"cve_mun": str})
    emovi = emovi_cohorte1()
    log(f"Cohorte 1 ESRU-EMOVI con municipio a los 14 válido: {len(emovi):,} "
        f"(por año ICE: {emovi.anio_ice.value_counts().sort_index().to_dict()})")

    filas, alts, redund = [], [], []
    for a in C.ANIOS:
        X = matriz(largo, a)
        Xc = matriz(largo, a, nivel="clase")
        base = ice02[(ice02.anio == a) & (ice02.especificacion == "base")]
        _, col_base = calcular_ice(X)["nucleo"]
        specs = {}
        for u, d, p in itertools.product(C.GRID_U, C.GRID_D, C.GRID_P):
            specs[f"umbral_U{u}_D{d}_P{p}"] = (X, dict(u_min=u, d_min=d, p_min=p))
        for nombre, regla in C.REGLAS_EXCLUSION.items():
            excl = [r for r in X.columns if regla(r)]
            ya_fuera = [r for r in excl if r not in col_base]
            redund.append({"anio": a, "regla": nombre, "ramas_excluidas": " ".join(excl),
                           "n_excluidas": len(excl), "ya_fuera_del_nucleo_por_P_MIN": " ".join(ya_fuera)})
            specs[f"excluye_{nombre}"] = (X.drop(columns=excl), {})
        specs["clase"] = (Xc, {})
        specs["fitness"] = (X, dict(metodo="fitness"))
        for nombre, (Xs, kw) in specs.items():
            r = calcular_ice(Xs, **kw)
            m = r["mun"]
            met = metricas(m, base, emovi, a)
            met.update({"anio": a, "especificacion": nombre, "n_mun_nucleo": r["diag"]["n_mun_nucleo"],
                        "n_ramas_nucleo": r["diag"]["n_ramas_nucleo"],
                        "componentes": r["diag"]["componentes"],
                        "lambda2": r["diag"].get("lambda2"), "lambda3": r["diag"].get("lambda3")})
            if nombre == "fitness":
                met["fitness_iteraciones"] = r["diag"]["fitness_iteraciones"]
                met["fitness_ranking_estable"] = r["diag"]["fitness_ranking_estable"]
            filas.append(met)
            alts.append(m[["cve_mun", "en_nucleo", "ice"]].assign(anio=a, especificacion=nombre))
        rc = ice02[(ice02.anio == a) & (ice02.especificacion == "ramas_comunes")]
        met = metricas(rc, base, emovi, a)
        met.update({"anio": a, "especificacion": "ramas_comunes"})
        filas.append(met)
        alts.append(rc[["cve_mun", "en_nucleo", "ice"]].assign(anio=a, especificacion="ramas_comunes"))
        log(f"[{a}] {len(specs) + 1} especificaciones calculadas")

    tab = pd.DataFrame(filas)
    tab.to_csv(C.OUT / "04_sensibilidad.csv", index=False)
    pd.DataFrame(redund).to_csv(C.OUT / "04_redundancia_reglas.csv", index=False)
    alts = pd.concat(alts, ignore_index=True)
    alts.to_csv(C.CLEAN / "ice_alternativas.csv.gz", index=False)

    pd.set_option("display.width", 220)
    base_nom = f"umbral_U{C.U_MIN}_D{C.D_MIN}_P{C.P_MIN}"
    assert (tab.loc[tab.especificacion == base_nom, "spearman_base"] > 0.99999).all()
    um = tab[tab.especificacion.str.startswith("umbral")]
    log("\nMalla de umbrales (27 combinaciones x 5 años): Spearman con la base "
        f"min {um.spearman_base.min():.4f}, mediana {um.spearman_base.median():.4f}; "
        f"% cambia quintil max {um.pct_cambia_quintil.max():.1f}")
    peor = um.nsmallest(5, "spearman_base")[["anio", "especificacion", "spearman_base",
                                              "pct_cambia_quintil", "mun_fuera_nucleo"]]
    log("Combinaciones más alejadas de la base:\n" + peor.round(4).to_string(index=False))
    por_p = um.groupby(um.especificacion.str.extract(r"_P(\d+)")[0].astype(int)).spearman_base.agg(["min", "median"])
    log("Spearman con la base según P_MIN:\n" + por_p.round(4).to_string())
    otros = tab[~tab.especificacion.str.startswith("umbral")]
    log("\nOtras alternativas:\n" + otros.pivot(index="especificacion", columns="anio",
                                               values="spearman_base").round(4).to_string())
    log("\n% de municipios que cambian de quintil:\n" + otros.pivot(
        index="especificacion", columns="anio", values="pct_cambia_quintil").round(1).to_string())
    b = tab[tab.especificacion == base_nom][["anio", "mun_fuera_nucleo", "emovi_n", "emovi_fuera_nucleo",
                                             "emovi_fuera_nucleo_pct_pond", "emovi_sin_ice"]]
    log("\nEspecificación base — entrevistados de la cohorte 1 afectados (según su año ICE):\n"
        + b.round(2).to_string(index=False))
    log("\nRedundancia de las reglas con P_MIN:\n" + pd.DataFrame(redund).query("anio in [2003, 2023]")
        .to_string(index=False))
    f = tab[tab.especificacion == "fitness"][["anio", "fitness_iteraciones", "fitness_ranking_estable"]]
    log("\nConvergencia Fitness (ranking estable 200 iteraciones):\n" + f.to_string(index=False))
    log.close()


if __name__ == "__main__":
    main()
