"""03_dml.py: DML parcialmente lineal del ICE de origen sobre la posición de destino.

Proyecto: Movilidad social y complejidad económica (ESRU-EMOVI 2023).

Modelo (D5):  Y = g(X) + beta * D + u,   D = e(X) + v
  Y = pct_act_c1 (percentil de destino dentro de la cohorte, 0-100; D3)
  D = ice14 estandarizado con pesos (media 0, DE 1 en la muestra; D15)
  X = X principal de diccionario_variables_02.csv (D6, D10-D13, D17, D19, D20)

El script corre en dos fases para fijar la lectura de un resultado nulo antes
de ver beta:
  --fase 1  Funciones auxiliares m(X) = E[Y|X] y e(X) = E[D|X] con
            cross-fitting repetido, selección del algoritmo por error fuera de
            pliegue y efecto mínimo detectable (potencia). No calcula beta.
  --fase 2  Beta, errores estándar agrupados (municipio de origen x UPM; D16),
            cociente condicional/total (D20) y validación contra DoubleML.

Especificaciones:
  principal  X principal (incluye log_pob14: asociación más allá de la escala)
  total      X principal sin log_pob14 (asociación total, D20)

Decisiones implementadas:
  D7   XGBoost, random forest y regresión lineal (referencia, T10). Se elige,
       por función auxiliar y especificación, el algoritmo con menor ECM
       ponderado fuera de pliegue (promedio sobre repeticiones). La regla se
       fija aquí, antes de estimar.
  D8   5 pliegues agrupados por municipio de origen (cve_ice, padre en D21),
       estratificados por quintil de destino.
  T8   Hiperparámetros ajustados dentro de cada pliegue de entrenamiento con
       validación cruzada agrupada interna (anidada). Semillas fijas.
  T9   Factor de expansión como peso en el entrenamiento, la evaluación y la
       etapa final.
  D16  DoubleMLPLR no acepta pesos: la etapa final (MCO ponderado de Y~ sobre
       D~) y su varianza agrupada en dos dimensiones (Cameron, Gelbach y
       Miller, 2011) se calculan a mano y se validan contra DoubleML con pesos
       iguales a 1.
  Agregación de repeticiones: mediana de beta y
       SE = sqrt(mediana(SE_r^2 + (beta_r - beta_mediana)^2))
       (Chernozhukov et al., 2018, sección 3.4).

Uso (desde la raíz del proyecto):
  python codigo/modelo/03_dml.py --fase 1
  python codigo/modelo/03_dml.py --fase 2
  Opcional: --n-rep 2 para una prueba corta (escribe en 03_resultados_prueba/).

Insumos:  data/clean/02_base_dml.csv, data/clean/02_resultados/diccionario_variables_02.csv
Salidas:  data/clean/03_resultados/
"""
import argparse
import json
import platform
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import sklearn
import xgboost
from sklearn.ensemble import RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import GroupKFold, StratifiedGroupKFold
from sklearn.pipeline import make_pipeline
from xgboost import XGBRegressor

# ==========================================
# Parámetros
# ==========================================
RAIZ = Path(__file__).resolve().parents[2]
BASE = RAIZ / "data" / "clean" / "02_base_dml.csv"
DICC = RAIZ / "data" / "clean" / "02_resultados" / "diccionario_variables_02.csv"

SEMILLA = 20261013
N_FOLDS = 5
N_REP = 20
N_FOLDS_INTERNOS = 3          # validación cruzada interna para hiperparámetros
N_JOBS = 4

Y_VAR = "pct_act_c1"
D_VAR = "ice14"
PESO = "factor"
GRUPO_PLIEGUES = "cve_ice"     # D8, D21
ESTRATO_PLIEGUES = "q_act_c1"  # D8
CLUSTERS = ("cve_ice", "upm_muestra")  # D16

ESPECIFICACIONES = {
    "principal": [],             # variables que se QUITAN de la X principal
    "total": ["log_pob14"],
}

