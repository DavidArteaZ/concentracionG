"""Módulo 06 — Validación externa del ICE y control de escala (A3, A4).

Validador principal (medido, no modelado): totales municipales de los Censos
Económicos, en log relativo al promedio nacional del año:
  log_rem_rel     = log(remuneraciones / personal remunerado) - log(nacional)
  log_vacb_po_rel = log(VACB / personal ocupado) - log(nacional)
Niveles, por año:  y = b*ICE + g1*log(UE) + g2*log(pob) + d*diversidad + FE_estado
  (1) ICE; (2) + escala; (3) + diversidad; (4) + FE de estado.
Crecimiento: dy(t->t+5) = b*ICE_t + th*y_t + escala_t + FE_estado (+ FE periodo).
Inferencia: CRV1 por estado; p-valor wild cluster restringido (Webb, B=9,999);
Conley (100 km, kernel uniforme) como robustez.
Regla Rama vs. Clase (fijada antes de correr): R2 parcial del ICE en (4) con
log_rem_rel de 2003 y 2013; Clase solo si el IC 95% bootstrap por estado de
(Clase - Rama) excluye el cero a favor de Clase en ambos años.
PIB (Kummu et al., 2025): solo descriptivo, sin FE de estado.
Salidas: outputs/ice/validacion_niveles.csv, validacion_crecimiento.csv,
         rama_vs_clase.csv, descriptivo_pib_kummu.csv
"""
import numpy as np
import pandas as pd

from . import config as C
from .utils import Log, asegurar_dirs, poblacion_censal

RNG = np.random.default_rng(C.SEED)
WEBB = np.array([-np.sqrt(1.5), -1, -np.sqrt(0.5), np.sqrt(0.5), 1, np.sqrt(1.5)])


def diseno(df, cols, fe=None):
    X = [np.ones(len(df))] + [df[c].to_numpy(float) for c in cols]
    names = ["const"] + list(cols)
    for f in (fe or []):
        d = pd.get_dummies(df[f], drop_first=True, dtype=float)
        X += [d[c].to_numpy() for c in d.columns]
        names += [f"{f}_{c}" for c in d.columns]
    return np.column_stack(X), names


def ols(y, X):
    XtX_inv = np.linalg.pinv(X.T @ X)
    A = XtX_inv @ X.T
    b = A @ y
    e = y - X @ b
    return b, e, A


def crv1(A_j, e, g):
    """Varianza CRV1 de un coeficiente (A_j = fila j de (X'X)^-1 X')."""
    n, G = len(e), len(np.unique(g))
    s = pd.Series(A_j * e).groupby(g).sum().to_numpy()
    return s @ s * G / (G - 1)


def wild_p(y, X, j, g, t_obs, B=C.B_WILD):
    """p-valor del wild cluster bootstrap restringido (H0: b_j = 0), pesos de Webb."""
    Xr = np.delete(X, j, axis=1)
    br, er, _ = ols(y, Xr)
    yr = Xr @ br
    _, _, A = ols(y, X)
    gi, ginv = np.unique(g, return_inverse=True)
    G, n, k = len(gi), len(y), X.shape[1]
    c = G / (G - 1)
    t_star = []
    for b0 in range(0, B, 1000):
        bb = min(1000, B - b0)
        W = WEBB[RNG.integers(0, 6, size=(G, bb))][ginv]  # n x bb
        Ys = yr[:, None] + er[:, None] * W
        Bs = A @ Ys
        Es = Ys - X @ Bs
        S = np.zeros((G, bb))
        np.add.at(S, ginv, A[j][:, None] * Es)
        se = np.sqrt(c * (S ** 2).sum(0))
        t_star.append(Bs[j] / se)
    t_star = np.concatenate(t_star)
    return (np.abs(t_star) >= abs(t_obs)).mean()


def conley_se(A_j, e, lat, lon, km=C.CONLEY_KM):
    la, lo = np.deg2rad(lat), np.deg2rad(lon)
    d = 6371 * np.arccos(np.clip(np.sin(la)[:, None] * np.sin(la)[None, :] +
                                 np.cos(la)[:, None] * np.cos(la)[None, :] *
                                 np.cos(lo[:, None] - lo[None, :]), -1, 1))
    s = A_j * e
    return np.sqrt(s @ ((d <= km) @ s))


def estimar(df, y, cols, fe, cluster="ent", conley=True, wild=True):
    X, names = diseno(df, cols, fe)
    yv = df[y].to_numpy(float)
    b, e, A = ols(yv, X)
    j = names.index("ice")
    se = np.sqrt(crv1(A[j], e, df[cluster].to_numpy()))
    Xr = np.delete(X, j, axis=1)
    _, er, _ = ols(yv, Xr)
    out = {"beta_ice": b[j], "se_crv1": se, "t": b[j] / se, "n": len(yv),
           "r2": 1 - (e @ e) / ((yv - yv.mean()) @ (yv - yv.mean())),
           "r2_parcial_ice": 1 - (e @ e) / (er @ er)}
    if wild:
        out["p_wild_cluster"] = wild_p(yv, X, j, df[cluster].to_numpy(), out["t"])
    if conley:
        out["se_conley_100km"] = conley_se(A[j], e, df.lat.to_numpy(), df.lon.to_numpy())
    for c in cols:
        if c != "ice":
            out[f"beta_{c}"] = b[names.index(c)]
    return out


