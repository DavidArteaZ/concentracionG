"""Módulo 07 — Base de ICE para el DML.

Salida: data/clean/ice/ice_para_dml.csv (formato ancho por especificación)
  cve_mun, anio, ice (base), ice_<especificacion> para cada alternativa,
  en_nucleo, motivo_na, log_ue_total, log_pob, diversidad.
La tabla padre-hijo (municipios_padre_hijo.csv) se entrega aparte; la regla
para asignar ICE a municipios creados después de los 14 años del entrevistado
queda diferida (decisión 6).
Nota para el DML: X principal incluye log_pob; robustez agrega log_ue_total.
La diversidad no va en X (es parte del ICE).
"""
import numpy as np
import pandas as pd

from . import config as C
from .utils import Log, asegurar_dirs, poblacion_censal


def main():
    asegurar_dirs()
    log = Log("07_export_dml")
    ice = pd.read_csv(C.CLEAN / "ice_municipal.csv", dtype={"cve_mun": str})
    base = ice[ice.especificacion == "base"].copy()
    alt = pd.read_csv(C.CLEAN / "ice_alternativas.csv.gz", dtype={"cve_mun": str})
    alt = alt[alt.especificacion != f"umbral_U{C.U_MIN}_D{C.D_MIN}_P{C.P_MIN}"]
    ancho = alt.pivot_table(index=["cve_mun", "anio"], columns="especificacion", values="ice")
    ancho.columns = [f"ice_{c}" for c in ancho.columns]
    out = (base[["cve_mun", "anio", "ice", "en_nucleo", "motivo_na", "ue_total", "diversidad"]]
           .merge(poblacion_censal(), on=["cve_mun", "anio"], how="left")
           .merge(ancho.reset_index(), on=["cve_mun", "anio"], how="left"))
    out["log_ue_total"] = np.log(out.pop("ue_total"))
    assert not out.duplicated(["cve_mun", "anio"]).any()
    assert out.ice.notna().all()
    out = out[["cve_mun", "anio", "ice", "en_nucleo", "motivo_na", "log_ue_total", "log_pob",
               "diversidad"] + sorted(ancho.columns)]
    out.to_csv(C.CLEAN / "ice_para_dml.csv", index=False)
    log(f"ice_para_dml.csv: {len(out):,} filas, {out.shape[1]} columnas, "
        f"{len(ancho.columns)} especificaciones alternativas")
    log("Municipios por año: " + out.groupby("anio").size().to_string().replace("\n", " | "))
    log(f"Sin población: {out.log_pob.isna().sum()} | NaN por alternativa (máx.): "
        f"{out[sorted(ancho.columns)].isna().sum().max()}")
    log.close()


if __name__ == "__main__":
    main()