# Rejillas pequeñas y fijas (T8). XGBoost elige el número de árboles con
# parada temprana en los pliegues internos.
REJILLA_XGB = [{"max_depth": 2}, {"max_depth": 4}]
XGB_FIJOS = dict(learning_rate=0.05, subsample=0.8, colsample_bytree=0.8,
                 min_child_weight=5, reg_lambda=1.0, tree_method="hist",
                 n_jobs=N_JOBS)
XGB_MAX_ARBOLES = 1500
XGB_PARADA = 50
REJILLA_RF = [{"min_samples_leaf": 10}, {"min_samples_leaf": 40}]
RF_FIJOS = dict(n_estimators=300, max_features=1 / 3, n_jobs=N_JOBS)

APRENDICES = ("lineal", "rf", "xgb")
Z_POTENCIA = 1.959964 + 0.841621   # alfa = 0.05 a dos colas, potencia = 0.80


# ==========================================
# Datos
# ==========================================
def cargar():
    tipos = {c: str for c in ("cve_ice", "cve_or", "cve_actual", "ent_or", "upm_muestra")}
    base = pd.read_csv(BASE, dtype=tipos)
    dicc = pd.read_csv(DICC)
    assert base["index"].is_unique
    assert base[[Y_VAR, D_VAR, PESO, GRUPO_PLIEGUES, *CLUSTERS]].notna().all().all()
    return base, dicc


def matriz_x(base, dicc, quitar):
    """X con las nominales en dummies (más una dummy de faltante). Los NA de
    las numéricas se dejan como NaN: XGBoost y random forest los manejan de
    forma nativa; la regresión lineal imputa la mediana con indicador."""
    xp = dicc[dicc.rol == "X_principal"]
    xp = xp[~xp.variable.isin(quitar)]
    nominales = xp.loc[xp.tipo == "nominal", "variable"].tolist()
    x = base[xp.variable.tolist()].copy()
    for v in nominales:
        x[v] = x[v].astype("Int64").astype(str).replace("<NA>", np.nan)
    x = pd.get_dummies(x, columns=nominales, dummy_na=True, dtype=float)
    x = x.loc[:, x.nunique(dropna=False) > 1]   # dummies vacías de NA
    return x.astype(float)


def tratamiento(base):
    w = base[PESO].to_numpy()
    d = base[D_VAR].to_numpy()
    mu = np.average(d, weights=w)
    sd = np.sqrt(np.average((d - mu) ** 2, weights=w))
    return (d - mu) / sd, mu, sd


# ==========================================
# Aprendices con ajuste anidado
# ==========================================
def ecm(y, p, w):
    return float(np.average((y - p) ** 2, weights=w))


def ajustar_lineal(xtr, ytr, wtr, semilla):
    mod = make_pipeline(SimpleImputer(strategy="median", add_indicator=True),
                        LinearRegression())
    mod.fit(xtr, ytr, linearregression__sample_weight=wtr)
    return mod, {}


def ajustar_rf(xtr, ytr, wtr, gtr, semilla):
    internos = list(GroupKFold(n_splits=N_FOLDS_INTERNOS).split(xtr, ytr, gtr))
    mejor, mejor_ecm = None, np.inf
    for hp in REJILLA_RF:
        errores = []
        for a, b in internos:
            m = RandomForestRegressor(**RF_FIJOS, **hp, random_state=semilla)
            m.fit(xtr.iloc[a], ytr[a], sample_weight=wtr[a])
            errores.append(ecm(ytr[b], m.predict(xtr.iloc[b]), wtr[b]))
        if np.mean(errores) < mejor_ecm:
            mejor, mejor_ecm = hp, np.mean(errores)
    mod = RandomForestRegressor(**RF_FIJOS, **mejor, random_state=semilla)
    mod.fit(xtr, ytr, sample_weight=wtr)
    return mod, dict(mejor, ecm_interno=mejor_ecm)


