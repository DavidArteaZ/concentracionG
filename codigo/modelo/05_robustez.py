"""05_robustez.py: batería de robustez del DML (sin cambiar la especificación principal).

Proyecto: Movilidad social y complejidad económica (ESRU-EMOVI 2023).

Cada prueba cambia una sola cosa respecto de 03_dml.py (Y, D, X o la
muestra) y se estima en las dos especificaciones (principal, con escala, y
total, sin escala), salvo las pruebas de escala, que solo afectan a la
principal. Se reutilizan los pliegues, las semillas, la rejilla y el aprendiz
de 03_dml.py (XGBoost, elegido en las cuatro funciones auxiliares). Solo se
vuelve a ajustar la función auxiliar que cambia:
  - cambia Y          -> se reajusta m(X); e(X) se reutiliza.
  - cambia D          -> se reajusta e(X); m(X) se reutiliza.
  - cambia X o la muestra -> se reajustan ambas.
Con la misma partición, las diferencias contra la principal no vienen del azar
de los pliegues.

Pruebas (decisiones en decisiones_metodologicas.md):
  servicios      D6   + agua y electricidad de la vivienda, p26c baño, p33a-i barrio
  ice_cercano    D15a ICE del año censal más cercano
  ice_2003       D15b ICE de 2003 para todos
  sin_edad25     acumulación de edad en 25 (18.5% ponderado): se excluye
  pob_censo      D20  población censal 2000-2010 interpolada en lugar de CONAPO
  log_ue         D20a + log de unidades económicas a los 14
  soloaga        D20b categorías de tamaño de Soloaga en lugar del log de población
  etnia_auto     D17  + p110 (autoadscripción; "Negra" agrupada con "Indígena") y p112
  no_migrantes   D14  solo quienes viven en su municipio de origen (condiciona a
                      una variable posterior al tratamiento; se declara así)
  y_quintil      D3   Y = quintil de destino (1-5); E[Y|X] por regresión, que es
                      el mismo objetivo que sum_k k p_k
  y_sube_q, y_sube_2q, y_q12_q45   D9  binarias observadas de movilidad (x100: pp)
  ice_alt_*      33 ICE alternativos (umbrales, ramas, fitness, clase), 5 repeticiones

D se estandariza con la media y la DE ponderadas de la muestra completa
(n = 5,072) de cada variable de ICE, para que beta esté en las mismas unidades
que la principal también en las submuestras.

Uso (desde la raíz del proyecto):
  python codigo/modelo/05_robustez.py                 # todo
  python codigo/modelo/05_robustez.py --grupo bateria
  python codigo/modelo/05_robustez.py --grupo ice_alt

Insumos:  data/clean/02_base_dml.csv, data/clean/03_resultados/
Salidas:  data/clean/05_resultados/
"""
import argparse
import importlib.util
import json
import platform
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import norm

_spec = importlib.util.spec_from_file_location(
    "dml03", Path(__file__).resolve().parent / "03_dml.py")
dml03 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(dml03)

# ==========================================
# Parámetros
# ==========================================
RAIZ = dml03.RAIZ
ENTRADA = RAIZ / "data" / "clean" / "03_resultados"
SALIDA = RAIZ / "data" / "clean" / "05_resultados"
APRENDIZ = "xgb"
N_REP_BATERIA = 20
N_REP_ICE_ALT = 5
ESCALA = "log_pob14"
SERVICIOS = ["ac_or6_na", "ac_or10_na", "p26c"] + [f"p33{c}" for c in "abcdefghi"]
P110_AGRUPA = {1: 2}   # D17: "Negra" (1; 52 casos) se agrupa con "Indígena" (2)
Z = 1.959964


def prueba(nombre, decision, especs=("principal", "total"), y=None, d=None,
           agregar=(), quitar=(), filtro=None, escala_y=1.0, grupo="bateria"):
    return dict(nombre=nombre, decision=decision, especs=especs, y=y or dml03.Y_VAR,
                d=d or dml03.D_VAR, agregar=list(agregar), quitar=list(quitar),
                filtro=filtro, escala_y=escala_y, grupo=grupo)