ESPEC = {"(1) ICE": ([], None), "(2) + escala": (["log_ue", "log_pob"], None),
         "(3) + diversidad": (["log_ue", "log_pob", "diversidad"], None),
         "(4) + FE estado": (["log_ue", "log_pob", "diversidad"], ["ent"])}


def r2_parcial(df, y):
    X, names = diseno(df, ["ice", "log_ue", "log_pob", "diversidad"], ["ent_b"])
    yv = df[y].to_numpy(float)
    _, e, _ = ols(yv, X)
    _, er, _ = ols(yv, np.delete(X, names.index("ice"), axis=1))
    return 1 - (e @ e) / (er @ er)


def main():
    asegurar_dirs()
    log = Log("06_validacion_externa")
    ice = pd.read_csv(C.CLEAN / "ice_municipal.csv", dtype={"cve_mun": str})
    ice = ice[ice.especificacion == "base"]
    alt = pd.read_csv(C.CLEAN / "ice_alternativas.csv.gz", dtype={"cve_mun": str})
    tot = pd.read_csv(C.CLEAN / "saic_totales_limpio.csv", dtype={"cve_mun": str})
    pob = poblacion_censal()
    cen = pd.read_csv(C.CLEAN / "centroides_municipales.csv", dtype={"cve_mun": str})
    df = (ice.merge(tot[["anio", "cve_mun", "log_rem_rel", "log_vacb_po_rel"]], on=["anio", "cve_mun"], how="left")
          .merge(pob, on=["anio", "cve_mun"], how="left").merge(cen, on="cve_mun", how="left"))
    df["log_ue"] = np.log(df.ue_total)
    df["ent"] = df.cve_mun.str[:2]
    log(f"Municipio-año: {len(df):,}; sin población: {df.log_pob.isna().sum()}; "
        f"sin centroide: {df.lat.isna().sum()}; sin remuneración media: {df.log_rem_rel.isna().sum()}; "
        f"sin productividad: {df.log_vacb_po_rel.isna().sum()}")
    falt = df[df.log_rem_rel.isna()]
    log(f"Los municipios sin remuneración media tienen mediana de {falt.ue_total.median():.0f} UE "
        f"vs. {df[df.log_rem_rel.notna()].ue_total.median():.0f} del resto; "
        f"{100*(~falt.en_nucleo).mean():.0f}% están fuera del núcleo.")

    # --------------------------------------------------------- niveles
    filas = []
    for y in ["log_rem_rel", "log_vacb_po_rel"]:
        for a in C.ANIOS:
            d = df[df.anio == a].dropna(subset=[y, "ice", "log_ue", "log_pob", "diversidad", "lat"])
            for nom, (ctrl, fe) in ESPEC.items():
                r = estimar(d, y, ["ice"] + ctrl, fe)
                r.update({"dependiente": y, "anio": a, "columna": nom})
                filas.append(r)
            log(f"[{y} {a}] n={len(d)} | " + " | ".join(
                f"{f['columna'][:3]} b={f['beta_ice']:.3f} (se {f['se_crv1']:.3f}, p_w {f['p_wild_cluster']:.4f}, "
                f"R2p {f['r2_parcial_ice']:.3f})" for f in filas[-4:]))
    niv = pd.DataFrame(filas)
    niv.to_csv(C.OUT / "validacion_niveles.csv", index=False)

    # --------------------------------------------------------- crecimiento
    filas = []
    w = df.set_index(["cve_mun", "anio"])
    for y in ["log_rem_rel", "log_vacb_po_rel"]:
        pares = [(2003, 2008), (2008, 2013), (2013, 2018), (2018, 2023)]
        apil = []
        for t0, t1 in pares + [(2003, 2023)]:
            d0 = df[df.anio == t0].set_index("cve_mun")
            d1 = df[df.anio == t1].set_index("cve_mun")
            d = d0[["ice", "log_ue", "log_pob", "diversidad", "ent", "lat", "lon", y]].join(
                d1[[y]], rsuffix="_t1", how="inner").dropna()
            d["dy"] = d[f"{y}_t1"] - d[y]
            d["y0"] = d[y]
            d["periodo"] = f"{t0}-{t1}"
            if (t0, t1) == (2003, 2023):
                for nom, ctrl in [("(a) ICE + y0", ["y0"]),
                                  ("(b) + escala + diversidad + FE estado", ["y0", "log_ue", "log_pob", "diversidad"])]:
                    r = estimar(d.reset_index(), "dy", ["ice"] + ctrl, ["ent"] if "(b)" in nom else None)
                    r.update({"dependiente": y, "periodo": "2003-2023", "columna": nom})
                    filas.append(r)
            else:
                apil.append(d.reset_index())
        p = pd.concat(apil, ignore_index=True)
        for nom, ctrl, fe in [("(a) ICE + y0 + FE periodo", ["y0"], ["periodo"]),
                              ("(b) + escala + diversidad + FE estado y periodo",
                               ["y0", "log_ue", "log_pob", "diversidad"], ["ent", "periodo"])]:
            r = estimar(p, "dy", ["ice"] + ctrl, fe, conley=False)
            r.update({"dependiente": y, "periodo": "apilado 5 años", "columna": nom})
            filas.append(r)
    cre = pd.DataFrame(filas)
    cre.to_csv(C.OUT / "validacion_crecimiento.csv", index=False)
    pd.set_option("display.width", 220)
    log("\nCrecimiento:\n" + cre[["dependiente", "periodo", "columna", "beta_ice", "se_crv1",
                                  "p_wild_cluster", "r2_parcial_ice", "n"]].round(4).to_string(index=False))

    # --------------------------------------------------------- Rama vs. Clase
    cl = alt[alt.especificacion == "clase"][["anio", "cve_mun", "ice"]].rename(columns={"ice": "ice_clase"})
    filas = []
    for a in [2003, 2013]:
        d = df[df.anio == a].merge(cl, on=["anio", "cve_mun"]).dropna(
            subset=["log_rem_rel", "ice", "ice_clase", "log_ue", "log_pob", "diversidad"])
        d = d.reset_index(drop=True)
        d["ent_b"] = d.ent
        def dif(dd):
            r_r = r2_parcial(dd, "log_rem_rel")
            r_c = r2_parcial(dd.assign(ice=dd.ice_clase), "log_rem_rel")
            return r_r, r_c
        r_r, r_c = dif(d)
        ents = d.ent.unique()
        grupos = {e: d.index[d.ent == e].to_numpy() for e in ents}
        boot = []
        for b in range(C.B_PAIRS):
            sel = RNG.choice(ents, size=len(ents), replace=True)
            idx = np.concatenate([grupos[e] for e in sel])
            dd = d.loc[idx].copy()
            dd["ent_b"] = np.repeat(np.arange(len(sel)), [len(grupos[e]) for e in sel]).astype(str)
            rr, rc = dif(dd.reset_index(drop=True))
            boot.append(rc - rr)
        lo, hi = np.percentile(boot, [2.5, 97.5])
        filas.append({"anio": a, "n": len(d), "r2p_rama": r_r, "r2p_clase": r_c,
                      "dif_clase_menos_rama": r_c - r_r, "ic95_inf": lo, "ic95_sup": hi,
                      "clase_gana": lo > 0})
    rvc = pd.DataFrame(filas)
    rvc.to_csv(C.OUT / "rama_vs_clase.csv", index=False)
    decision = "Clase" if rvc.clase_gana.all() else "Rama"
    log("\nRegla Rama vs. Clase (R2 parcial del ICE, col. 4, log_rem_rel):\n" + rvc.round(4).to_string(index=False))
    log(f"Decisión según la regla fijada: especificación base = {decision}")

    # --------------------------------------------------------- PIB (descriptivo)
    cw = pd.read_csv(C.CLEAN / "crosswalk_gadm_inegi.csv", dtype={"cve_mun": str})
    gdp = pd.read_csv(C.GDP)
    cw = cw[cw.tipo_relacion == "1:1"].merge(gdp, on="GID_2")
    filas = []
    for a in C.ANIOS:
        col = str(min(a, 2022))
        d = df[df.anio == a].merge(cw[["cve_mun", col]], on="cve_mun").dropna(
            subset=["ice", "log_ue", "log_pob", "lat"])
        d["log_pib_pc"] = np.log(d[col])
        r = estimar(d, "log_pib_pc", ["ice", "log_ue", "log_pob"], None, wild=False)
        r.update({"anio": a, "anio_pib": int(col), "corr_ice_logpib": d.ice.corr(d.log_pib_pc),
                  "nota": "PIB municipal modelado (urbanización y tiempo de viaje); sin FE de estado; "
                          "no se usa para A3"})
        filas.append(r)
    pib = pd.DataFrame(filas)
    pib.to_csv(C.OUT / "descriptivo_pib_kummu.csv", index=False)
    log("\nPIB Kummu (descriptivo, solo relaciones 1:1):\n" + pib[["anio", "anio_pib", "n", "corr_ice_logpib",
        "beta_ice", "se_crv1", "r2_parcial_ice"]].round(4).to_string(index=False))
    log.close()


if __name__ == "__main__":
    main()