def ajustar_xgb(xtr, ytr, wtr, gtr, semilla):
    internos = list(GroupKFold(n_splits=N_FOLDS_INTERNOS).split(xtr, ytr, gtr))
    mejor, mejor_ecm, mejor_arboles = None, np.inf, None
    for hp in REJILLA_XGB:
        errores, arboles = [], []
        for a, b in internos:
            m = XGBRegressor(**XGB_FIJOS, **hp, n_estimators=XGB_MAX_ARBOLES,
                             early_stopping_rounds=XGB_PARADA, random_state=semilla)
            m.fit(xtr.iloc[a], ytr[a], sample_weight=wtr[a],
                  eval_set=[(xtr.iloc[b], ytr[b])], sample_weight_eval_set=[wtr[b]],
                  verbose=False)
            arboles.append(m.best_iteration + 1)
            errores.append(ecm(ytr[b], m.predict(xtr.iloc[b],
                                                 iteration_range=(0, m.best_iteration + 1)),
                               wtr[b]))
        if np.mean(errores) < mejor_ecm:
            mejor, mejor_ecm, mejor_arboles = hp, np.mean(errores), int(np.mean(arboles))
    mod = XGBRegressor(**XGB_FIJOS, **mejor, n_estimators=mejor_arboles,
                       random_state=semilla)
    mod.fit(xtr, ytr, sample_weight=wtr, verbose=False)
    return mod, dict(mejor, n_estimators=mejor_arboles, ecm_interno=mejor_ecm)


def ajustar(aprendiz, xtr, ytr, wtr, gtr, semilla):
    if aprendiz == "lineal":
        return ajustar_lineal(xtr, ytr, wtr, semilla)
    if aprendiz == "rf":
        return ajustar_rf(xtr, ytr, wtr, gtr, semilla)
    return ajustar_xgb(xtr, ytr, wtr, gtr, semilla)


# ==========================================
# Etapa final: MCO ponderado y varianza agrupada
# ==========================================
def etapa_final(y_res, d_res, w, clusters, theta=None):
    """Score de partialling out con pesos: psi_i = w_i (y~_i - theta d~_i) d~_i.
    theta = sum(w d~ y~) / sum(w d~^2). Si se da theta (p. ej. 0 para la
    potencia), la varianza se evalúa en ese valor.

    Varianza agrupada: V = Omega / (sum w d~^2)^2, con
    Omega = c_A Omega_A + c_B Omega_B - c_AB Omega_AB (dos dimensiones; CGM 2011),
    Omega_G = sum_g (sum_{i en g} psi_i)^2 y c_G = G / (G - 1).
    Si la combinación en dos dimensiones no es positiva, se usa la mayor de
    las dos de una dimensión (y se marca)."""
    j = np.sum(w * d_res ** 2)
    est = np.sum(w * d_res * y_res) / j
    t = est if theta is None else theta
    psi = w * (y_res - t * d_res) * d_res

    def omega(g):
        s = pd.Series(psi).groupby(np.asarray(g)).sum().to_numpy()
        n_g = len(s)
        return n_g / (n_g - 1) * np.sum(s ** 2), n_g

    a, b = clusters
    om_a, g_a = omega(a)
    om_b, g_b = omega(b)
    om_ab, _ = omega(pd.Series(a).astype(str) + "|" + pd.Series(b).astype(str))
    om_2v = om_a + om_b - om_ab
    ajuste = om_2v <= 0
    if ajuste:
        om_2v = max(om_a, om_b)
    return dict(theta=est, se_2v=np.sqrt(om_2v) / j, se_mun=np.sqrt(om_a) / j,
                se_hc=np.sqrt(np.sum(psi ** 2)) / j, g_mun=g_a, g_upm=g_b,
                ajuste_2v=ajuste)


def agregar(thetas, ses):
    thetas, ses = np.asarray(thetas), np.asarray(ses)
    med = np.median(thetas)
    return med, np.sqrt(np.median(ses ** 2 + (thetas - med) ** 2))