PRUEBAS = [
    prueba("servicios", "D6", agregar=SERVICIOS),
    prueba("ice_cercano", "D15a", d="ice14_cercano"),
    prueba("ice_2003", "D15b", d="ice14_2003"),
    prueba("sin_edad25", "acumulación de edad", filtro=lambda b: b.edad != 25),
    prueba("pob_censo", "D20", especs=("principal",), agregar=["log_pob14_censo"],
           quitar=[ESCALA]),
    prueba("log_ue", "D20a", especs=("principal",), agregar=["log_ue14"]),
    prueba("soloaga", "D20b", especs=("principal",), agregar=["tam_soloaga14"],
           quitar=[ESCALA]),
    prueba("etnia_auto", "D17", agregar=["p110", "p112_num"]),
    prueba("no_migrantes", "D14", filtro=lambda b: b.migro == 0),
    prueba("y_quintil", "D3", y="q_act_c1"),
    prueba("y_sube_q", "D9", y="y_sube_quintil", escala_y=100),
    prueba("y_sube_2q", "D9", y="y_sube_2quintil", escala_y=100),
    prueba("y_q12_q45", "D9", y="y_q12_a_q45", escala_y=100),
]
def _alternativos(dicc):
    otros = dicc.loc[dicc.rol == "tratamiento", "variable"]
    return [v for v in otros if v not in ("ice14", "ice14_cercano", "ice14_2003")]


# ==========================================
# X de cada prueba
# ==========================================
def matriz(base, dicc, espec, pr):
    x = dml03.matriz_x(base, dicc, dml03.ESPECIFICACIONES[espec] + pr["quitar"])
    extra = []
    for v in pr["agregar"]:
        if v == "p110":
            extra.append(pd.get_dummies(base[v].replace(P110_AGRUPA).astype(str),
                                        prefix=v, dtype=float))
        elif v == "tam_soloaga14":
            # XGBoost no acepta "<" ni "[" en los nombres de columnas.
            cat = base[v].astype(str).str.replace("<", "menos", regex=False) \
                .str.replace(">=", "mas", regex=False)
            extra.append(pd.get_dummies(cat, prefix=v, dtype=float))
        else:
            extra.append(base[[v]].astype(float))
    if extra:
        x = pd.concat([x] + extra, axis=1)
    assert x.columns.is_unique
    for v in pr["quitar"]:
        assert v not in x.columns
    return x


