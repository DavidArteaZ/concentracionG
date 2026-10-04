"""Tablas adicionales para el Apéndice Metodológico del ICE (docs/anexo_ice.docx).

1. Municipios por año: con datos, en núcleo, fuera de núcleo; comparación con los
   catálogos CUCG 2003 y 2023 y altas/bajas entre censos consecutivos con motivo.
2. Ramas por año: presentes, en núcleo y excluidas (con nombre y presencia).
3. Escala: R2 del ICE sobre log población, log UE, diversidad y FE de estado;
   ICE vs. remuneración media; categorías de tamaño poblacional (estilo Soloaga
   et al., 2025) en la regresión de validación.
4. Concentración del PBT observado vs. UE (factor secundario del colapso del PBT).
Salidas: outputs/ice/anexo/*.csv y log 09_anexo_tablas.log
"""
import importlib

import numpy as np
import pandas as pd

from . import config as C
from .utils import Log, asegurar_dirs, calcular_ice, matriz, poblacion_censal

v06 = importlib.import_module("codigo.ice.06_validacion_externa")
OUTA = C.OUT / "anexo"


def nombres():
    from .export_ecomplexity import nombres_municipio
    return nombres_municipio()


def main():
    asegurar_dirs()
    OUTA.mkdir(exist_ok=True)
    log = Log("09_anexo_tablas")
    ice = pd.read_csv(C.CLEAN / "ice_municipal.csv", dtype={"cve_mun": str})
    ice = ice[ice.especificacion == "base"]
    nom = nombres()
    cu = {a: set(pd.read_csv(C.CUCG[a], dtype=str, usecols=["CVE_ENT", "CVE_MUN"])
                 .pipe(lambda d: d.CVE_ENT + d.CVE_MUN)) for a in (2003, 2023)}
    nuevos = cu[2023] - cu[2003]

    # ---------------------------------------------------------------- 1. municipios
    filas, altas_bajas = [], []
    prev = None
    for a in C.ANIOS:
        m = ice[ice.anio == a]
        s = set(m.cve_mun)
        r = {"anio": a, "municipios_con_ue": len(s), "en_nucleo": int(m.en_nucleo.sum()),
             "fuera_nucleo_con_ice_proyectado": int((~m.en_nucleo).sum()),
             "sin_ice": int(m.ice.isna().sum()),
             "fuera_por_ue_menor_30": int(((~m.en_nucleo) & (m.ue_total < C.U_MIN)).sum()),
             "fuera_por_menos_de_5_ramas_(con_ue>=30)": int(((~m.en_nucleo) & (m.ue_total >= C.U_MIN)
                                                              & (m.ramas_presentes < C.D_MIN)).sum())}
        if a in cu:
            r[f"catalogo_cucg_{a}"] = len(cu[a])
            r["en_catalogo_sin_ue"] = len(cu[a] - s)
            r["con_ue_fuera_de_catalogo"] = len(s - cu[a])
            for c in sorted(cu[a] - s):
                altas_bajas.append({"anio": a, "cve_mun": c, "nombre": nom.get(c), "tipo": "en catálogo, sin UE en SAIC",
                                    "motivo": "sin unidades económicas registradas en el censo"})
            for c in sorted(s - cu[a]):
                altas_bajas.append({"anio": a, "cve_mun": c, "nombre": nom.get(c), "tipo": "con UE, fuera del catálogo",
                                    "motivo": "creado entre el catálogo y el levantamiento censal"})
        if prev is not None:
            for c in sorted(s - prev):
                motivo = ("municipio de nueva creación" if c in nuevos else
                          "reaparece con UE registradas (existía; sin UE en el censo anterior)")
                altas_bajas.append({"anio": a, "cve_mun": c, "nombre": nom.get(c),
                                    "tipo": "alta respecto al censo anterior", "motivo": motivo})
            for c in sorted(prev - s):
                altas_bajas.append({"anio": a, "cve_mun": c, "nombre": nom.get(c),
                                    "tipo": "baja respecto al censo anterior",
                                    "motivo": "sin unidades económicas registradas en este censo"})
        prev = s
        filas.append(r)
    tm = pd.DataFrame(filas)
    tm.to_csv(OUTA / "municipios_por_anio.csv", index=False)
    ab = pd.DataFrame(altas_bajas)
    ab.to_csv(OUTA / "municipios_altas_bajas.csv", index=False)
    log("Municipios por año:\n" + tm.to_string(index=False))
    log("\nAltas, bajas y diferencias con catálogo:\n" + ab.to_string(index=False))

    # ---------------------------------------------------------------- 2. ramas
    largo = pd.read_csv(C.CLEAN / "saic_largo.csv.gz", dtype={"cve_mun": str, "codigo": str})
    cat = pd.read_csv(C.CLEAN / "catalogo_ramas.csv", dtype={"rama": str}).set_index("rama").nombre_rama
    fr, ex = [], []
    for a in C.ANIOS:
        X = matriz(largo, a)
        r = calcular_ice(X)
        fil, col = r["nucleo"]
        pres = (X > 0).sum(0)
        fuera = sorted(set(X.columns) - set(col))
        fr.append({"anio": a, "ramas_presentes": X.shape[1], "ramas_en_nucleo": len(col),
                   "ramas_fuera_nucleo": len(fuera),
                   "ramas_ausentes_vs_union_279": len(C.RAMAS_AUSENTES[a])})
        for p in fuera:
            ex.append({"anio": a, "rama": p, "nombre": cat.get(p), "municipios_con_ue": int(pres[p]),
                       "motivo": f"presente en menos de {C.P_MIN} municipios (P_MIN)"})
        for p in sorted(C.RAMAS_AUSENTES[a]):
            ex.append({"anio": a, "rama": p, "nombre": cat.get(p), "municipios_con_ue": 0,
                       "motivo": "sin cobertura en el censo de ese año"})
    tr, er = pd.DataFrame(fr), pd.DataFrame(ex)
    tr.to_csv(OUTA / "ramas_por_anio.csv", index=False)
    er.to_csv(OUTA / "ramas_excluidas.csv", index=False)
    log("\nRamas por año:\n" + tr.to_string(index=False))
    log("\nRamas excluidas:\n" + er.to_string(index=False))

    # ---------------------------------------------------------------- 3. escala
    pob = poblacion_censal()
    tot = pd.read_csv(C.CLEAN / "saic_totales_limpio.csv", dtype={"cve_mun": str})
    cen = pd.read_csv(C.CLEAN / "centroides_municipales.csv", dtype={"cve_mun": str})
    df = (ice.merge(pob, on=["anio", "cve_mun"]).merge(tot[["anio", "cve_mun", "log_rem_rel"]],
          on=["anio", "cve_mun"], how="left").merge(cen, on="cve_mun"))
    df["log_ue"] = np.log(df.ue_total)
    df["ent"] = df.cve_mun.str[:2]
    pobn = np.exp(df.log_pob)
    df["tam_pob"] = pd.cut(pobn, [0, 15_000, 50_000, 350_000, np.inf],
                           labels=["<15 mil", "15-50 mil", "50-350 mil", ">=350 mil"], right=False).astype(str)
    esc = []
    for a in C.ANIOS:
        d = df[df.anio == a]
        y = d.ice.to_numpy()
        fila = {"anio": a, "n": len(d)}
        for nombre, cols, fe in [("log_pob", ["log_pob"], None), ("log_pob+log_ue", ["log_pob", "log_ue"], None),
                                 ("+diversidad", ["log_pob", "log_ue", "diversidad"], None),
                                 ("+FE_estado", ["log_pob", "log_ue", "diversidad"], ["ent"]),
                                 ("categorias_tamano", [], ["tam_pob"])]:
            X, _ = v06.diseno(d, cols, fe)
            _, e, _ = v06.ols(y, X)
            fila[f"r2_{nombre}"] = 1 - (e @ e) / ((y - y.mean()) @ (y - y.mean()))
        dd = d.dropna(subset=["log_rem_rel"])
        fila["pearson_ice_logrem"] = dd.ice.corr(dd.log_rem_rel)
        fila["spearman_ice_logrem"] = dd.ice.corr(dd.log_rem_rel, method="spearman")
        g = d.groupby("tam_pob").ice
        fila.update({f"sd_ice_{k}": v for k, v in g.std().items()})
        fila.update({f"n_{k}": v for k, v in g.size().items()})
        esc.append(fila)
    esc = pd.DataFrame(esc)
    esc.to_csv(OUTA / "escala_varianza_ice.csv", index=False)
    pd.set_option("display.width", 250)
    log("\nEscala y varianza del ICE:\n" + esc.round(3).to_string(index=False))

    filas = []
    for a in C.ANIOS:
        d = df[(df.anio == a)].dropna(subset=["log_rem_rel", "lat"]).reset_index(drop=True)
        for nombre, cols, fe in [("(A) ICE + categorías de tamaño", [], ["tam_pob"]),
                                 ("(B) ICE + categorías + FE estado", [], ["tam_pob", "ent"]),
                                 ("(C) ICE + categorías + log pob + log UE + diversidad + FE estado",
                                  ["log_pob", "log_ue", "diversidad"], ["tam_pob", "ent"])]:
            r = v06.estimar(d, "log_rem_rel", ["ice"] + cols, fe, conley=False)
            r.update({"anio": a, "especificacion": nombre})
            filas.append(r)
    sol = pd.DataFrame(filas)
    sol.to_csv(OUTA / "validacion_categorias_tamano.csv", index=False)
    log("\nValidación con categorías de tamaño (log remuneración media relativa):\n" +
        sol[["anio", "especificacion", "beta_ice", "se_crv1", "p_wild_cluster", "r2_parcial_ice", "n"]]
        .round(4).to_string(index=False))

    # ---------------------------------------------------------------- 4. concentración PBT
    rama = largo[largo.nivel == "rama"]
    conc = []
    for a in C.ANIOS:
        for var in ["ue", "pbt"]:
            s = rama[(rama.anio == a) & (rama.variable == var)].groupby("cve_mun").valor.sum(min_count=1)
            s = s.fillna(0).clip(lower=0).sort_values(ascending=False)
            n = len(s)
            conc.append({"anio": a, "variable": var, "municipios": n,
                         "pct_top1": 100 * s.iloc[:max(1, n // 100)].sum() / s.sum(),
                         "pct_top5": 100 * s.iloc[:max(1, n // 20)].sum() / s.sum(),
                         "pct_municipios_valor_cero": 100 * (s == 0).mean()})
    conc = pd.DataFrame(conc)
    conc.to_csv(OUTA / "concentracion_pbt_ue.csv", index=False)
    log("\nConcentración (PBT observado sumando ramas no suprimidas; UE completas):\n" + conc.round(1).to_string(index=False))
    log.close()


if __name__ == "__main__":
    main()
