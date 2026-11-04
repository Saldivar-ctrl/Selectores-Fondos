"""Utilidades de Windows (solo se importa desde los backends de Windows)."""

from __future__ import annotations

import subprocess

from ..base import sin_ventana


def proceso_en_ejecucion(nombres) -> bool:
    """True si alguno de los .exe está corriendo (usa tasklist, incluido
    en Windows; no necesita permisos de administrador)."""
    for nombre in nombres:
        try:
            r = subprocess.run(
                ["tasklist", "/FI", f"IMAGENAME eq {nombre}", "/FO", "CSV", "/NH"],
                capture_output=True, text=True, timeout=10,
                creationflags=sin_ventana(),
            )
        except (OSError, subprocess.TimeoutExpired):
            continue

        if nombre.lower() in r.stdout.lower():
            return True

    return False


def es_ejecutable_valido(ruta) -> bool:
    """Un archivo existente terminado en .exe (nada de carpetas ni scripts)."""
    return ruta.is_file() and ruta.suffix.lower() == ".exe"
