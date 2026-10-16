"""04_supresion_influencia.py: diagnóstico de supresión e influencia del DML.

Proyecto: Movilidad social y complejidad económica (ESRU-EMOVI 2023).

Motivación (fase 2 de 03_dml.py): el beta condicional a la escala (5.09) es
4.2 veces el total (1.21) y el ICE residual conserva solo 14% de la varianza
del ICE. Este script no cambia la especificación principal; describe de dónde
sale beta.

A. Supresión
  A1. Modelo parcialmente lineal con dos regresores lineales:
        Y = g(X sin escala) + b_D * ICE + g_P * log_pob14 + u
      Reutiliza Y~ y D~ de la especificación total y ajusta una sola función
      auxiliar nueva, p(X) = E[log_pob14 | X sin escala], con XGBoost, los
      mismos pliegues, semillas y rejilla de 03_dml.py. Da el coeficiente de
      la escala condicional al ICE (g_P) y la descomposición exacta, en la
      muestra, del beta total:
        b_total = b_D + g_P * delta,  delta = coef. de P~ sobre D~ (total).
  A2. Distribución del ICE residual (especificación principal) por tamaño de
      municipio (categorías de Soloaga): varianza, peso en el denominador de
      beta (sum w D~^2) y beta dentro de cada categoría.

B. Influencia (funciones auxiliares fijas; solo se recalcula la etapa final)
  B1. Excluir un estado de origen a la vez (32).
  B2. Excluir el 1% y el 5% de municipios con |D~| medio más alto
      (especificación principal; misma exclusión en ambas especificaciones).
  B3. DFBETA exacto por municipio: beta sin el municipio g, con las mismas
      predicciones fuera de pliegue.
  Limitación: las funciones auxiliares se ajustaron con toda la muestra. B
  mide cuánto pesa cada grupo en la etapa final, no cómo cambiaría el ajuste
  de m(X) y e(X) sin él.

Uso (desde la raíz del proyecto):
  python codigo/modelo/04_supresion_influencia.py

Insumos:  data/clean/02_base_dml.csv y data/clean/03_resultados/
          (predicciones_oof.csv.gz, pliegues.csv.gz, aprendices_elegidos.csv)
Salidas:  data/clean/04_resultados/
"""
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
SALIDA = RAIZ / "data" / "clean" / "04_resultados"
ESCALA = "log_pob14"
TAMANO = "tam_soloaga14"
ESTADO = "ent_or"
CORTES_ATIPICOS = (0.01, 0.05)   # fracción de municipios con |D~| más alto
N_DFBETA = 15                    # municipios más influyentes que se reportan
Z = 1.959964


# ==========================================
# Etapa final con varios regresores
# ==========================================
def mco_agrupado(y_res, x_res, w, clusters):
    """MCO ponderado sin constante de y~ sobre las columnas de x~ y varianza
    agrupada en dos dimensiones (CGM 2011), igual que etapa_final de 03_dml.py
    pero con k regresores. Si la matriz en dos dimensiones no es definida
    positiva, se usa la de municipio (y se marca)."""
    x_res = np.column_stack(x_res)
    j = (x_res * w[:, None]).T @ x_res
    coef = np.linalg.solve(j, (x_res * w[:, None]).T @ y_res)
    psi = (w * (y_res - x_res @ coef))[:, None] * x_res

    def omega(g):
        s = pd.DataFrame(psi).groupby(np.asarray(g)).sum().to_numpy()
        return len(s) / (len(s) - 1) * s.T @ s

    a, b = clusters
    om = omega(a) + omega(b) - omega(pd.Series(a).astype(str) + "|" + pd.Series(b).astype(str))
    ajuste = np.linalg.eigvalsh(om).min() <= 0
    if ajuste:
        om = omega(a)
    jinv = np.linalg.inv(j)
    v = jinv @ om @ jinv
    return coef, np.sqrt(np.diag(v)), ajuste


def resumir(f, extra):
    th, se = dml03.agregar(f.theta, f.se_2v)
    return dict(**extra, beta=th, se_2v=se, ic95_inf=th - Z * se, ic95_sup=th + Z * se,
                p=float(2 * norm.sf(abs(th / se))),
                beta_min_rep=f.theta.min(), beta_max_rep=f.theta.max())


