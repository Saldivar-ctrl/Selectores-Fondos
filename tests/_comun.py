"""Ayudas para las pruebas: ruta de importación y entorno aislado."""

import os
import sys
import tempfile
import unittest
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from selectores_fondos.core.configuracion import Configuracion  # noqa: E402


class CasoAislado(unittest.TestCase):
    """Cada prueba usa un HOME y una configuración temporales: no toca
    nada del usuario."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)

        self._env = {
            k: os.environ.get(k)
            for k in ("HOME", "XDG_CONFIG_HOME", "XDG_CACHE_HOME",
                      "SELECTORES_FONDOS_CONFIG", "APPDATA", "LOCALAPPDATA")
        }
        self.addCleanup(self._restaurar_env)

        os.environ["HOME"] = str(self.dir / "home")
        os.environ["XDG_CONFIG_HOME"] = str(self.dir / "home" / ".config")
        os.environ["XDG_CACHE_HOME"] = str(self.dir / "home" / ".cache")
        os.environ.pop("SELECTORES_FONDOS_CONFIG", None)
        (self.dir / "home").mkdir()

        self.config = Configuracion(archivo=self.dir / "cfg" / "config.json")

    def _restaurar_env(self):
        for k, v in self._env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