# ==========================================
# Fase 1
# ==========================================
def fase1(n_rep, salida):
    base, dicc = cargar()
    d, mu_d, sd_d = tratamiento(base)
    y = base[Y_VAR].to_numpy(dtype=float)
    w = base[PESO].to_numpy(dtype=float)
    w = w / w.mean()
    grupos = base[GRUPO_PLIEGUES].to_numpy()
    estratos = base[ESTRATO_PLIEGUES].to_numpy()
    objetivos = {"m": y, "e": d}

    # Cada repetición se guarda al terminar (parciales/) y se reutiliza si el
    # proceso se interrumpe: una repetición depende solo de su semilla.
    parciales = salida / "parciales"
    parciales.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    for r in range(n_rep):
        if (parciales / f"preds_rep{r:02d}.csv.gz").exists():
            print(f"repetición {r + 1}/{n_rep}: ya estaba guardada", flush=True)
            continue
        pliegues, preds, hiper = [], [], []
        semilla = SEMILLA + r
        sgkf = StratifiedGroupKFold(n_splits=N_FOLDS, shuffle=True, random_state=semilla)
        particion = list(sgkf.split(np.zeros(len(y)), estratos, grupos))
        fold = np.empty(len(y), dtype=int)
        for k, (_, te) in enumerate(particion):
            fold[te] = k
        pliegues.append(pd.DataFrame({"index": base["index"], "rep": r, "fold": fold}))
        for espec, quitar in ESPECIFICACIONES.items():
            x = matriz_x(base, dicc, quitar)
            for nuis, obj in objetivos.items():
                for apr in APRENDICES:
                    oof = np.full(len(y), np.nan)
                    for k, (tr, te) in enumerate(particion):
                        mod, hp = ajustar(apr, x.iloc[tr], obj[tr], w[tr], grupos[tr],
                                          semilla * 10 + k)
                        oof[te] = mod.predict(x.iloc[te])
                        hiper.append(dict(rep=r, fold=k, espec=espec, nuisance=nuis,
                                          aprendiz=apr, **hp))
                    preds.append(pd.DataFrame({"index": base["index"], "rep": r,
                                               "espec": espec, "nuisance": nuis,
                                               "aprendiz": apr, "pred": oof}))
        pd.concat(pliegues).to_csv(parciales / f"pliegues_rep{r:02d}.csv.gz", index=False)
        pd.DataFrame(hiper).to_csv(parciales / f"hiper_rep{r:02d}.csv.gz", index=False)
        pd.concat(preds).to_csv(parciales / f"preds_rep{r:02d}.csv.gz", index=False)
        print(f"repetición {r + 1}/{n_rep} lista ({time.time() - t0:.0f} s)", flush=True)

    leer = lambda pref: pd.concat(pd.read_csv(parciales / f"{pref}_rep{r:02d}.csv.gz")
                                  for r in range(n_rep))
    pliegues, preds, hiper = leer("pliegues"), leer("preds"), leer("hiper")

    # Diagnóstico de las funciones auxiliares: R2 ponderado fuera de pliegue.
    diag = []
    for (espec, nuis, apr, r), g in preds.groupby(["espec", "nuisance", "aprendiz", "rep"]):
        obj = objetivos[nuis]
        e = ecm(obj, g.pred.to_numpy(), w)
        var = ecm(obj, np.average(obj, weights=w), w)
        diag.append(dict(espec=espec, nuisance=nuis, aprendiz=apr, rep=r,
                         ecm=e, r2=1 - e / var))
    diag = pd.DataFrame(diag)
    resumen = (diag.groupby(["espec", "nuisance", "aprendiz"])
               .agg(ecm=("ecm", "mean"), r2=("r2", "mean"), r2_min=("r2", "min"),
                    r2_max=("r2", "max")).reset_index())
    elegidos = (resumen.loc[resumen.groupby(["espec", "nuisance"]).ecm.idxmin(),
                            ["espec", "nuisance", "aprendiz"]])

    # Potencia: SE evaluado en beta = 0 (no usa beta) y efecto mínimo detectable.
    clusters = (base[CLUSTERS[0]].to_numpy(), base[CLUSTERS[1]].to_numpy())
    pot = []
    for espec in ESPECIFICACIONES:
        combos = {"elegido": tuple(elegidos.set_index(["espec", "nuisance"])
                                   .loc[(espec, n), "aprendiz"] for n in ("m", "e"))}
        combos.update({f"{a}/{a}": (a, a) for a in APRENDICES})
        for nombre, (am, ae) in combos.items():
            ses, var_d = [], []
            for r in range(n_rep):
                pm = preds.query("espec == @espec and rep == @r and nuisance == 'm' and aprendiz == @am").pred.to_numpy()
                pe = preds.query("espec == @espec and rep == @r and nuisance == 'e' and aprendiz == @ae").pred.to_numpy()
                res = etapa_final(y - pm, d - pe, w, clusters, theta=0.0)
                ses.append(res["se_2v"])
                var_d.append(np.average((d - pe) ** 2, weights=w))
            se0 = float(np.median(ses))
            pot.append(dict(espec=espec, combo=nombre, aprendiz_m=am, aprendiz_e=ae,
                            var_d_residual=float(np.median(var_d)),
                            se_beta0_2v=se0, efecto_minimo_detectable=Z_POTENCIA * se0))
    pot = pd.DataFrame(pot)

    salida.mkdir(parents=True, exist_ok=True)
    pliegues.to_csv(salida / "pliegues.csv.gz", index=False)
    preds.to_csv(salida / "predicciones_oof.csv.gz", index=False)
    hiper.to_csv(salida / "hiperparametros.csv", index=False)
    resumen.to_csv(salida / "diagnostico_nuisances.csv", index=False)
    elegidos.to_csv(salida / "aprendices_elegidos.csv", index=False)
    pot.to_csv(salida / "potencia.csv", index=False)
    json.dump(dict(n=len(y), n_rep=n_rep, n_folds=N_FOLDS, semilla=SEMILLA,
                   media_ice14=mu_d, de_ice14=sd_d,
                   n_x={e: matriz_x(base, dicc, q).shape[1] for e, q in ESPECIFICACIONES.items()},
                   python=sys.version, plataforma=platform.platform(),
                   numpy=np.__version__, pandas=pd.__version__,
                   sklearn=sklearn.__version__, xgboost=xgboost.__version__),
              open(salida / "entorno_fase1.json", "w"), indent=2)
    print(resumen.to_string(index=False))
    print(elegidos.to_string(index=False))
    print(pot.to_string(index=False))