# ==========================================
# A1. Función auxiliar de la escala
# ==========================================
def ajustar_escala(base, dicc, pliegues, w, n_rep):
    """p(X) = E[log_pob14 | X sin escala] con XGBoost (el aprendiz elegido
    para e(X) en ambas especificaciones), mismos pliegues y semillas."""
    x = dml03.matriz_x(base, dicc, dml03.ESPECIFICACIONES["total"])
    assert ESCALA not in x.columns
    p = base[ESCALA].to_numpy(dtype=float)
    grupos = base[dml03.GRUPO_PLIEGUES].to_numpy()
    parciales = SALIDA / "parciales"
    parciales.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    for r in range(n_rep):
        archivo = parciales / f"pred_escala_rep{r:02d}.csv.gz"
        if archivo.exists():
            continue
        fold = pliegues.query("rep == @r").fold.to_numpy()
        oof, hiper = np.full(len(p), np.nan), []
        for k in range(dml03.N_FOLDS):
            tr, te = np.where(fold != k)[0], np.where(fold == k)[0]
            mod, hp = dml03.ajustar("xgb", x.iloc[tr], p[tr], w[tr], grupos[tr],
                                    (dml03.SEMILLA + r) * 10 + k)
            oof[te] = mod.predict(x.iloc[te])
            hiper.append(dict(rep=r, fold=k, **hp))
        pd.DataFrame({"index": base["index"], "rep": r, "pred": oof}).to_csv(archivo, index=False)
        pd.DataFrame(hiper).to_csv(parciales / f"hiper_escala_rep{r:02d}.csv.gz", index=False)
        print(f"escala: repetición {r + 1}/{n_rep} lista ({time.time() - t0:.0f} s)", flush=True)
    preds = pd.concat(pd.read_csv(parciales / f"pred_escala_rep{r:02d}.csv.gz")
                      for r in range(n_rep))
    hiper = pd.concat(pd.read_csv(parciales / f"hiper_escala_rep{r:02d}.csv.gz")
                      for r in range(n_rep))
    return preds, hiper


