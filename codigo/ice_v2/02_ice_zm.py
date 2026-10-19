"""V2 — Módulo 02: ICE por zona metropolitana (D25).

Uso (desde la raíz del repositorio):  python codigo/ice_v2/02_ice_zm.py
Requisitos: haber corrido V1 01_limpieza_saic (data/clean/ice_v1/saic_largo.csv.gz)
            y V2 01_delimitaciones.

Cada zona metropolitana es UNA unidad de la red: se suman las UE por rama de sus
municipios; los municipios no metropolitanos quedan como unidades propias. Todo
lo demás es V1 sin cambios (ice_v1.utils.calcular_ice: UE, rama, RCA >= 1, núcleo
U_MIN/D_MIN/P_MIN, PCI espectral, proyección), un cálculo por año censal y por
delimitación (mapa estático: la misma para todos los años).

Especificaciones:
  identidad  cada municipio es su propia unidad. Debe reproducir ice_municipal.csv
             (V1, base); si no, el módulo se detiene (prueba de identidad de D25).
  zm2010     delimitación 2010 (principal de esta robustez).
  zm2020     delimitación 2020 (alternativa).

Asignación de municipios a unidades (D25, reglas de geografía):
  1. Municipio en la delimitación -> su unidad.
  2. Hijo (municipios_padre_hijo.csv) fuera de la delimitación con padre dentro:
     según config_v2.HIJO_EXISTIA, hereda la unidad del padre (no existía en la
     geografía de la delimitación) o queda como unidad propia (existía y fue
     excluido). Un caso no declarado detiene el módulo.
  3. Cualquier otro municipio -> unidad propia.
  Se aplica a la geografía de cada levantamiento SAIC (para el ICE) y a la de
  2023 (para la población CONAPO y para las claves cve_ice del DML).

Salidas (data/clean/ice_v2/):
  unidades_zm.csv          delimitacion, geografia, cve_mun, unidad, regla
  ice_zm_unidad.csv        delimitacion, anio, unidad, n_mun, en_nucleo, ue_total,
                           ramas_presentes, diversidad, ice, ice_raw, motivo_na
  pci_rama_zm.csv          delimitacion, anio, rama, ubicuidad, pci_raw, pci
  ice_zm_para_dml.csv      cve_mun, anio, y por delimitación d: unidad_d, ice_d,
                           en_nucleo_d, log_ue_total_d  (claves de la geografía
                           de cada levantamiento, como ice_para_dml.csv de V1)
  pob_unidad_conapo.csv    cve_mun (geografía 2023), anio, unidad_d, log_pob_d
                           (CONAPO, suma de los municipios de la unidad)
  outputs/ice_v2/diagnosticos_zm.csv
"""
import numpy as np
import pandas as pd

import config_v2 as C2
from _v1 import cargar

C1, U = cargar()


def leer_entradas():
    largo = pd.read_csv(C2.CLEAN_V1 / "saic_largo.csv.gz", dtype={"cve_mun": str, "codigo": str})
    ph = pd.read_csv(C2.CLEAN_V1 / "municipios_padre_hijo.csv", dtype=str)
    padre = ph.dropna(subset=["cve_mun_padre"]).set_index("cve_mun_hijo").cve_mun_padre
    delims = {d: pd.read_csv(C2.CLEAN / f"delimitacion_{d}.csv", dtype={"cve_mun": str})
              for d in C2.DELIMITACIONES}
    v1 = pd.read_csv(C2.CLEAN_V1 / "ice_municipal.csv", dtype={"cve_mun": str})
    v1 = v1[v1.especificacion == "base"]
    con = pd.read_csv(C2.CONAPO, encoding="utf-8-sig", usecols=["CLAVE", "SEXO", "ANO", "POB_TOTAL"])
    assert set(con.SEXO) == {"HOMBRES", "MUJERES"}
    con["cve_mun"] = con.CLAVE.astype(int).map("{:05d}".format)
    con = con.groupby(["cve_mun", "ANO"]).POB_TOTAL.agg(["sum", "size"]).reset_index()
    assert (con["size"] == 2).all()
    con = con.rename(columns={"ANO": "anio", "sum": "pob"})[["cve_mun", "anio", "pob"]]
    return largo, padre, delims, v1, con


