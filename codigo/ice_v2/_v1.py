"""Carga el paquete del ICE V1 por ruta.

Los scripts de V2 se corren como archivos (python codigo/ice_v2/02_ice_zm.py),
no como módulos de `codigo`, así que codigo/ice_v1 se registra por ruta como
paquete `ice_v1` para reutilizar sus funciones (calcular_ice, matriz, Log) sin
copiarlas: V2 usa exactamente el mismo algoritmo que V1.
"""
import importlib
import importlib.util
import sys

import config_v2 as C2


def cargar():
    if "ice_v1" not in sys.modules:
        spec = importlib.util.spec_from_file_location(
            "ice_v1", C2.V1_DIR / "__init__.py", submodule_search_locations=[str(C2.V1_DIR)])
        mod = importlib.util.module_from_spec(spec)
        sys.modules["ice_v1"] = mod
        spec.loader.exec_module(mod)
    config = importlib.import_module("ice_v1.config")
    utils = importlib.import_module("ice_v1.utils")
    return config, utils