# ==========================================
# Principal
# ==========================================
def main():
    base, dicc = dml03.cargar()
    d, _, _ = dml03.tratamiento(base)
    y = base[dml03.Y_VAR].to_numpy(dtype=float)
    w = base[dml03.PESO].to_numpy(dtype=float)
    w = w / w.mean()
    mun = base[dml03.CLUSTERS[0]].to_numpy()
    upm = base[dml03.CLUSTERS[1]].to_numpy()
    estado = base[ESTADO].to_numpy()
    p_escala = base[ESCALA].to_numpy(dtype=float)

    preds = pd.read_csv(ENTRADA / "predicciones_oof.csv.gz")
    pliegues = pd.read_csv(ENTRADA / "pliegues.csv.gz")
    elegidos = pd.read_csv(ENTRADA / "aprendices_elegidos.csv").set_index(["espec", "nuisance"])
    n_rep = preds.rep.nunique()
    for r in range(n_rep):
        assert (pliegues.query("rep == @r")["index"].to_numpy() == base["index"].to_numpy()).all()

    def res(espec, r):
        am = elegidos.loc[(espec, "m"), "aprendiz"]
        ae = elegidos.loc[(espec, "e"), "aprendiz"]
        q = preds.query("espec == @espec and rep == @r")
        pm = q.query("nuisance == 'm' and aprendiz == @am")
        pe = q.query("nuisance == 'e' and aprendiz == @ae")
        assert (pm["index"].to_numpy() == base["index"].to_numpy()).all()
        return y - pm.pred.to_numpy(), d - pe.pred.to_numpy()

    residuos = {(e, r): res(e, r) for e in dml03.ESPECIFICACIONES for r in range(n_rep)}
    SALIDA.mkdir(parents=True, exist_ok=True)

    # Comprobación: con todas las observaciones se reproduce la fase 2.
    est03 = pd.read_csv(ENTRADA / "estimaciones.csv").query("combo == 'elegido'").set_index("espec")
    for espec in dml03.ESPECIFICACIONES:
        f = pd.DataFrame([dml03.etapa_final(*residuos[(espec, r)], w, (mun, upm))
                          for r in range(n_rep)])
        th, se = dml03.agregar(f.theta, f.se_2v)
        assert abs(th - est03.loc[espec, "beta"]) < 1e-9 and abs(se - est03.loc[espec, "se_2v"]) < 1e-9

    # ---------- A1. Escala condicional al ICE ----------
    pred_p, hiper_p = ajustar_escala(base, dicc, pliegues, w, n_rep)
    sd_p = np.sqrt(np.average((p_escala - np.average(p_escala, weights=w)) ** 2, weights=w))
    filas, r2_p = [], []
    for r in range(n_rep):
        pr = pred_p.query("rep == @r")
        assert (pr["index"].to_numpy() == base["index"].to_numpy()).all()
        p_res = p_escala - pr.pred.to_numpy()
        r2_p.append(1 - np.average(p_res ** 2, weights=w)
                    / np.average((p_escala - np.average(p_escala, weights=w)) ** 2, weights=w))
        y_t, d_t = residuos[("total", r)]
        coef, se, ajuste = mco_agrupado(y_t, [d_t, p_res], w, (mun, upm))
        b_total = np.sum(w * d_t * y_t) / np.sum(w * d_t ** 2)
        delta = np.sum(w * d_t * p_res) / np.sum(w * d_t ** 2)
        assert abs(b_total - (coef[0] + coef[1] * delta)) < 1e-8   # identidad de omisión
        filas.append(dict(rep=r, b_ice=coef[0], se_ice=se[0], g_escala=coef[1],
                          se_escala=se[1], delta=delta, b_total=b_total,
                          r2_escala=r2_p[-1], ajuste_2v=ajuste))
    a1_rep = pd.DataFrame(filas)
    a1 = []
    for nombre, col, se_col, factor in (
            ("ICE | escala (b_D)", "b_ice", "se_ice", 1.0),
            ("Escala | ICE, por 1 log de población (g_P)", "g_escala", "se_escala", 1.0),
            ("Escala | ICE, por 1 DE de log población", "g_escala", "se_escala", sd_p)):
        f = pd.DataFrame({"theta": a1_rep[col] * factor, "se_2v": a1_rep[se_col] * factor})
        a1.append(resumir(f, dict(termino=nombre)))
    a1 = pd.DataFrame(a1)
    descomp = pd.DataFrame([dict(
        b_total=np.median(a1_rep.b_total), b_ice_dado_escala=np.median(a1_rep.b_ice),
        g_escala=np.median(a1_rep.g_escala), delta=np.median(a1_rep.delta),
        sesgo_omision=np.median(a1_rep.g_escala * a1_rep.delta),
        de_log_pob14=sd_p, r2_escala_media=np.mean(r2_p))])

    # ---------- A2. ICE residual por tamaño de municipio ----------
    a2 = []
    for espec in dml03.ESPECIFICACIONES:
        for cat in ["<15mil", "15-50mil", "50-350mil", ">=350mil", "todas"]:
            sel = np.ones(len(y), bool) if cat == "todas" else (base[TAMANO] == cat).to_numpy()
            fil, var, peso_den, peso_num = [], [], [], []
            for r in range(n_rep):
                y_r, d_r = residuos[(espec, r)]
                var.append(np.average(d_r[sel] ** 2, weights=w[sel]))
                peso_den.append(np.sum((w * d_r ** 2)[sel]) / np.sum(w * d_r ** 2))
                fil.append(dml03.etapa_final(y_r[sel], d_r[sel], w[sel], (mun[sel], upm[sel])))
            f = pd.DataFrame(fil)
            a2.append(resumir(f, dict(espec=espec, tamano=cat, n=int(sel.sum()),
                                      n_mun=int(pd.Series(mun[sel]).nunique()),
                                      pct_peso_muestral=100 * w[sel].sum() / w.sum(),
                                      var_d_residual=np.median(var),
                                      pct_denominador=100 * np.median(peso_den))))
    a2 = pd.DataFrame(a2)

    # ---------- B. Influencia ----------
    def beta_sin(excluir):
        out = []
        for espec in dml03.ESPECIFICACIONES:
            keep = ~excluir
            f = pd.DataFrame([dml03.etapa_final(*(v[keep] for v in residuos[(espec, r)]),
                                                w[keep], (mun[keep], upm[keep]))
                              for r in range(n_rep)])
            out.append(resumir(f, dict(espec=espec, n=int(keep.sum()),
                                       n_mun=int(pd.Series(mun[keep]).nunique()))))
        return out

    b1 = []
    for e in sorted(pd.unique(estado)):
        for fila in beta_sin(estado == e):
            b1.append(dict(estado_excluido=e, n_excluidos=int((estado == e).sum()), **fila))
    b1 = pd.DataFrame(b1)

    # |D~| medio por municipio (principal), promedio de repeticiones.
    abs_d = np.mean([np.abs(residuos[("principal", r)][1]) for r in range(n_rep)], axis=0)
    por_mun = (pd.DataFrame({"mun": mun, "abs_d": abs_d, "w": w})
               .assign(wd=lambda t: t.abs_d * t.w).groupby("mun")
               .agg(wd=("wd", "sum"), w=("w", "sum"), n=("w", "size")))
    por_mun["abs_d_medio"] = por_mun.wd / por_mun.w
    b2 = []
    for corte in CORTES_ATIPICOS:
        k = int(np.ceil(corte * len(por_mun)))
        fuera = por_mun.abs_d_medio.nlargest(k).index
        excl = np.isin(mun, fuera)
        for fila in beta_sin(excl):
            b2.append(dict(corte=corte, mun_excluidos=k, n_excluidos=int(excl.sum()),
                           municipios=" ".join(sorted(fuera)), **fila))
    b2 = pd.DataFrame(b2)

    # DFBETA exacto por municipio (mediana de repeticiones).
    b3 = []
    for espec in dml03.ESPECIFICACIONES:
        th_sin = []
        for r in range(n_rep):
            y_r, d_r = residuos[(espec, r)]
            t = pd.DataFrame({"mun": mun, "num": w * d_r * y_r, "den": w * d_r ** 2})
            g = t.groupby("mun")[["num", "den"]].sum()
            th_sin.append((t.num.sum() - g.num) / (t.den.sum() - g.den))
        th_sin = pd.concat(th_sin, axis=1).median(axis=1)
        th_todo = est03.loc[espec, "beta"]
        info = (base.copy().assign(w=w, d_med=np.mean([residuos[(espec, r)][1] for r in range(n_rep)], axis=0))
                .groupby(dml03.CLUSTERS[0])
                .agg(estado=(ESTADO, "first"), n=("w", "size"), log_pob14=(ESCALA, "mean"),
                     tamano=(TAMANO, "first"), ice14=(dml03.D_VAR, "mean"),
                     d_residual_medio=("d_med", "mean")))
        g = pd.DataFrame({"beta_sin_mun": th_sin, "cambio": th_sin - th_todo}).join(info)
        g["espec"] = espec
        b3.append(g.reindex(g.cambio.abs().sort_values(ascending=False).index).head(N_DFBETA)
                  .reset_index(names="cve_ice"))
    b3 = pd.concat(b3)

    # ---------- Salidas ----------
    a1.to_csv(SALIDA / "a1_escala_condicional.csv", index=False)
    a1_rep.to_csv(SALIDA / "a1_por_rep.csv", index=False)
    descomp.to_csv(SALIDA / "a1_descomposicion.csv", index=False)
    hiper_p.to_csv(SALIDA / "a1_hiperparametros_escala.csv", index=False)
    a2.to_csv(SALIDA / "a2_por_tamano.csv", index=False)
    b1.to_csv(SALIDA / "b1_sin_estado.csv", index=False)
    b2.to_csv(SALIDA / "b2_sin_atipicos.csv", index=False)
    b3.to_csv(SALIDA / "b3_dfbeta_municipios.csv", index=False)
    import scipy, xgboost, sklearn
    json.dump(dict(n=len(y), n_rep=n_rep, python=sys.version, plataforma=platform.platform(),
                   numpy=np.__version__, pandas=pd.__version__, scipy=scipy.__version__,
                   sklearn=sklearn.__version__, xgboost=xgboost.__version__),
              open(SALIDA / "entorno_04.json", "w"), indent=2)
    pd.set_option("display.width", 250)
    for nombre, t in (("A1", a1), ("descomposición", descomp), ("A2", a2), ("B1", b1),
                      ("B2", b2.drop(columns="municipios")), ("B3", b3)):
        print(f"\n== {nombre} ==\n{t.to_string(index=False)}")


if __name__ == "__main__":
    main()
