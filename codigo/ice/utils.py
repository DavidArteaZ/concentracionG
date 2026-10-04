"""Utilidades comunes: logging, lectura de SAIC y cálculo del ICE."""
from __future__ import annotations

import io
import platform
import re
import sys
import unicodedata
from datetime import datetime

import numpy as np
import pandas as pd
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import connected_components

from . import config as C


# ----------------------------------------------------------------------------
# Logging
# ----------------------------------------------------------------------------
class Log:
    """Imprime en pantalla y escribe en outputs/ice/logs/<nombre>.log."""

    def __init__(self, nombre: str):
        C.LOGS.mkdir(parents=True, exist_ok=True)
        self.path = C.LOGS / f"{nombre}.log"
        self.f = open(self.path, "w", encoding="utf-8")
        self(f"# {nombre} | {datetime.now().isoformat(timespec='seconds')}")
        self(f"# Python {platform.python_version()} | numpy {np.__version__} | "
             f"pandas {pd.__version__}")

    def __call__(self, *msg):
        s = " ".join(str(m) for m in msg)
        print(s)
        self.f.write(s + "\n")
        self.f.flush()

    def close(self):
        self.f.close()


def asegurar_dirs():
    for d in (C.CLEAN, C.OUT, C.LOGS):
        d.mkdir(parents=True, exist_ok=True)


# ----------------------------------------------------------------------------
# Lectura de archivos SAIC
# ----------------------------------------------------------------------------
NOTA_CONF = "se omitieron los datos absolutos de las variables económicas"


def leer_saic(path) -> tuple[pd.DataFrame, dict]:
    """Lee un CSV exportado por SAIC.

    - quita el relleno de bytes nulos al final del archivo;
    - decodifica UTF-8 con BOM;
    - descarta las 4 filas de encabezado y la nota al pie;
    - lee todo como texto (las celdas vacías se conservan como "").
    Devuelve el DataFrame y metadatos (nulos eliminados, nota encontrada).
    """
    raw = open(path, "rb").read()
    n_nulos = len(raw) - len(raw.rstrip(b"\x00"))
    texto = raw.rstrip(b"\x00").decode("utf-8-sig")
    lineas = texto.split("\n")
    meta = {
        "bytes_nulos": n_nulos,
        "consulta": lineas[2].split(",")[0].strip(),
        "nota_confidencialidad": NOTA_CONF in texto,
    }
    # quitar nota final: la última línea con contenido es la nota, precedida por una vacía
    cuerpo = "\n".join(lineas[4:])
    df = pd.read_csv(io.StringIO(cuerpo), dtype=str, keep_default_na=False)
    df = df.loc[:, ~df.columns.str.startswith("Unnamed")]
    df = df[df.iloc[:, 0].str.fullmatch(r"\d{4}")].copy()  # descarta vacías y la nota
    return df, meta


def clasificar_celda(s: pd.Series) -> tuple[pd.Series, pd.Series]:
    """Devuelve (valor numérico, estado) con estado en {valor, cero, suprimida}."""
    s = s.str.strip()
    num = pd.to_numeric(s, errors="coerce")
    no_num = s[(num.isna()) & (s != "")]
    if len(no_num):
        raise ValueError(f"Valores no numéricos inesperados: {no_num.value_counts().head()}")
    estado = np.where(s == "", "suprimida", np.where(num == 0, "cero", "valor"))
    return num, pd.Series(estado, index=s.index)


def clave_mun(ent: pd.Series, mun: pd.Series) -> pd.Series:
    e = ent.str.extract(r"^\s*(\d{2})")[0]
    m = mun.str.extract(r"^\s*(\d{3})")[0]
    return e + m