# ==========================================
# Fase 2
# ==========================================
def fase2(salida):
    base, dicc = cargar()
    d, _, _ = tratamiento(base)
    y = base[Y_VAR].to_numpy(dtype=float)
    w = base[PESO].to_numpy(dtype=float)
    w = w / w.mean()
    clusters = (base[CLUSTERS[0]].to_numpy(), base[CLUSTERS[1]].to_numpy())
    preds = pd.read_csv(salida / "predicciones_oof.csv.gz")
    elegidos = pd.read_csv(salida / "aprendices_elegidos.csv").set_index(["espec", "nuisance"])
    n_rep = preds.rep.nunique()
    assert (preds.groupby(["espec", "nuisance", "aprendiz", "rep"])["index"]
            .apply(lambda s: (s.to_numpy() == base["index"].to_numpy()).all())).all()

    def pred(espec, nuis, apr, r):
        return preds.query("espec == @espec and nuisance == @nuis and aprendiz == @apr and rep == @r").pred.to_numpy()

    por_rep, est = [], []
    for espec in ESPECIFICACIONES:
        combos = {"elegido": (elegidos.loc[(espec, "m"), "aprendiz"],
                              elegidos.loc[(espec, "e"), "aprendiz"])}
        combos.update({f"{a}/{a}": (a, a) for a in APRENDICES})
        for nombre, (am, ae) in combos.items():
            filas = []
            for r in range(n_rep):
                res = etapa_final(y - pred(espec, "m", am, r), d - pred(espec, "e", ae, r),
                                  w, clusters)
                filas.append(dict(espec=espec, combo=nombre, rep=r, **res))
            f = pd.DataFrame(filas)
            por_rep.append(f)
            fila = dict(espec=espec, combo=nombre, aprendiz_m=am, aprendiz_e=ae, n_rep=n_rep)
            for tipo in ("2v", "mun", "hc"):
                th, se = agregar(f.theta, f[f"se_{tipo}"])
                fila.update({"beta": th, f"se_{tipo}": se})
            fila.update(ic95_inf=fila["beta"] - 1.959964 * fila["se_2v"],
                        ic95_sup=fila["beta"] + 1.959964 * fila["se_2v"],
                        z=fila["beta"] / fila["se_2v"],
                        reps_con_ajuste_2v=int(f.ajuste_2v.sum()),
                        g_mun=int(f.g_mun.iloc[0]), g_upm=int(f.g_upm.iloc[0]))
            est.append(fila)
    por_rep = pd.concat(por_rep)
    est = pd.DataFrame(est)

    # D20: proporción de la asociación total que sobrevive al control por escala.
    eleg = est[est.combo == "elegido"].set_index("espec")
    cociente = pd.DataFrame([dict(
        beta_principal=eleg.loc["principal", "beta"], beta_total=eleg.loc["total", "beta"],
        cociente=eleg.loc["principal", "beta"] / eleg.loc["total", "beta"])])

    validar_doubleml(base, y, d, preds, elegidos, salida)

    por_rep.to_csv(salida / "estimaciones_por_rep.csv", index=False)
    est.to_csv(salida / "estimaciones.csv", index=False)
    cociente.to_csv(salida / "cociente_escala.csv", index=False)
    print(est.to_string(index=False))
    print(cociente.to_string(index=False))


