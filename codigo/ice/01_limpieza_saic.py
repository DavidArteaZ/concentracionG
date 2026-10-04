"""Módulo 01 — Limpieza de SAIC.

Entradas (data/raw/ice/):
  - saic_2003_2023/*.csv          UE y PBT por municipio x rama/clase
  - saic_totales_municipales.csv  totales municipales (UE, PO, remuneraciones, VACB)
  - municipios_nuevos_2024.csv    reasignación de municipios creados en 2024
Salidas (data/clean/ice/):
  - saic_largo.csv.gz             anio, cve_mun, nivel, codigo, variable, valor, estado_celda
  - saic_totales_limpio.csv       un registro por municipio-año
Reglas: celda vacía = suprimida por confidencialidad (nota del propio archivo).
"""
import numpy as np
import pandas as pd

from . import config as C
from .utils import Log, asegurar_dirs, clasificar_celda, clave_mun, leer_saic


def reasignar_2024(df, nuevos, cols_valor, log, etiqueta):
    """Suma los municipios creados en 2024 a su municipio de origen (solo 2023)."""
    mapa = dict(zip(nuevos.cve_mun_nuevo, nuevos.cve_mun_origen))
    m23 = df.anio == 2023
    afectados = df.loc[m23 & df.cve_mun.isin(mapa), "cve_mun"].unique()
    log(f"[{etiqueta}] municipios 2024 reasignados en 2023: {sorted(afectados)}")
    df.loc[m23, "cve_mun"] = df.loc[m23, "cve_mun"].replace(mapa)
    return df