def norm_nombre(s: str) -> str:
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().lower()
    s = re.sub(r"[^a-z0-9 ]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


# ----------------------------------------------------------------------------
# Cálculo del ICE: núcleo + PCI espectral + proyección
# ----------------------------------------------------------------------------
def nucleo(X: pd.DataFrame, u_min, d_min, p_min):
    """Filtro iterativo de municipios y ramas sobre tamaños crudos.

    X: matriz municipios x ramas con conteos (>= 0).
    Devuelve (índice de municipios, columnas de ramas, número de iteraciones).
    """
    filas, cols = X.index, X.columns
    it = 0
    while True:
        it += 1
        sub = X.loc[filas, cols]
        ok_m = (sub.sum(1) >= u_min) & ((sub > 0).sum(1) >= d_min)
        f2 = sub.index[ok_m]
        sub = sub.loc[f2]
        ok_p = (sub > 0).sum(0) >= p_min
        c2 = sub.columns[ok_p]
        if len(f2) == len(filas) and len(c2) == len(cols):
            return filas, cols, it
        filas, cols = f2, c2
        if it > 100:
            raise RuntimeError("El filtro del núcleo no converge")


def rca_binaria(Xc: np.ndarray, den: np.ndarray | None = None):
    tot_c = Xc.sum(1, keepdims=True)
    with np.errstate(divide="ignore", invalid="ignore"):
        s = Xc / tot_c
    if den is None:
        den = Xc.sum(0) / Xc.sum()
    with np.errstate(divide="ignore", invalid="ignore"):
        rca = s / den[None, :]
    rca = np.nan_to_num(rca, nan=0.0, posinf=0.0)
    return rca, (rca >= C.RCA_UMBRAL).astype(float), den


def componentes(M: np.ndarray) -> int:
    n, p = M.shape
    A = csr_matrix(M)
    big = csr_matrix((np.r_[A.data, A.data],
                      (np.r_[A.nonzero()[0], A.nonzero()[1] + n],
                       np.r_[A.nonzero()[1] + n, A.nonzero()[0]])),
                     shape=(n + p, n + p))
    return connected_components(big, directed=False)[0]


def calcular_ice(X: pd.DataFrame, u_min=C.U_MIN, d_min=C.D_MIN, p_min=C.P_MIN,
                 metodo="eigen", fitness_iter=20000):
    """ICE por núcleo + proyección.

    X: DataFrame municipios (cve_mun) x ramas con UE (u otra variable >= 0).
    Devuelve dict con DataFrames 'mun' y 'prod' y el diccionario 'diag'.
    """
    X = X.loc[X.sum(1) > 0, X.sum(0) > 0]
    fil, col, iters = nucleo(X, u_min, d_min, p_min)
    Xc = X.loc[fil, col].to_numpy(float)
    _, M, den = rca_binaria(Xc)
    kc, kp = M.sum(1), M.sum(0)
    assert (kc > 0).all() and (kp > 0).all(), "diversidad o ubicuidad cero en el núcleo"
    diag = {"n_mun_total": len(X), "n_ramas_total": X.shape[1],
            "n_mun_nucleo": len(fil), "n_ramas_nucleo": len(col),
            "iter_nucleo": iters, "componentes": componentes(M)}

    if metodo == "eigen":
        S = (M / np.sqrt(kp)[None, :]).T @ (M / kc[:, None]) / np.sqrt(kp)[None, :]
        S = (S + S.T) / 2
        w, V = np.linalg.eigh(S)
        w, V = w[::-1], V[:, ::-1]
        pci_raw = V[:, 1] / np.sqrt(kp)
        eci_core = (M / kc[:, None]) @ pci_raw
        sgn = np.sign(np.corrcoef(eci_core, kc)[0, 1])
        pci_raw, eci_core = sgn * pci_raw, sgn * eci_core
        diag.update({f"lambda{i+1}": w[i] for i in range(5)})
        diag["brecha_l2_l3"] = w[1] - w[2]
        diag["cociente_l3_l2"] = w[2] / w[1]
        diag["n_eig_mayor_0999"] = int((w > 0.999).sum())
    elif metodo == "fitness":
        # Tacchella et al. (2012). Los valores de F de algunos municipios tienden a
        # cero sin converger (matriz no anidada); por eso el criterio de parada es
        # la estabilidad del ranking: ranking idéntico durante 200 iteraciones.
        F = np.ones(len(kc)); Q = np.ones(len(kp))
        rank_prev, estable, i = None, 0, 0
        while i < fitness_iter:
            i += 1
            F_new = M @ Q
            Q_new = 1.0 / (M.T @ (1.0 / F))
            F, Q = F_new / F_new.mean(), Q_new / Q_new.mean()
            F, Q = np.maximum(F, 1e-300), np.maximum(Q, 1e-300)
            rk = np.argsort(np.argsort(F))
            estable = estable + 1 if rank_prev is not None and (rk == rank_prev).all() else 0
            rank_prev = rk
            if estable >= 200:
                break
        diag["fitness_iteraciones"] = i
        diag["fitness_ranking_estable"] = estable >= 200
        diag["fitness_cambio_final"] = estable
        pci_raw = np.log(Q)
        eci_core = np.log(F)
    else:
        raise ValueError(metodo)

    # Proyección a todos los municipios sobre las ramas del núcleo
    Xall = X.loc[:, col].to_numpy(float)
    con_ue = Xall.sum(1) > 0
    _, Mall, _ = rca_binaria(np.where(con_ue[:, None], Xall, 0), den)
    kc_all = Mall.sum(1)
    if metodo == "eigen":
        with np.errstate(divide="ignore", invalid="ignore"):
            ice_raw = (Mall @ pci_raw) / kc_all
    else:
        Fall = Mall @ Q  # en el núcleo es proporcional a F al converger
        with np.errstate(divide="ignore"):
            ice_raw = np.where(kc_all > 0, np.log(np.where(Fall > 0, Fall, np.nan)), np.nan)
    ice_raw = np.where(kc_all > 0, ice_raw, np.nan)

    en_nucleo = X.index.isin(fil)
    idx_core = np.where(en_nucleo)[0]
    pos = pd.Index(X.index[idx_core]).get_indexer(fil)
    # verificación: la proyección reproduce el ICE del núcleo
    r = np.corrcoef(ice_raw[idx_core][np.argsort(pos)], eci_core)[0, 1]
    diag["corr_proyeccion_nucleo"] = r
    assert r >= C.TOL_PROYECCION, f"La proyección no reproduce el núcleo (r={r})"

    mu, sd = np.nanmean(ice_raw[en_nucleo]), np.nanstd(ice_raw[en_nucleo])
    ice = (ice_raw - mu) / sd
    pci = (pci_raw - mu) / sd if metodo == "eigen" else (pci_raw - pci_raw.mean()) / pci_raw.std()

    motivo = np.where(~con_ue, "sin_ue_en_ramas_nucleo",
                      np.where(kc_all == 0, "sin_rama_nucleo_con_rca", ""))
    mun = pd.DataFrame({
        "cve_mun": X.index, "en_nucleo": en_nucleo, "ue_total": X.sum(1).to_numpy(),
        "ramas_presentes": (X > 0).sum(1).to_numpy(), "diversidad": kc_all,
        "ice_raw": ice_raw, "ice": ice, "motivo_na": motivo})
    prod = pd.DataFrame({"rama": col, "ubicuidad": kp, "pci_raw": pci_raw, "pci": pci})

    core = mun[mun.en_nucleo]
    diag["spearman_ice_diversidad"] = core.ice.corr(core.diversidad, method="spearman")
    diag["spearman_ice_logue"] = core.ice.corr(np.log(core.ue_total), method="spearman")
    diag["empates_ice_pct"] = 100 * mun.ice.dropna().round(10).duplicated(keep=False).mean()
    diag["n_ice_nan"] = int(mun.ice.isna().sum())
    return {"mun": mun, "prod": prod, "diag": diag, "nucleo": (fil, col), "M": M}


def matriz(df: pd.DataFrame, anio: int, nivel="rama", var="ue") -> pd.DataFrame:
    sub = df[(df.anio == anio) & (df.nivel == nivel) & (df.variable == var)]
    X = sub.pivot_table(index="cve_mun", columns="codigo", values="valor",
                        aggfunc="sum", fill_value=0)
    return X.clip(lower=0)


# ----------------------------------------------------------------------------
# Población por año censal (interpolación log-lineal de quinquenios)
# ----------------------------------------------------------------------------
def poblacion_censal() -> pd.DataFrame:
    """Población municipal (geografía 2023) para 2003, 2008, 2013, 2018 y 2023.

    2003 = interp. log-lineal 2000-2005; 2008 = 2005-2010; 2013 = 2010-2015;
    2018 = 2015-2020; 2023 = extrapolación con la tasa 2015-2020.
    """
    p = pd.read_csv(C.POBLACION, dtype={"CVEGEO": str}).set_index("CVEGEO")
    lp = np.log(p.astype(float))
    out = {
        2003: lp["2000"] + 0.6 * (lp["2005"] - lp["2000"]),
        2008: lp["2005"] + 0.6 * (lp["2010"] - lp["2005"]),
        2013: lp["2010"] + 0.6 * (lp["2015"] - lp["2010"]),
        2018: lp["2015"] + 0.6 * (lp["2020"] - lp["2015"]),
        2023: lp["2020"] + 0.6 * (lp["2020"] - lp["2015"]),
    }
    df = pd.DataFrame(out).stack().rename("log_pob").reset_index()
    df.columns = ["cve_mun", "anio", "log_pob"]
    return df


# ----------------------------------------------------------------------------
# Cohorte 1 de ESRU-EMOVI (solo para contar entrevistados afectados)
# ----------------------------------------------------------------------------
def emovi_cohorte1() -> pd.DataFrame:
    """Entrevistados de 25 a 34 años con municipio a los 14 años válido.

    anio_ice = año censal (2003, 2008, 2013) más cercano al año en que el
    entrevistado tenía 14 años (2023 - edad + 14). Solo se usa para contar
    afectados por los filtros; la asignación final es la de D15.
    """
    d = pd.read_stata(C.RAW_EMOVI, columns=["p20_COD", "edad", "factor"],
                      convert_categoricals=False)
    d["edad"] = d.edad.astype(int)
    d = d[(d.edad >= 25) & (d.edad <= 34)].copy()
    d["cve_mun"] = d.p20_COD.astype(str).str.zfill(5)
    d = d[~d.cve_mun.isin(["33333", "99999"])]
    a14 = 2023 - d.edad + 14
    d["anio_ice"] = np.select([a14 <= 2005, a14 <= 2010], [2003, 2008], 2013)
    return d[["cve_mun", "edad", "factor", "anio_ice"]].reset_index(drop=True)