def asignar(claves, delim, nombre, padre):
    """Unidad de cada clave municipal según las reglas de D25."""
    dm = delim.set_index("cve_mun").unidad
    decl = C2.HIJO_EXISTIA.get(nombre, {})
    unidad, regla = {}, {}
    for c in claves:
        if c in dm.index:
            unidad[c], regla[c] = dm[c], "delimitacion"
        elif c in padre.index and padre[c] in dm.index:
            if c not in decl:
                raise ValueError(f"{nombre}: el hijo {c} (padre {padre[c]}) no está declarado en "
                                 "config_v2.HIJO_EXISTIA")
            if decl[c]:
                unidad[c], regla[c] = f"M_{c}", "hijo_excluido"
            else:
                unidad[c], regla[c] = dm[padre[c]], "hereda_padre"
        else:
            unidad[c], regla[c] = f"M_{c}", "no_metropolitano"
    return pd.DataFrame({"cve_mun": list(unidad), "unidad": list(unidad.values()),
                         "regla": [regla[c] for c in unidad]})


def main():
    for d in (C2.CLEAN, C2.OUT, C2.LOGS):
        d.mkdir(parents=True, exist_ok=True)
    C1.LOGS = C2.LOGS
    log = U.Log("v2_02_ice_zm")
    log(f"Parámetros de V1: U_MIN={C1.U_MIN}, D_MIN={C1.D_MIN}, P_MIN={C1.P_MIN}, "
        f"RCA >= {C1.RCA_UMBRAL}")
    largo, padre, delims, v1, con = leer_entradas()
    geo23 = sorted(con.cve_mun.unique())

    asign, uni_rows, prod_rows, mun_rows, diags = [], [], [], [], []
    for esp in ["identidad"] + C2.DELIMITACIONES:
        for a in C1.ANIOS:
            X = U.matriz(largo, a)
            if esp == "identidad":
                mp = pd.DataFrame({"cve_mun": X.index, "unidad": X.index, "regla": "identidad"})
            else:
                mp = asignar(X.index, delims[esp], esp, padre)
                asign.append(mp.assign(delimitacion=esp, geografia=f"SAIC {a}"))
                # Regla 2: municipios de la delimitación que no existen en el levantamiento
                # y cuyo padre (que sí existe) quedó en otra unidad.
                dm = delims[esp].set_index("cve_mun").unidad
                um = mp.set_index("cve_mun").unidad
                for c in sorted(set(dm.index) - set(X.index)):
                    p = padre.get(c)
                    if p is not None and p in um.index and um[p] != dm[c]:
                        log(f"[{esp} {a}] {c} no existe en SAIC {a}; su territorio va con su padre "
                            f"{p} ({um[p]}), no con {dm[c]}")
                    elif p is None:
                        log(f"[{esp} {a}] {c} de la delimitación no aparece en SAIC {a} (sin UE)")
            Xu = X.groupby(mp.set_index("cve_mun").unidad.reindex(X.index).to_numpy()).sum()
            Xu.index.name = "unidad"
            r = U.calcular_ice(Xu)
            d = r["diag"]
            assert d["componentes"] == 1, f"{esp} {a}: núcleo con {d['componentes']} componentes"
            un = r["mun"].rename(columns={"cve_mun": "unidad"})
            un["n_mun"] = un.unidad.map(mp.groupby("unidad").size())
            un["anio"], un["delimitacion"] = a, esp
            uni_rows.append(un)
            prod_rows.append(r["prod"].assign(anio=a, delimitacion=esp))
            mm = mp.merge(un[["unidad", "ice", "en_nucleo", "ue_total", "motivo_na"]], on="unidad")
            mm["anio"], mm["delimitacion"] = a, esp
            mun_rows.append(mm)

            zm = un[un.n_mun > 1]
            p = con[con.anio == a].merge(mp[["cve_mun", "unidad"]], on="cve_mun")
            lp = np.log(p.groupby("unidad").pob.sum())
            core = un[un.en_nucleo].set_index("unidad")
            d.update({"delimitacion": esp, "anio": a, "n_unidades": len(un),
                      "n_unidades_multimunicipales": len(zm),
                      "n_multimunicipales_en_nucleo": int(zm.en_nucleo.sum()),
                      "spearman_ice_logpob_conapo": core.ice.corr(lp.reindex(core.index),
                                                                  method="spearman")})
            if esp != "identidad":
                b = v1[v1.anio == a].set_index("cve_mun").ice
                nm = mm[mm.unidad.str.startswith("M_")].set_index("cve_mun").ice
                d["spearman_v1_v2_no_metro"] = nm.corr(b.reindex(nm.index), method="spearman")
                d["spearman_v1_v2_todos_mun"] = mm.set_index("cve_mun").ice.corr(
                    b.reindex(mm.cve_mun).set_axis(mm.cve_mun), method="spearman")
            diags.append(d)
            log(f"[{esp} {a}] unidades {len(un)} ({len(zm)} multimunicipales, "
                f"{int(zm.en_nucleo.sum())} en el núcleo); núcleo {d['n_mun_nucleo']} unidades x "
                f"{d['n_ramas_nucleo']} ramas; brecha λ2-λ3 {d['brecha_l2_l3']:.4f}; "
                f"Spearman ICE~log pob {d['spearman_ice_logpob_conapo']:.3f}"
                + (f"; Spearman V1-V2 (no metropolitanos) {d['spearman_v1_v2_no_metro']:.4f}"
                   if esp != "identidad" else ""))

    mun = pd.concat(mun_rows, ignore_index=True)

    # Prueba de identidad (D25): debe reproducir V1 exactamente.
    ide = mun[mun.delimitacion == "identidad"].merge(
        v1[["anio", "cve_mun", "ice", "en_nucleo"]], on=["anio", "cve_mun"], how="outer",
        suffixes=("", "_v1"), indicator=True)
    assert (ide._merge == "both").all(), ide._merge.value_counts()
    assert (ide.ice.isna() == ide.ice_v1.isna()).all()
    dif = (ide.ice - ide.ice_v1).abs().max()
    assert dif < C2.TOL_IDENTIDAD, f"La identidad no reproduce V1: máx. |Δ| = {dif}"
    assert (ide.en_nucleo == ide.en_nucleo_v1.astype(bool)).all()
    log(f"\nPrueba de identidad superada: {len(ide):,} municipio-año, máx. |ICE - ICE V1| = {dif:.2e}")

    # ---- Salidas ----
    pd.concat(asign + [asignar(geo23, delims[e], e, padre).assign(delimitacion=e, geografia="2023")
                       for e in C2.DELIMITACIONES], ignore_index=True)[
        ["delimitacion", "geografia", "cve_mun", "unidad", "regla"]].to_csv(
        C2.CLEAN / "unidades_zm.csv", index=False)
    uni = pd.concat(uni_rows, ignore_index=True)
    uni = uni[uni.delimitacion != "identidad"]
    uni[["delimitacion", "anio", "unidad", "n_mun", "en_nucleo", "ue_total", "ramas_presentes",
         "diversidad", "ice", "ice_raw", "motivo_na"]].to_csv(C2.CLEAN / "ice_zm_unidad.csv", index=False)
    pr = pd.concat(prod_rows, ignore_index=True)
    pr[pr.delimitacion != "identidad"].to_csv(C2.CLEAN / "pci_rama_zm.csv", index=False)

    ancho = None
    for e in C2.DELIMITACIONES:
        s = mun[mun.delimitacion == e][["cve_mun", "anio", "unidad", "ice", "en_nucleo", "ue_total"]]
        s = s.assign(log_ue_total=np.log(s.pop("ue_total"))).rename(
            columns={c: f"{c}_{e}" for c in ["unidad", "ice", "en_nucleo", "log_ue_total"]})
        ancho = s if ancho is None else ancho.merge(s, on=["cve_mun", "anio"], how="outer")
    assert not ancho.duplicated(["cve_mun", "anio"]).any()
    ancho.sort_values(["anio", "cve_mun"]).to_csv(C2.CLEAN / "ice_zm_para_dml.csv", index=False)

    pob = con[con.anio.isin(C2.ANIOS_POB)][["cve_mun", "anio", "pob"]]
    out = pob[["cve_mun", "anio"]].copy()
    for e in C2.DELIMITACIONES:
        mp = asignar(geo23, delims[e], e, padre)[["cve_mun", "unidad"]]
        t = pob.merge(mp, on="cve_mun")
        t["log_pob"] = np.log(t.groupby(["unidad", "anio"]).pob.transform("sum"))
        out = out.merge(t[["cve_mun", "anio", "unidad", "log_pob"]].rename(
            columns={"unidad": f"unidad_{e}", "log_pob": f"log_pob_{e}"}), on=["cve_mun", "anio"])
    assert out.notna().all().all()
    out.to_csv(C2.CLEAN / "pob_unidad_conapo.csv", index=False)

    pd.DataFrame(diags).to_csv(C2.OUT / "diagnosticos_zm.csv", index=False)
    log(f"ice_zm_para_dml.csv: {len(ancho):,} filas | pob_unidad_conapo.csv: {len(out):,} filas")
    log.close()


if __name__ == "__main__":
    main()