# ==========================================
# Estimación de una prueba
# ==========================================
def correr(pr, base, dicc, pliegues, preds03, n_rep, w, clusters, log):
    filas_rep, filas = [], []
    filtro = np.ones(len(base), bool) if pr["filtro"] is None else pr["filtro"](base).to_numpy()
    y_all = base[pr["y"]].to_numpy(dtype=float) * pr["escala_y"]
    dv = base[pr["d"]].to_numpy(dtype=float)
    mu = np.average(dv, weights=w)
    sd = np.sqrt(np.average((dv - mu) ** 2, weights=w))
    d_all = (dv - mu) / sd
    usa = filtro & ~np.isnan(y_all) & ~np.isnan(d_all)
    cambia_x = bool(pr["agregar"] or pr["quitar"]) or pr["filtro"] is not None
    refit = {"m": cambia_x or pr["y"] != dml03.Y_VAR,
             "e": cambia_x or pr["d"] != dml03.D_VAR}
    grupos = base[dml03.GRUPO_PLIEGUES].to_numpy()
    parciales = SALIDA / "parciales"
    parciales.mkdir(parents=True, exist_ok=True)
    for espec in pr["especs"]:
        x = matriz(base, dicc, espec, pr) if any(refit.values()) else None
        for r in range(n_rep):
            fold = pliegues[r]
            pred = {}
            for nuis, obj in (("m", y_all), ("e", d_all)):
                if not refit[nuis]:
                    pred[nuis] = preds03[(espec, nuis, r)]
                    continue
                archivo = parciales / f"{pr['nombre']}_{espec}_{nuis}_rep{r:02d}.csv.gz"
                if archivo.exists():
                    pred[nuis] = pd.read_csv(archivo).pred.to_numpy()
                    continue
                t0 = time.time()
                entrena = filtro & ~np.isnan(obj)
                oof, hiper = np.full(len(base), np.nan), []
                for k in range(dml03.N_FOLDS):
                    tr = np.where(entrena & (fold != k))[0]
                    te = np.where(filtro & (fold == k))[0]
                    mod, hp = dml03.ajustar(APRENDIZ, x.iloc[tr], obj[tr], w[tr], grupos[tr],
                                            (dml03.SEMILLA + r) * 10 + k)
                    oof[te] = mod.predict(x.iloc[te])
                    hiper.append(dict(rep=r, fold=k, **hp))
                pd.DataFrame({"index": base["index"], "pred": oof}).to_csv(archivo, index=False)
                pd.DataFrame(hiper).to_csv(str(archivo).replace(".csv.gz", "_hiper.csv.gz"),
                                           index=False)
                pred[nuis] = oof
                log(f"{pr['nombre']} {espec} {nuis} rep {r + 1}/{n_rep} ({time.time() - t0:.0f} s)")
            u = usa
            y_res, d_res = y_all[u] - pred["m"][u], d_all[u] - pred["e"][u]
            res = dml03.etapa_final(y_res, d_res, w[u], (clusters[0][u], clusters[1][u]))
            def r2(obj, p):
                return 1 - np.average((obj[u] - p[u]) ** 2, weights=w[u]) / \
                    np.average((obj[u] - np.average(obj[u], weights=w[u])) ** 2, weights=w[u])
            filas_rep.append(dict(prueba=pr["nombre"], espec=espec, rep=r, **res,
                                  var_d_res=np.average(d_res ** 2, weights=w[u]),
                                  r2_m=r2(y_all, pred["m"]), r2_e=r2(d_all, pred["e"])))
        f = pd.DataFrame([fr for fr in filas_rep if fr["prueba"] == pr["nombre"]
                          and fr["espec"] == espec])
        th, se = dml03.agregar(f.theta, f.se_2v)
        filas.append(dict(prueba=pr["nombre"], decision=pr["decision"], espec=espec,
                          y=pr["y"], d=pr["d"], escala_y=pr["escala_y"], n=int(usa.sum()),
                          n_mun=int(pd.Series(clusters[0][usa]).nunique()), n_rep=n_rep,
                          beta=th, se_2v=se, ic95_inf=th - Z * se, ic95_sup=th + Z * se,
                          p=float(2 * norm.sf(abs(th / se))),
                          beta_min_rep=f.theta.min(), beta_max_rep=f.theta.max(),
                          var_d_res=f.var_d_res.median(), r2_m=f.r2_m.mean(),
                          r2_e=f.r2_e.mean(), reajuste_m=refit["m"], reajuste_e=refit["e"]))
    return filas, filas_rep


