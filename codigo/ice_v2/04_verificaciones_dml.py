"""V2 — Módulo 04: verificaciones de la inferencia del DML con ICE V2 (D25).

Uso (desde la raíz del repositorio):  python codigo/ice_v2/04_verificaciones_dml.py

Las tres verificaciones usan las predicciones fuera de pliegue ya guardadas
(combinación elegida, 20 repeticiones) y sólo rehacen la etapa final; no
reajustan los nuisances. Lo que miden es la sensibilidad de la etapa final,
no la del ajuste completo.

1. Influencia por ZM: theta sin una unidad (ZM o municipio suelto) a la vez,
   mediana sobre repeticiones. Para comparar, V1 se recalcula quitando las
   mismas personas.
2. Descomposición del SE: SE = sqrt(Omega) / J, con J = sum w d~^2. Se separa
   la parte que viene de J (variación independiente del tratamiento) de la
   que viene de Omega (residuos del resultado y su correlación por grupo).
3. Wild cluster bootstrap restringido (WCR, H0: theta = 0), pesos de Webb a
   nivel del primer clúster (unidad de V2 o cve_ice en V1), estadístico t con
   la varianza en dos dimensiones de 03_dml.py. B = 9999 por repetición.

Salida: outputs/ice_v2/verificaciones/*.csv
"""
import importlib.util
import sys
from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("dml03", RAIZ / "codigo" / "modelo" / "03_dml.py")
M = importlib.util.module_from_spec(spec)
sys.modules["dml03"] = M
spec.loader.exec_module(M)

OUT = RAIZ / "outputs" / "ice_v2" / "verificaciones"
B = 9999
SEMILLA = 20261019
WEBB = np.array([-np.sqrt(1.5), -1, -np.sqrt(0.5), np.sqrt(0.5), 1, np.sqrt(1.5)])
# Resultados de V1: los de la corrida original (03_resultados), con la misma base.
CARPETAS = {"v1": RAIZ / "data" / "clean" / "03_resultados",
            "v2_zm2010": RAIZ / "data" / "clean" / "03_resultados_ice_v2_zm2010",
            "v2_zm2020": RAIZ / "data" / "clean" / "03_resultados_ice_v2_zm2020"}


def residuos(version):
    """y~, d~ de la combinación elegida por repetición, y lo necesario de la base."""
    M.configurar_ice(version)
    base, _ = M.cargar()
    d, _, _ = M.tratamiento(base)
    y = base[M.Y_VAR].to_numpy(float)
    w = base[M.PESO].to_numpy(float)
    w = w / w.mean()
    car = CARPETAS[version]
    eleg = pd.read_csv(car / "aprendices_elegidos.csv").set_index(["espec", "nuisance"]).aprendiz
    p = pd.read_csv(car / "predicciones_oof.csv.gz")
    out = {}
    for espec in M.ESPECIFICACIONES:
        ys, ds = [], []
        for r in sorted(p.rep.unique()):
            for nuis, dest, obs in (("m", ys, y), ("e", ds, d)):
                q = p[(p.espec == espec) & (p.nuisance == nuis) & (p.aprendiz == eleg[(espec, nuis)])
                      & (p.rep == r)]
                assert (q["index"].to_numpy() == base["index"].to_numpy()).all()
                dest.append(obs - q.pred.to_numpy())
        out[espec] = (np.array(ys), np.array(ds))
    cl = (base[M.CLUSTERS[0]].to_numpy(), base[M.CLUSTERS[1]].to_numpy())
    return base, w, cl, out


def influencia(base, w, cl, res, unidad, version, espec, top=None):
    ys, ds = res[espec]
    g = base[unidad].to_numpy()
    filas = []
    a_tot = (w * ds * ys).sum(1)
    j_tot = (w * ds ** 2).sum(1)
    sumas_a = pd.DataFrame((w * ds * ys).T).groupby(g).sum()
    sumas_j = pd.DataFrame((w * ds ** 2).T).groupby(g).sum()
    th_lo = (a_tot - sumas_a.to_numpy()) / (j_tot - sumas_j.to_numpy())   # unidades x reps
    full = np.median(a_tot / j_tot)
    t = pd.DataFrame({"unidad": sumas_a.index, "theta_sin": np.median(th_lo, 1)})
    t["cambio"] = t.theta_sin - full
    t["personas"] = t.unidad.map(pd.Series(g).value_counts())
    t = t.reindex(t.cambio.abs().sort_values(ascending=False).index)
    # SE sin la unidad para las de mayor influencia
    for u in t.unidad.head(top or 10):
        k = g != u
        r = [M.etapa_final(ys[i][k], ds[i][k], w[k], (cl[0][k], cl[1][k])) for i in range(len(ys))]
        th, se = M.agregar([x["theta"] for x in r], [x["se_2v"] for x in r])
        filas.append(dict(unidad=u, theta_sin_rehecho=th, se_2v_sin=se, z_sin=th / se))
    t = t.merge(pd.DataFrame(filas), on="unidad", how="left")
    t.insert(0, "espec", espec)
    t.insert(0, "version", version)
    t["theta_completo"] = full
    return t


