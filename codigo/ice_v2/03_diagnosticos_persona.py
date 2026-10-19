"""V2 — Módulo 03: diagnósticos a nivel persona del ICE por ZM (D25).

Uso (desde la raíz del repositorio):  python codigo/ice_v2/03_diagnosticos_persona.py

Vista previa, no la base del DML: aplica a la muestra de análisis de
data/clean/02_base_dml.csv la misma regla de D15 (interpolación lineal entre años
censales al año en que la persona tenía 14) y la de D20 (población CONAPO en ese
año), usando cve_ice (con el padre de D21). La base del DML con V2 la arma
02_preparar_base_dml.R leyendo ice_zm_para_dml.csv y pob_unidad_conapo.csv.

Salida: outputs/ice_v2/diagnosticos_persona_zm.csv, unidades_muestra_zm.csv
"""
import numpy as np
import pandas as pd

import config_v2 as C2
from _v1 import cargar

C1, U = cargar()
ANIOS_ICE = [2003, 2008, 2013]


def wstd(x, w):
    m = np.average(x, weights=w)
    return (x - m) / np.sqrt(np.average((x - m) ** 2, weights=w))


def r2_ponderado(y, x, w):
    X = np.column_stack([np.ones_like(x), x])
    W = np.sqrt(w)
    b = np.linalg.lstsq(X * W[:, None], y * W, rcond=None)[0]
    e = y - X @ b
    return 1 - np.average(e ** 2, weights=w) / np.average((y - np.average(y, weights=w)) ** 2, weights=w), e


def main():
    C1.LOGS = C2.LOGS
    log = U.Log("v2_03_diagnosticos_persona")
    b = pd.read_csv(C2.BASE_DML, dtype={"cve_ice": str, "upm_muestra": str},
                    usecols=["cve_ice", "anio14", "factor", "ice14", "log_pob14", "upm_muestra"])
    ice = pd.read_csv(C2.CLEAN / "ice_zm_para_dml.csv", dtype={"cve_mun": str})
    pob = pd.read_csv(C2.CLEAN / "pob_unidad_conapo.csv", dtype={"cve_mun": str})
    t0 = np.where(b.anio14 < 2008, 2003, 2008)
    t1 = t0 + 5
    w = b.factor.to_numpy(float)
    filas, top = [], []
    for e in C2.DELIMITACIONES:
        k = ice.set_index(["cve_mun", "anio"])
        v0 = k[f"ice_{e}"].reindex(pd.MultiIndex.from_arrays([b.cve_ice, t0])).to_numpy()
        v1 = k[f"ice_{e}"].reindex(pd.MultiIndex.from_arrays([b.cve_ice, t1])).to_numpy()
        u0 = k[f"unidad_{e}"].reindex(pd.MultiIndex.from_arrays([b.cve_ice, t0])).to_numpy()
        u1 = k[f"unidad_{e}"].reindex(pd.MultiIndex.from_arrays([b.cve_ice, t1])).to_numpy()
        assert not np.isnan(v0).any() and not np.isnan(v1).any(), "personas sin ICE V2"
        assert (u0 == u1).all(), "la unidad cambia entre años censales (mapa no estático)"
        ice14 = v0 + (b.anio14 - t0) / (t1 - t0) * (v1 - v0)
        p = pob.set_index(["cve_mun", "anio"])
        lp = p[f"log_pob_{e}"].reindex(pd.MultiIndex.from_arrays([b.cve_ice, b.anio14])).to_numpy()
        assert not np.isnan(lp).any()
        unidad = pd.Series(u0)
        multi = unidad.str.startswith("ZM").to_numpy()
        z1, z2 = wstd(b.ice14.to_numpy(), w), wstd(ice14.to_numpy(), w)
        r2_v1, e1 = r2_ponderado(z1, b.log_pob14.to_numpy(), w)
        r2_v2, e2 = r2_ponderado(z2, lp, w)
        n_u = unidad.nunique()
        por_u = unidad.value_counts()
        filas.append({
            "delimitacion": e, "n": len(b),
            "n_origen_en_zm": int(multi.sum()), "pct_pond_origen_en_zm": 100 * w[multi].sum() / w.sum(),
            "zm_con_entrevistados": int(unidad[multi].nunique()),
            "grupos_v1_cve_ice": b.cve_ice.nunique(), "grupos_v2_unidad": n_u,
            "max_personas_por_grupo_v2": int(por_u.max()),
            "unidad_mas_grande": por_u.index[0],
            "pearson_ice14_v1_v2": np.corrcoef(z1, z2)[0, 1],
            "spearman_ice14_v1_v2": pd.Series(z1).corr(pd.Series(z2), method="spearman"),
            "pearson_ice14_v1_v2_solo_zm": np.corrcoef(z1[multi], z2[multi])[0, 1],
            "r2_ice_logpob_v1": r2_v1, "r2_ice_logpob_v2": r2_v2,
            "var_resid_logpob_v1": np.average(e1 ** 2, weights=w),
            "var_resid_logpob_v2": np.average(e2 ** 2, weights=w),
        })
        top.append(por_u.head(15).rename("personas").rename_axis("unidad").reset_index()
                   .assign(delimitacion=e, pct=lambda d: 100 * d.personas / len(b)))
    res = pd.DataFrame(filas)
    res.to_csv(C2.OUT / "diagnosticos_persona_zm.csv", index=False)
    pd.concat(top).to_csv(C2.OUT / "unidades_muestra_zm.csv", index=False)
    log(res.T.to_string())
    log("\n" + pd.concat(top).to_string(index=False))
    log.close()


if __name__ == "__main__":
    main()