def main():
    asegurar_dirs()
    log = Log("01_limpieza_saic")
    nuevos = pd.read_csv(C.NUEVOS_2024, dtype=str)
    assert set(nuevos.cve_mun_nuevo) == {"24059", "25019", "25020"}

    # ------------------------------------------------------------------ ramas/clases
    partes = []
    for anio, fn in C.SAIC_FILES.items():
        df, meta = leer_saic(C.SAIC_DIR / fn)
        log(f"\n== {anio}: {fn}")
        log(f"   consulta: {meta['consulta']} | bytes nulos eliminados: {meta['bytes_nulos']:,}"
            f" | nota de confidencialidad: {meta['nota_confidencialidad']}")
        assert meta["nota_confidencialidad"], "No se encontró la nota de confidencialidad"
        assert len(df) == C.SAIC_FILAS_ESPERADAS[anio], (anio, len(df))
        df.columns = ["anio", "entidad", "municipio", "actividad", "ue", "pbt"]
        assert (df.anio.astype(int) == anio).all()
        n0 = len(df)
        df = df[df.municipio.str.strip() != ""]
        df = df[df.actividad.str.match(r"^(Rama|Clase) \d")].copy()
        log(f"   filas: {n0:,} -> municipales rama/clase: {len(df):,}")
        df["cve_mun"] = clave_mun(df.entidad, df.municipio)
        assert df.cve_mun.str.fullmatch(r"\d{5}").all()
        df["nivel"] = np.where(df.actividad.str.startswith("Rama"), "rama", "clase")
        df["codigo"] = df.actividad.str.extract(r"^(?:Rama|Clase) (\d+)")[0]
        assert (df.loc[df.nivel == "rama", "codigo"].str.len() == 4).all()
        assert (df.loc[df.nivel == "clase", "codigo"].str.len() == 6).all()
        ramas = set(df.loc[df.nivel == "rama", "codigo"])
        log(f"   municipios: {df.cve_mun.nunique():,} | ramas: {len(ramas)} | "
            f"clases: {df.loc[df.nivel == 'clase', 'codigo'].nunique()}")
        for var in ["ue", "pbt"]:
            val, est = clasificar_celda(df[var])
            df[f"{var}_v"], df[f"{var}_e"] = val, est
            log(f"   {var}: " + ", ".join(f"{k}={v:,}" for k, v in est.value_counts().items()))
        assert (df.ue_e == "valor").all(), "UE con celdas suprimidas o cero"
        rr = df[df.nivel == "rama"]
        log(f"   PBT suprimido | UE>0 (rama): {100*(rr.pbt_e == 'suprimida').mean():.1f}%"
            f" | PBT negativo (rama): {(rr.pbt_v < 0).sum()}")
        dup = df.duplicated(["cve_mun", "nivel", "codigo"]).sum()
        assert dup == 0, f"{dup} duplicados"
        partes.append((anio, df, ramas))

    union = set().union(*[r for _, _, r in partes])
    log(f"\nRamas en la unión 2003-2023: {len(union)}")
    for anio, _, r in partes:
        aus = union - r
        log(f"   {anio}: ausentes {sorted(aus)}")
        assert aus == C.RAMAS_AUSENTES[anio], anio

    largo = []
    for anio, df, _ in partes:
        for var in ["ue", "pbt"]:
            t = df[["cve_mun", "nivel", "codigo"]].copy()
            t["anio"], t["variable"] = anio, var
            t["valor"], t["estado_celda"] = df[f"{var}_v"].values, df[f"{var}_e"].values
            largo.append(t)
    largo = pd.concat(largo, ignore_index=True)

    # Reasignación de municipios creados en 2024 (solo 2023). Se suma UE; el PBT
    # se suma solo si ambos componentes son observados (si no, queda suprimido).
    largo = reasignar_2024(largo, nuevos, ["valor"], log, "ramas")
    largo["sup"] = (largo.estado_celda == "suprimida").astype(int)
    m23n = (largo.anio == 2023)
    claves = ["anio", "cve_mun", "nivel", "codigo", "variable"]
    afect = largo[m23n].duplicated(claves, keep=False)
    log(f"   celdas 2023 que se combinan por la reasignación: {int(afect.sum()):,}")
    agg = largo.groupby(claves, as_index=False, sort=False).agg(
        valor=("valor", "sum"), n_sup=("sup", "sum"))
    agg["estado_celda"] = np.where(agg.n_sup > 0, "suprimida",
                                   np.where(agg.valor == 0, "cero", "valor"))
    agg.loc[agg.estado_celda == "suprimida", "valor"] = np.nan
    largo = agg.drop(columns="n_sup")[["anio", "cve_mun", "nivel", "codigo",
                                        "variable", "valor", "estado_celda"]]
    largo.to_csv(C.CLEAN / "saic_largo.csv.gz", index=False)
    log(f"\nGuardado saic_largo.csv.gz: {len(largo):,} filas")
    resumen = (largo[largo.variable == "ue"].groupby(["anio", "nivel"])
               .agg(municipios=("cve_mun", "nunique"), codigos=("codigo", "nunique"),
                    filas=("valor", "size"), ue_total=("valor", "sum")))
    log(resumen.to_string())
    resumen.to_csv(C.OUT / "01_resumen_saic.csv")

    # ------------------------------------------------------------------ totales
    log("\n== Totales municipales")
    tot, meta = leer_saic(C.SAIC_TOTALES)
    log(f"   consulta: {meta['consulta']} | bytes nulos eliminados: {meta['bytes_nulos']:,}"
        f" | nota: {meta['nota_confidencialidad']}")
    tot.columns = ["anio", "entidad", "municipio", "actividad", "ue", "po_total",
                   "po_rem", "remuneraciones_mdp", "vacb_mdp"]
    log(f"   actividades: {tot.actividad.value_counts().to_dict()}")
    nac = tot[tot.actividad == "Total nacional"].copy()
    tot = tot[tot.actividad == "Total municipal"].copy()
    tot["anio"] = tot.anio.astype(int)
    tot["cve_mun"] = clave_mun(tot.entidad, tot.municipio)
    assert tot.cve_mun.str.fullmatch(r"\d{5}").all()
    assert not tot.duplicated(["anio", "cve_mun"]).any()
    vars_ = ["ue", "po_total", "po_rem", "remuneraciones_mdp", "vacb_mdp"]
    sup = {}
    for v in vars_:
        val, est = clasificar_celda(tot[v])
        tot[v] = val
        sup[v] = est
    est_df = pd.DataFrame(sup)
    tab = est_df.assign(anio=tot.anio.values).groupby("anio").agg(
        lambda s: int((s == "suprimida").sum()))
    log("   celdas suprimidas por año:\n" + tab.to_string())
    log("   municipios por año: " + tot.groupby("anio").cve_mun.nunique().to_string().replace("\n", " | "))
    # consistencia con la suma de ramas (UE)
    ue_r = (largo[(largo.variable == "ue") & (largo.nivel == "rama")]
            .groupby(["anio", "cve_mun"]).valor.sum().rename("ue_ramas"))
    tot = reasignar_2024(tot, nuevos, vars_, log, "totales")
    sup_any = (est_df == "suprimida").groupby([tot.anio.values, tot.cve_mun.values]).any()
    tot = tot.groupby(["anio", "cve_mun"], as_index=False)[vars_].sum(min_count=1)
    sup_any.index.names = ["anio", "cve_mun"]
    sup_any = sup_any.reset_index()
    for v in vars_:
        m = tot.merge(sup_any[["anio", "cve_mun", v]], on=["anio", "cve_mun"],
                      suffixes=("", "_sup"))[f"{v}_sup"].values
        tot.loc[m, v] = np.nan
        tot[f"{v}_suprimida"] = m
    chk = tot.set_index(["anio", "cve_mun"]).join(ue_r, how="outer")
    dif = chk[(chk.ue - chk.ue_ramas).abs() > 0]
    log(f"   municipios donde UE total != suma de UE por rama: {len(dif)}")
    if len(dif):
        log(dif[["ue", "ue_ramas"]].head(15).to_string())
    # variables derivadas
    tot["rem_media_pesos"] = tot.remuneraciones_mdp * 1e6 / tot.po_rem
    tot["vacb_por_po_pesos"] = tot.vacb_mdp * 1e6 / tot.po_total
    log(f"   remuneración media no calculable (PO remunerado 0 o suprimido): "
        f"{tot.rem_media_pesos.isna().sum() + np.isinf(tot.rem_media_pesos).sum()}")
    log(f"   VACB negativo: {(tot.vacb_mdp < 0).sum()} | VACB/PO no calculable: "
        f"{tot.vacb_por_po_pesos.isna().sum()}")
    tot = tot.replace([np.inf, -np.inf], np.nan)
    # nacionales para relativizar (elimina inflación y ciclo nacional)
    nac["anio"] = nac.anio.astype(int)
    for v in ["po_rem", "remuneraciones_mdp", "po_total", "vacb_mdp"]:
        nac[v] = pd.to_numeric(nac[v])
    nac["rem_media_nac"] = nac.remuneraciones_mdp * 1e6 / nac.po_rem
    nac["vacb_po_nac"] = nac.vacb_mdp * 1e6 / nac.po_total
    tot = tot.merge(nac[["anio", "rem_media_nac", "vacb_po_nac"]], on="anio")
    tot["log_rem_rel"] = np.log(tot.rem_media_pesos / tot.rem_media_nac)
    with np.errstate(invalid="ignore"):
        tot["log_vacb_po_rel"] = np.log(tot.vacb_por_po_pesos.where(tot.vacb_por_po_pesos > 0)
                                        / tot.vacb_po_nac)
    tot.to_csv(C.CLEAN / "saic_totales_limpio.csv", index=False)
    log(f"   Guardado saic_totales_limpio.csv: {len(tot):,} filas")
    log(tot.groupby("anio")[["log_rem_rel", "log_vacb_po_rel"]].describe().round(3).T.to_string())
    log.close()


if __name__ == "__main__":
    main()
