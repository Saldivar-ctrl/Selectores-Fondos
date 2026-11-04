"""Elección del sistema que aplica los fondos según el sistema operativo.

  Linux    -> waywallen
  Windows  -> Wallpaper Engine (si se encuentra) o Lively Wallpaper
  macOS/otros -> no soportado

Los módulos de cada plataforma se importan solo cuando se necesitan, para
que nada específico de Windows se cargue en Linux y viceversa.
"""

from __future__ import annotations

import sys

from .base import Backend, ErrorBackend, Estado  # noqa: F401


def sistema() -> str:
    if sys.platform.startswith("linux"):
        return "linux"

    if sys.platform in ("win32", "cygwin"):
        return "windows"

    if sys.platform == "darwin":
        return "macos"

    return "otro"


def ids_validos() -> dict:
    """Ids de backend permitidos en cada sistema."""
    return {
        "linux": ("waywallen",),
        "windows": ("wallpaper_engine", "lively"),
    }.get(sistema(), ())


def crear_backend(config) -> Backend:
    elegido = config.backend
    sis = sistema()

    if sis not in ("linux", "windows"):
        raise ErrorBackend(
            f"Sistema no soportado ({sys.platform}). "
            "Solo se admiten Linux (waywallen) y Windows "
            "(Wallpaper Engine o Lively Wallpaper)."
        )

    if elegido == "auto":
        if sis == "linux":
            elegido = "waywallen"
        else:
            from .windows.wallpaper_engine import WallpaperEngineBackend

            # Wallpaper Engine si está instalado; si no, Lively si lo está
            if WallpaperEngineBackend(config).ejecutable() is not None:
                elegido = "wallpaper_engine"
            else:
                from .windows.lively_wallpaper import LivelyBackend

                elegido = (
                    "lively"
                    if LivelyBackend(config).ejecutable() is not None
                    else "wallpaper_engine"  # dará un error explicativo
                )

    if elegido not in ids_validos():
        raise ErrorBackend(
            f"El sistema '{elegido}' no se puede usar en {sis}. "
            f"Opciones válidas aquí: {', '.join(ids_validos())}."
        )

    if elegido == "waywallen":
        from .linux.waywallen import WaywallenBackend
        return WaywallenBackend(config)

    if elegido == "wallpaper_engine":
        from .windows.wallpaper_engine import WallpaperEngineBackend
        return WallpaperEngineBackend(config)

    from .windows.lively_wallpaper import LivelyBackend
    return LivelyBackend(config)