def validar_doubleml(base, y, d, preds, elegidos, salida):
    """Con pesos iguales a 1 y las mismas predicciones fuera de pliegue,
    beta y el SE heterocedástico calculados a mano deben coincidir con
    DoubleMLPLR (score 'partialling out', una repetición)."""
    import doubleml as dml
    from sklearn.base import clone

    pl = pd.read_csv(salida / "pliegues.csv.gz").query("rep == 0")
    assert (pl["index"].to_numpy() == base["index"].to_numpy()).all()
    folds = pl.fold.to_numpy()
    smpls = [[(np.where(folds != k)[0], np.where(folds == k)[0]) for k in range(N_FOLDS)]]
    filas = []
    for espec in ESPECIFICACIONES:
        am, ae = elegidos.loc[(espec, "m"), "aprendiz"], elegidos.loc[(espec, "e"), "aprendiz"]
        pm = preds.query("espec == @espec and nuisance == 'm' and aprendiz == @am and rep == 0").pred.to_numpy()
        pe = preds.query("espec == @espec and nuisance == 'e' and aprendiz == @ae and rep == 0").pred.to_numpy()
        datos = dml.DoubleMLData.from_arrays(np.zeros((len(y), 1)), y, d)
        obj = dml.DoubleMLPLR(datos, ml_l=clone(LinearRegression()), ml_m=clone(LinearRegression()),
                              n_folds=N_FOLDS, score="partialling out",
                              draw_sample_splitting=False)
        obj.set_sample_splitting(smpls)
        obj.fit(external_predictions={"d": {"ml_l": pm.reshape(-1, 1),
                                            "ml_m": pe.reshape(-1, 1)}})
        unos = np.ones(len(y))
        mano = etapa_final(y - pm, d - pe, unos, (np.arange(len(y)), np.arange(len(y))))
        filas.append(dict(espec=espec, beta_mano=mano["theta"], beta_doubleml=obj.coef[0],
                          se_hc_mano=mano["se_hc"], se_doubleml=obj.se[0],
                          dif_beta=abs(mano["theta"] - obj.coef[0]),
                          dif_se_rel=abs(mano["se_hc"] / obj.se[0] - 1)))
    val = pd.DataFrame(filas)
    val.to_csv(salida / "validacion_doubleml.csv", index=False)
    print(val.to_string(index=False))
    assert (val.dif_beta < 1e-10).all(), "beta a mano no coincide con DoubleML"
    assert (val.dif_se_rel < 1e-3).all(), "SE a mano no coincide con DoubleML"


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--fase", type=int, choices=[1, 2], required=True)
    ap.add_argument("--n-rep", type=int, default=N_REP)
    args = ap.parse_args()
    carpeta = "03_resultados" if args.n_rep == N_REP else "03_resultados_prueba"
    salida = RAIZ / "data" / "clean" / carpeta
    if args.fase == 1:
        fase1(args.n_rep, salida)
    else:
        fase2(salida)
