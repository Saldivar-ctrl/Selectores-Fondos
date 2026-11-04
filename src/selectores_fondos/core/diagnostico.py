"""Comprobación de dependencias (la usan --verificar y scripts/).

Solo LEE el sistema: no instala ni modifica nada.
"""

from __future__ import annotations

import importlib.util
import platform
import shutil
import sys

from ..platforms import ErrorBackend, crear_backend, sistema
from . import gestor_rutas


def ejecutar(config) -> list:
    """Devuelve una lista de (nivel, texto); nivel: 'ok', 'aviso' o 'error'."""
    r = []

    r.append(("ok", f"Sistema: {platform.platform()}"))
    r.append(("ok", f"Python {platform.python_version()} ({sys.executable})"))

    if sys.version_info < (3, 9):
        r.append(("error", "Se necesita Python 3.9 o superior (recomendado 3.12)."))

    if importlib.util.find_spec("PySide6") is None:
        r.append(("error", "Falta PySide6:  python -m pip install -r requirements.txt"))
    else:
        r.append(("ok", "PySide6 instalado"))

    if shutil.which("ffmpeg"):
        r.append(("ok", "ffmpeg encontrado (miniaturas de vídeo)"))
    else:
        r.append(("aviso",
                  "ffmpeg no encontrado: los vídeos mostrarán un cuadro gris "
                  "en vez de su miniatura."))

    sis = sistema()

    if sis not in ("linux", "windows"):
        r.append(("error", f"Sistema no soportado: {sys.platform}"))
        return r

    if sis == "linux" and importlib.util.find_spec("websockets") is None:
        r.append(("error", "Falta 'websockets':  python -m pip install -r requirements.txt"))

    try:
        backend = crear_backend(config)
    except ErrorBackend as error:
        r.append(("error", str(error)))
        return r

    estado = backend.comprobar()
    r.append(("ok" if estado.ok else "error", f"{backend.nombre}: {estado.mensaje}"))

    for detalle in estado.detalles:
        nivel = (
            "aviso" if detalle.startswith("AVISO")
            else "error" if detalle.startswith("FALTA")
            else "ok"
        )
        r.append((nivel, "  " + detalle))

    carpetas = gestor_rutas.carpetas_videos(config)

    for carpeta in carpetas:
        if carpeta.is_dir():
            r.append(("ok", f"Carpeta de fondos: {carpeta}"))
        else:
            r.append(("aviso", f"La carpeta de fondos no existe: {carpeta}"))

    r.append(("ok", f"Configuración: {config.archivo}"))

    if config.aviso:
        r.append(("aviso", config.aviso))

    return r
