"""Windows: Lively Wallpaper (alternativa gratuita y de código abierto).

Comunicación OFICIAL: línea de comandos documentada en
https://github.com/rocksdanister/lively/wiki/Command-Line-Controls

    Lively.exe setwp --file <archivo | carpeta con LivelyInfo.json>
                     [--monitor <n>]

La documentación oficial usa `livelycu.exe` (la utilidad de comandos); por eso
se busca primero. Que `Lively.exe` acepte los mismos argumentos NO está
confirmado en la documentación consultada (queda como segunda opción).
Los archivos de vídeo/imagen que no estén en la biblioteca de Lively se
importan solos, según la documentación.

Lively NO entiende los proyectos de Wallpaper Engine (project.json), por
eso este backend solo muestra vídeos, imágenes y carpetas de Lively.

Estado de verificación: sintaxis tomada de la documentación; las rutas de
instalación habituales son una suposición razonable (se pueden cambiar en
la configuración). NO se probó en un Windows real. Ver docs/PRUEBAS.md.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

from ...core import gestor_rutas
from ..base import Backend, ErrorBackend, Estado, sin_ventana
from .utiles import es_ejecutable_valido


class LivelyBackend(Backend):
    id = "lively"
    nombre = "Lively Wallpaper (Windows)"
    usa_lively = True

    def _candidatas(self):
        local = os.environ.get("LOCALAPPDATA", "")
        archivos = os.environ.get("ProgramFiles", "")

        for base in (local and Path(local) / "Programs" / "Lively Wallpaper",
                     archivos and Path(archivos) / "Lively Wallpaper"):
            if base:
                # Primero la utilidad de comandos documentada (livelycu);
                # Lively.exe queda como segunda opción (sin confirmar)
                yield base / "Livelycu.exe"
                yield base / "Lively.exe"

        for nombre in ("livelycu", "Lively"):
            encontrado = shutil.which(nombre)

            if encontrado:
                yield Path(encontrado)

    def ejecutable(self):
        if self.config.ruta_lively:
            ruta = gestor_rutas.expandir(self.config.ruta_lively)
            return ruta if es_ejecutable_valido(ruta) else None

        for ruta in self._candidatas():
            if es_ejecutable_valido(ruta):
                return ruta

        return None

    def comprobar(self) -> Estado:
        exe = self.ejecutable()

        if exe is None:
            return Estado(False, "No se encontró Lively Wallpaper", [
                "Instálalo desde https://github.com/rocksdanister/lively "
                "(o la Microsoft Store) e indica la ruta de Lively.exe en "
                "la configuración (tecla F2 en el selector).",
            ])

        return Estado(True, "Lively Wallpaper listo", [f"Ejecutable: {exe}"])

    def construir_comando(self, exe: Path, objetivo: str) -> list:
        comando = [str(exe), "setwp", "--file", str(objetivo)]

        if self.config.monitor.strip().isdigit():
            comando += ["--monitor", self.config.monitor.strip()]

        return comando

    def aplicar(self, fondo) -> str:
        exe = self.ejecutable()

        if exe is None:
            raise ErrorBackend(
                "No se encontró Lively Wallpaper. Instálalo o indica la ruta "
                "de Lively.exe en la configuración (F2)."
            )

        objetivo = fondo.proyecto or fondo.path

        if not os.path.exists(objetivo):
            raise ErrorBackend(f"El archivo ya no existe: {objetivo}")

        try:
            r = subprocess.run(
                self.construir_comando(exe, objetivo),
                capture_output=True, text=True, timeout=30,
                creationflags=sin_ventana(),
            )
        except (OSError, subprocess.TimeoutExpired) as error:
            raise ErrorBackend(f"Lively no respondió: {error}") from error

        if r.returncode != 0:
            raise ErrorBackend(
                "Lively devolvió un error: "
                + (r.stderr or r.stdout or f"código {r.returncode}").strip()
            )

        return f"Fondo enviado a Lively: {fondo.title or os.path.basename(objetivo)}"