def descomposicion(w, cl, res, version, espec):
    ys, ds = res[espec]
    filas = []
    for r in range(len(ys)):
        y_, d_ = ys[r], ds[r]
        e = M.etapa_final(y_, d_, w, cl)
        j = np.sum(w * d_ ** 2)
        th = e["theta"]
        u = y_ - th * d_
        psi = w * u * d_
        om_hc = np.sum(psi ** 2)
        om_2v = (e["se_2v"] * j) ** 2
        filas.append(dict(rep=r, theta=th, se_2v=e["se_2v"], J=j, omega_2v=om_2v, omega_hc=om_hc,
                          var_d_res=np.average(d_ ** 2, weights=w), var_y_res=np.average(u ** 2, weights=w),
                          efecto_diseno=om_2v / om_hc))
    f = pd.DataFrame(filas).median().drop("rep")
    f["version"], f["espec"] = version, espec
    return f


def wild(w, cl, res, version, espec, rng):
    """WCR con H0 theta=0: y* = v_g y~ (residuos restringidos = y~)."""
    ys, ds = res[espec]
    a = pd.Series(cl[0]).astype(str).to_numpy()
    b = pd.Series(cl[1]).astype(str).to_numpy()
    celda = pd.Series(a + "|" + b)
    cod_c, cel = pd.factorize(celda)
    ga = pd.factorize(pd.Series(cel).str.split("|").str[0])[0]
    gb = pd.factorize(pd.Series(cel).str.split("|").str[1])[0]
    na, nb, nc = ga.max() + 1, gb.max() + 1, len(cel)
    filas = []
    for r in range(len(ys)):
        y_, d_ = ys[r], ds[r]
        e = M.etapa_final(y_, d_, w, cl)
        t_obs = e["theta"] / e["se_2v"]
        j = np.sum(w * d_ ** 2)
        s_c = np.bincount(cod_c, w * d_ * y_, nc)       # score en theta=0 por celda
        d_c = np.bincount(cod_c, w * d_ ** 2, nc)
        v = WEBB[rng.integers(0, 6, size=(na, B))][ga]  # celdas x B, constante por clúster A
        sv = s_c[:, None] * v
        th_b = sv.sum(0) / j
        psi_c = sv - th_b[None, :] * d_c[:, None]       # suma del score por celda

        def om(idx, n):
            s = np.zeros((n, B))
            np.add.at(s, idx, psi_c)
            return n / (n - 1) * (s ** 2).sum(0)
        o = om(ga, na) + om(gb, nb) - om(np.arange(nc), nc)
        o = np.where(o > 0, o, np.maximum(om(ga, na), om(gb, nb)))
        t_b = th_b / (np.sqrt(o) / j)
        filas.append(dict(rep=r, t=t_obs, p_normal=2 * (1 - _phi(abs(t_obs))),
                          p_wild=np.mean(np.abs(t_b) >= abs(t_obs))))
    f = pd.DataFrame(filas)
    return dict(version=version, espec=espec, t_mediana=f.t.median(),
                p_normal_mediana=f.p_normal.median(), p_wild_mediana=f.p_wild.median(),
                p_wild_min=f.p_wild.min(), p_wild_max=f.p_wild.max(), B=B, reps=len(f))


def _phi(x):
    from math import erf, sqrt
    return 0.5 * (1 + erf(x / sqrt(2)))


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(SEMILLA)
    datos = {v: residuos(v) for v in CARPETAS}
    inf, dec, wb = [], [], []
    for v, (base, w, cl, res) in datos.items():
        for espec in ("principal", "total"):
            dec.append(descomposicion(w, cl, res, v, espec))
            wb.append(wild(w, cl, res, v, espec, rng))
            unidades = ["unidad_zm2010", "unidad_zm2020"] if v == "v1" else [M.VERSIONES_ICE[v]["grupo"]]
            for u in unidades:
                t = influencia(base, w, cl, res, u, v, espec)
                t.insert(2, "unidad_quitada", u)
                inf.append(t)
    inf = pd.concat(inf)
    dec = pd.DataFrame(dec)
    wb = pd.DataFrame(wb)
    inf.to_csv(OUT / "influencia_por_unidad.csv", index=False)
    dec.to_csv(OUT / "descomposicion_se.csv", index=False)
    wb.to_csv(OUT / "wild_cluster_bootstrap.csv", index=False)
    pd.set_option("display.width", 200)
    print(dec.to_string())
    print(wb.to_string())
    for (v, e, u), g in inf.groupby(["version", "espec", "unidad_quitada"], sort=False):
        print(f"\n== {v} {e} quitando {u}")
        print(g.head(8).drop(columns=["version", "espec", "unidad_quitada"]).to_string(index=False))


if __name__ == "__main__":
    main()
