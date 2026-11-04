"""Configuración persistente del usuario.

La configuración vive FUERA del código fuente, en un JSON por usuario:

  Linux:   $XDG_CONFIG_HOME/selectores-fondos/config.json
           (normalmente ~/.config/selectores-fondos/config.json)
  Windows: %APPDATA%\\SelectoresFondos\\config.json

Se puede usar otro archivo con la variable de entorno
SELECTORES_FONDOS_CONFIG (útil para pruebas o para una instalación portátil).

Este módulo no depende de Qt, así que se puede probar sin interfaz gráfica.
"""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass, field, fields
from pathlib import Path

ESQUEMA = 1
BACKENDS_VALIDOS = ("auto", "waywallen", "wallpaper_engine", "lively")
INTERFACES_VALIDAS = ("circular", "hexagonal")
MAX_HISTORIAL = 10


def directorio_config() -> Path:
    """Carpeta de configuración del usuario según el sistema operativo."""
    if os.name == "nt":
        base = os.environ.get("APPDATA") or (Path.home() / "AppData" / "Roaming")
        return Path(base) / "SelectoresFondos"

    base = os.environ.get("XDG_CONFIG_HOME") or (Path.home() / ".config")
    return Path(base) / "selectores-fondos"


def directorio_cache() -> Path:
    """Carpeta para miniaturas generadas (se puede borrar sin problema)."""
    if os.name == "nt":
        base = os.environ.get("LOCALAPPDATA") or (Path.home() / "AppData" / "Local")
        return Path(base) / "SelectoresFondos" / "cache"

    base = os.environ.get("XDG_CACHE_HOME") or (Path.home() / ".cache")
    return Path(base) / "selectores-fondos"


def archivo_config() -> Path:
    anulado = os.environ.get("SELECTORES_FONDOS_CONFIG")

    if anulado:
        return Path(anulado).expanduser()

    return directorio_config() / "config.json"


@dataclass
class Configuracion:
    # --- Sistema que aplica los fondos ---
    # "auto" elige según el sistema operativo (ver platforms/__init__.py)
    backend: str = "auto"
    # Selector que se abre si no se indica otro
    interfaz: str = "circular"

    # --- Rutas ---
    # Carpetas con vídeos/imágenes. Vacío = <Vídeos>/fondos
    carpetas_videos: list = field(default_factory=list)
    # Bibliotecas de Steam extra (donde Wallpaper Engine guarda sus fondos)
    carpetas_steam: list = field(default_factory=list)
    ruta_wallpaper_engine: str = ""   # wallpaper64.exe / wallpaper32.exe
    ruta_lively: str = ""             # Lively.exe o livelycu.exe
    monitor: str = ""                 # índice de monitor (vacío = predeterminado)

    # --- Modo oculto ---
    # Carpetas cuyo CONTENIDO (por nombre) se oculta; ver gestor_fondos.py
    carpetas_ocultas: list = field(default_factory=list)
    # Números de carpeta de Steam, títulos o nombres de archivo a ocultar
    fondos_ocultos: list = field(default_factory=list)
    modo_oculto_habilitado: bool = True
    # Verificador de la contraseña (sal + hash PBKDF2). Nunca texto plano.
    autenticacion: dict = field(default_factory=dict)

    # --- Waywallen ---
    # Muestra solo los fondos de Wallpaper Engine que Waywallen tiene
    # registrados (así todos los visibles se pueden aplicar)
    ocultar_no_registrados: bool = True

    # --- Estado ---
    ultimo_fondo: str = ""
    historial: list = field(default_factory=list)

    # No se guardan en el JSON
    archivo: Path = field(default_factory=archivo_config, repr=False, compare=False)
    aviso: str = field(default="", repr=False, compare=False)

    # ------------------------------------------------------------------
    @classmethod
    def cargar(cls, ruta=None) -> "Configuracion":
        """Lee la configuración. Un archivo ausente o dañado no es un error:
        se usan los valores por defecto y se deja un aviso legible."""
        ruta = Path(ruta) if ruta else archivo_config()
        config = cls(archivo=ruta)

        try:
            with open(ruta, "r", encoding="utf-8-sig") as f:
                datos = json.load(f)
        except FileNotFoundError:
            return config
        except (OSError, ValueError) as error:
            config.aviso = (
                f"No se pudo leer {ruta}: {error}. "
                "Se usan los valores por defecto."
            )
            return config

        if not isinstance(datos, dict):
            config.aviso = f"{ruta} no tiene el formato esperado; se ignora."
            return config

        config._aplicar(datos)
        return config

    def _claves_guardables(self):
        return [f.name for f in fields(self) if f.name not in ("archivo", "aviso")]

    def _aplicar(self, datos: dict):
        for nombre in self._claves_guardables():
            if nombre not in datos:
                continue

            actual = getattr(self, nombre)
            valor = datos[nombre]

            if isinstance(actual, bool):
                if isinstance(valor, bool):
                    setattr(self, nombre, valor)
            elif isinstance(actual, str):
                if isinstance(valor, str):
                    setattr(self, nombre, valor)
            elif isinstance(actual, list):
                if isinstance(valor, list):
                    setattr(self, nombre, [str(x) for x in valor])
            elif isinstance(actual, dict):
                if isinstance(valor, dict):
                    setattr(self, nombre, valor)

        if self.backend not in BACKENDS_VALIDOS:
            self.backend = "auto"

        if self.interfaz not in INTERFACES_VALIDAS:
            self.interfaz = "circular"

    def a_dict(self) -> dict:
        return {nombre: getattr(self, nombre) for nombre in self._claves_guardables()}

    def guardar(self):
        """Escritura atómica: nunca deja un JSON a medias."""
        self.archivo.parent.mkdir(parents=True, exist_ok=True)

        datos = {"esquema": ESQUEMA, **self.a_dict()}

        fd, temporal = tempfile.mkstemp(
            dir=self.archivo.parent, prefix=".config-", suffix=".tmp"
        )

        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(datos, f, ensure_ascii=False, indent=2)

            if os.name != "nt":
                os.chmod(temporal, 0o600)  # contiene el verificador

            os.replace(temporal, self.archivo)

        except BaseException:
            try:
                os.unlink(temporal)
            except OSError:
                pass
            raise

    # ------------------------------------------------------------------
    def carpetas_ocultas_efectivas(self) -> list:
        """Carpeta de privados junto al config.json + las del usuario."""
        return [str(self.archivo.parent / "privados")] + list(self.carpetas_ocultas)

    def registrar_aplicado(self, ruta: str):
        """Guarda el fondo aplicado y recuerda el anterior (para restaurarlo)."""
        previo = self.ultimo_fondo
        resto = [r for r in self.historial if r not in (ruta, previo)]

        self.historial = (
            ([previo] if previo and previo != ruta else []) + resto
        )[:MAX_HISTORIAL]

        self.ultimo_fondo = ruta

    def fondo_anterior(self) -> str:
        return self.historial[0] if self.historial else ""
