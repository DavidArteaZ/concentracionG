"""03b_dml_percentil.py: robustez del DML con el ICE en percentiles (D26 propuesta).

Corre 03_dml.py sin modificarlo. Importa el módulo y reemplaza solo la
transformación del tratamiento:
  03 (principal): D = ICE estandarizado con pesos (media 0, DE 1; D15)
  03b (robustez): D = percentil ponderado del ICE entre las personas de la
                  muestra de análisis, en escala 0-100.

Regla del percentil (fijada antes de estimar, revision_ice_y_controles.md y
decision_percentil.md):
  - Distribución de referencia: personas de la muestra (n = 5,072), con el
    factor de expansión como peso.
  - Rango medio ponderado: para cada valor único v del ICE,
      pct(v) = 100 * [W(ICE < v) + W(ICE = v) / 2] / W_total.
    Los empates (misma unidad y mismo año interpolado) reciben el mismo valor.
  - beta se lee como percentiles de destino por 1 punto de percentil de ICE
    (pendiente rango-rango); x10 da el efecto de 10 puntos.

Todo lo demás (X, especificaciones principal/total, aprendices, rejillas,
semillas, 20 repeticiones, pliegues, SE agrupados, regla de elección y
agregación) es el del 03 con --ice v1. m(X) no depende de D, así que sus
predicciones deben coincidir con las de la corrida V1 (control de
reproducibilidad).

Uso (desde la raíz del proyecto):
  python codigo/modelo/03b_dml_percentil.py --fase 1 [--ice v1]
  python codigo/modelo/03b_dml_percentil.py --fase 2 [--ice v1]
Salidas: data/clean/03_resultados_percentil_<ice>/
"""
import argparse
import importlib.util
import json
from pathlib import Path

import numpy as np

AQUI = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("dml03", AQUI / "03_dml.py")
dml = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(dml)


def percentil_ponderado(d, w):
    """Rango medio ponderado en escala 0-100; empates con el mismo valor."""
    valores, inv = np.unique(d, return_inverse=True)
    w_val = np.bincount(inv, weights=w)
    debajo = np.concatenate([[0.0], np.cumsum(w_val)[:-1]])
    return (100 * (debajo + w_val / 2) / w.sum())[inv]


def tratamiento_percentil(base):
    w = base[dml.PESO].to_numpy(dtype=float)
    p = percentil_ponderado(base[dml.D_VAR].to_numpy(dtype=float), w)
    mu = np.average(p, weights=w)
    sd = np.sqrt(np.average((p - mu) ** 2, weights=w))
    return p, mu, sd


dml.tratamiento = tratamiento_percentil


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--fase", type=int, choices=[1, 2], required=True)
    ap.add_argument("--n-rep", type=int, default=dml.N_REP)
    ap.add_argument("--ice", choices=list(dml.VERSIONES_ICE), default="v1")
    args = ap.parse_args()
    dml.configurar_ice(args.ice)
    carpeta = f"03_resultados_percentil_{args.ice}"
    if args.n_rep != dml.N_REP:
        carpeta += "_prueba"
    salida = dml.RAIZ / "data" / "clean" / carpeta
    if args.fase == 1:
        dml.fase1(args.n_rep, salida)
        base, _ = dml.cargar()
        p, mu, sd = tratamiento_percentil(base)
        json.dump(dict(transformacion="percentil ponderado entre personas, rango medio, 0-100",
                       tratamiento_original=dml.D_VAR, media_pct=mu, de_pct=sd,
                       min_pct=float(p.min()), max_pct=float(p.max()),
                       valores_unicos=int(np.unique(p).size)),
                  open(salida / "transformacion_tratamiento.json", "w"), indent=2)
    else:
        dml.fase2(salida)
