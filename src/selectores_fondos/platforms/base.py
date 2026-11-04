"""Contrato común de los sistemas que aplican fondos animados.

Cada plataforma (waywallen, Wallpaper Engine, Lively) implementa Backend.
El resto del programa solo conoce esta interfaz, de modo que los dos
selectores funcionan igual con cualquiera.
"""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass, field


class ErrorBackend(Exception):
    """Error con un mensaje pensado para mostrarse al usuario tal cual."""


@dataclass
class Estado:
    ok: bool
    mensaje: str
    detalles: list = field(default_factory=list)


class Backend:
    id = ""
    nombre = ""
    # Qué tipos de fondo entiende (el gestor los busca solo si se usan)
    usa_wallpaper_engine = False
    usa_lively = False

    def __init__(self, config):
        self.config = config

    def comprobar(self) -> Estado:
        """Revisa dependencias y disponibilidad SIN modificar nada."""
        raise NotImplementedError

    def filtrar_registrados(self, fondos: list) -> list:
        """Deja solo los fondos que este sistema puede aplicar."""
        return fondos

    def aplicar(self, fondo) -> str:
        """Aplica el fondo. Devuelve un mensaje o lanza ErrorBackend."""
        raise NotImplementedError


def sin_ventana() -> int:
    """Evita que aparezca una consola negra al lanzar procesos en Windows."""
    return getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0
