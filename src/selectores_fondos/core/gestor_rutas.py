"""Rutas del sistema: carpetas de vídeos, bibliotecas de Steam y de
Wallpaper Engine. Todo se resuelve con pathlib, así que los espacios, los
acentos (p. ej. "Vídeos") y las barras de Windows/Linux no son un problema.

Es el único módulo que sabe dónde suele estar cada cosa; si cambias una
ruta por defecto, hazlo aquí.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

WALLPAPER_ENGINE_APP_ID = "431960"


def expandir(ruta) -> Path:
    """~ y variables de entorno -> Path."""
    return Path(os.path.expandvars(os.path.expanduser(str(ruta))))


def _sin_repetir(rutas):
    vistas, salida = set(), []

    for ruta in rutas:
        try:
            clave = os.path.realpath(ruta)
        except OSError:
            clave = str(ruta)

        if clave not in vistas:
            vistas.add(clave)
            salida.append(Path(ruta))

    return salida


# ---------------------------------------------------------------- vídeos
def carpeta_videos_del_sistema() -> Path:
    """Carpeta "Vídeos" del usuario (en Linux respeta user-dirs.dirs)."""
    if os.name != "nt":
        base = os.environ.get("XDG_CONFIG_HOME") or (Path.home() / ".config")
        archivo = Path(base) / "user-dirs.dirs"

        try:
            for linea in archivo.read_text(encoding="utf-8").splitlines():
                m = re.match(r'\s*XDG_VIDEOS_DIR\s*=\s*"?(.*?)"?\s*$', linea)

                if m:
                    return Path(m.group(1).replace("$HOME", str(Path.home())))
        except OSError:
            pass

    return Path.home() / "Videos"


def carpetas_videos(config) -> list:
    """Carpetas configuradas o, si no hay ninguna, <Vídeos>/fondos."""
    if config.carpetas_videos:
        rutas = [expandir(r) for r in config.carpetas_videos]
    else:
        rutas = [carpeta_videos_del_sistema() / "fondos"]

    return _sin_repetir(rutas)


# ----------------------------------------------------------------- Steam
def _raices_steam() -> list:
    home = Path.home()
    raices = []

    if os.name == "nt":
        try:
            import winreg

            for hive, clave_reg, valor in (
                (winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam", "SteamPath"),
                (winreg.HKEY_LOCAL_MACHINE,
                 r"SOFTWARE\WOW6432Node\Valve\Steam", "InstallPath"),
            ):
                try:
                    with winreg.OpenKey(hive, clave_reg) as clave:
                        raices.append(Path(winreg.QueryValueEx(clave, valor)[0]))
                except OSError:
                    pass
        except ImportError:
            pass

        for variable in ("ProgramFiles(x86)", "ProgramFiles"):
            base = os.environ.get(variable)

            if base:
                raices.append(Path(base) / "Steam")
    else:
        raices += [
            home / ".steam" / "steam",
            home / ".local" / "share" / "Steam",
            home / ".var" / "app" / "com.valvesoftware.Steam"
            / ".local" / "share" / "Steam",
        ]

    return raices


def leer_bibliotecas_vdf(vdf: Path) -> list:
    """Rutas de las bibliotecas listadas en steamapps/libraryfolders.vdf."""
    try:
        texto = Path(vdf).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []

    return [
        Path(m.group(1).replace("\\\\", "\\"))
        for m in re.finditer(r'"path"\s+"([^"]+)"', texto)
    ]


def bibliotecas_steam(config) -> list:
    """Todas las bibliotecas de Steam que existen (raíces + extras)."""
    candidatas = []

    for raiz in _raices_steam():
        if raiz.is_dir():
            candidatas.append(raiz)
            candidatas += leer_bibliotecas_vdf(
                raiz / "steamapps" / "libraryfolders.vdf"
            )

    candidatas += [expandir(r) for r in config.carpetas_steam]

    return [r for r in _sin_repetir(candidatas) if r.is_dir()]


def carpetas_wallpaper_engine(config) -> list:
    """Carpetas donde buscar fondos de Wallpaper Engine (project.json)."""
    rutas = []

    for biblioteca in bibliotecas_steam(config):
        pasos = biblioteca / "steamapps"
        proyectos = pasos / "common" / "wallpaper_engine" / "projects"

        rutas += [
            proyectos / "defaultprojects",
            proyectos / "myprojects",
            pasos / "workshop" / "content" / WALLPAPER_ENGINE_APP_ID,
        ]

    return [r for r in _sin_repetir(rutas) if r.is_dir()]


def instalaciones_wallpaper_engine(config) -> list:
    """Carpetas de instalación de Wallpaper Engine (donde está el .exe)."""
    return [
        b / "steamapps" / "common" / "wallpaper_engine"
        for b in bibliotecas_steam(config)
        if (b / "steamapps" / "common" / "wallpaper_engine").is_dir()
    ]
