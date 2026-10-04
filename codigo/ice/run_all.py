"""Ejecuta el pipeline del ICE de principio a fin: python -m codigo.ice.run_all

Incluye la exportación de la base ecomplexity (Módulo 08, parte 1). Las gráficas
(Módulo 08, parte 2) se generan abriendo y ejecutando codigo/ice/08_graficas.ipynb.
anexo_tablas genera las tablas adicionales del Apéndice Metodológico (docs/anexo_ice.docx).
"""
import runpy
import time

MODULOS = ["01_limpieza_saic", "02_ice", "03_diagnostico_variables", "04_sensibilidad",
           "05_crosswalk_gadm_inegi", "06_validacion_externa", "07_export_dml",
           "export_ecomplexity", "anexo_tablas"]

if __name__ == "__main__":
    for m in MODULOS:
        t = time.time()
        print(f"\n{'=' * 70}\n>>> {m}\n{'=' * 70}")
        runpy.run_module(f"codigo.ice.{m}", run_name="__main__")
        print(f">>> {m} terminado en {time.time() - t:.0f} s")