# ==========================================
# Principal
# ==========================================
def main(grupo, n_rep_bateria, n_rep_alt):
    base, dicc = dml03.cargar()
    w = base[dml03.PESO].to_numpy(dtype=float)
    w = w / w.mean()
    clusters = (base[dml03.CLUSTERS[0]].to_numpy(), base[dml03.CLUSTERS[1]].to_numpy())
    pl = pd.read_csv(ENTRADA / "pliegues.csv.gz")
    pliegues = {}
    for r, g in pl.groupby("rep"):
        assert (g["index"].to_numpy() == base["index"].to_numpy()).all()
        pliegues[r] = g.fold.to_numpy()
    p03 = pd.read_csv(ENTRADA / "predicciones_oof.csv.gz").query("aprendiz == @APRENDIZ")
    preds03 = {}
    for (espec, nuis, r), g in p03.groupby(["espec", "nuisance", "rep"]):
        assert (g["index"].to_numpy() == base["index"].to_numpy()).all()
        preds03[(espec, nuis, r)] = g.pred.to_numpy()
    SALIDA.mkdir(parents=True, exist_ok=True)
    bitacora = open(SALIDA / "bitacora.log", "a")

    def log(msg):
        print(msg, flush=True)
        bitacora.write(msg + "\n")
        bitacora.flush()

    pruebas = [dict(p, n_rep=n_rep_bateria) for p in PRUEBAS] + \
              [dict(prueba(f"alt_{v.removeprefix('ice14_')}", "ICE alternativo", d=v,
                           grupo="ice_alt"), n_rep=n_rep_alt) for v in _alternativos(dicc)]
    # Referencia: la principal con las mismas repeticiones (debe reproducir la fase 2).
    pruebas = [dict(prueba("referencia", "principal"), n_rep=n_rep_bateria)] + pruebas
    if grupo != "todo":
        pruebas = [p for p in pruebas if p["grupo"] == grupo or p["nombre"] == "referencia"]

    est, por_rep = [], []
    for pr in pruebas:
        log(f"== {pr['nombre']} ({pr['n_rep']} repeticiones)")
        f, fr = correr(pr, base, dicc, pliegues, preds03, pr["n_rep"], w, clusters, log)
        est += f
        por_rep += fr
        pd.DataFrame(est).to_csv(SALIDA / f"estimaciones_{grupo}.csv", index=False)
        pd.DataFrame(por_rep).to_csv(SALIDA / f"por_rep_{grupo}.csv", index=False)
    est = pd.DataFrame(est)
    ref = est.query("prueba == 'referencia'").set_index("espec")
    if n_rep_bateria == dml03.N_REP:
        e03 = pd.read_csv(ENTRADA / "estimaciones.csv").query("combo == 'elegido'").set_index("espec")
        for espec in ("principal", "total"):
            assert abs(ref.loc[espec, "beta"] - e03.loc[espec, "beta"]) < 1e-9
    # Referencia de 5 repeticiones para comparar los ICE alternativos.
    if (est.n_rep == n_rep_alt).any() and n_rep_alt != n_rep_bateria:
        pr = dict(prueba("referencia_5rep", "principal"), n_rep=n_rep_alt)
        f, _ = correr(pr, base, dicc, pliegues, preds03, n_rep_alt, w, clusters, log)
        est = pd.concat([est, pd.DataFrame(f)])
    est.to_csv(SALIDA / f"estimaciones_{grupo}.csv", index=False)
    import scipy, sklearn, xgboost
    json.dump(dict(grupo=grupo, n_rep_bateria=n_rep_bateria, n_rep_alt=n_rep_alt,
                   python=sys.version, plataforma=platform.platform(), numpy=np.__version__,
                   pandas=pd.__version__, scipy=scipy.__version__, sklearn=sklearn.__version__,
                   xgboost=xgboost.__version__),
              open(SALIDA / f"entorno_{grupo}.json", "w"), indent=2)
    pd.set_option("display.width", 250)
    log(est[["prueba", "espec", "n", "beta", "se_2v", "ic95_inf", "ic95_sup", "p",
             "var_d_res", "r2_e"]].to_string(index=False))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--grupo", choices=["bateria", "ice_alt", "todo"], default="todo")
    ap.add_argument("--n-rep", type=int, default=N_REP_BATERIA)
    ap.add_argument("--n-rep-alt", type=int, default=N_REP_ICE_ALT)
    a = ap.parse_args()
    if a.n_rep != N_REP_BATERIA:
        SALIDA = RAIZ / "data" / "clean" / "05_resultados_prueba"
    main(a.grupo, a.n_rep, a.n_rep_alt)
