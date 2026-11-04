"""Windows: Wallpaper Engine (Steam).

Comunicación OFICIAL: línea de comandos documentada en
https://help.wallpaperengine.io/en/functionality/cli.html

    wallpaper64.exe -control openWallpaper -file <project.json | archivo>
                    [-monitor <n>]

Wallpaper Engine debe estar en ejecución para aceptar el comando; si no
lo está, este backend lo inicia y espera unos segundos.

Estado de verificación: el comando está tomado de la documentación oficial,
pero NO se pudo probar en un Windows real (el autor trabaja en Linux).
Consulta docs/PRUEBAS.md.
"""

from __future__ import annotations

import os
import subprocess
import time
from pathlib import Path

from ...core import gestor_rutas
from ..base import Backend, ErrorBackend, Estado, sin_ventana
from .utiles import es_ejecutable_valido, proceso_en_ejecucion

EXE_NAMES = ("wallpaper64.exe", "wallpaper32.exe")
ESPERA_ARRANQUE = 15  # segundos


class WallpaperEngineBackend(Backend):
    id = "wallpaper_engine"
    nombre = "Wallpaper Engine (Windows)"
    usa_wallpaper_engine = True

    def ejecutable(self):
        """Ruta del .exe: la configurada o la hallada en las bibliotecas de Steam."""
        if self.config.ruta_wallpaper_engine:
            ruta = gestor_rutas.expandir(self.config.ruta_wallpaper_engine)
            return ruta if es_ejecutable_valido(ruta) else None

        for instalacion in gestor_rutas.instalaciones_wallpaper_engine(self.config):
            for nombre in EXE_NAMES:
                ruta = instalacion / nombre

                if ruta.is_file():
                    return ruta

        return None

    def comprobar(self) -> Estado:
        exe = self.ejecutable()

        if exe is None:
            return Estado(False, "No se encontró Wallpaper Engine", [
                "Instálalo desde Steam o indica la ruta de wallpaper64.exe "
                "en la configuración (tecla F2 en el selector).",
                "Ruta habitual: C:\\Program Files (x86)\\Steam\\steamapps\\"
                "common\\wallpaper_engine\\wallpaper64.exe",
            ])

        detalles = [f"Ejecutable: {exe}"]
        detalles.append(
            "Wallpaper Engine está en ejecución."
            if proceso_en_ejecucion(EXE_NAMES)
            else "Wallpaper Engine no está en ejecución (se iniciará al aplicar un fondo)."
        )

        return Estado(True, "Wallpaper Engine listo", detalles)

    def _asegurar_en_ejecucion(self, exe: Path):
        if proceso_en_ejecucion(EXE_NAMES):
            return

        try:
            subprocess.Popen(
                [str(exe)], cwd=str(exe.parent),
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                creationflags=sin_ventana(),
            )
        except OSError as error:
            raise ErrorBackend(
                f"No se pudo iniciar Wallpaper Engine ({exe}): {error}"
            ) from error

        limite = time.time() + ESPERA_ARRANQUE

        while time.time() < limite:
            if proceso_en_ejecucion(EXE_NAMES):
                time.sleep(2)  # deja que termine de arrancar
                return
            time.sleep(0.5)

        raise ErrorBackend(
            "Wallpaper Engine no arrancó a tiempo. Ábrelo manualmente "
            "y vuelve a intentarlo."
        )

    def construir_comando(self, exe: Path, objetivo: str) -> list:
        comando = [str(exe), "-control", "openWallpaper", "-file", str(objetivo)]

        if self.config.monitor.strip().isdigit():
            comando += ["-monitor", self.config.monitor.strip()]

        return comando

    def aplicar(self, fondo) -> str:
        exe = self.ejecutable()

        if exe is None:
            raise ErrorBackend(
                "No se encontró Wallpaper Engine. Instálalo o indica la ruta "
                "de wallpaper64.exe en la configuración (F2)."
            )

        # Wallpaper Engine acepta el project.json (o un archivo suelto)
        objetivo = fondo.proyecto or fondo.path

        if not os.path.exists(objetivo):
            raise ErrorBackend(f"El archivo ya no existe: {objetivo}")

        self._asegurar_en_ejecucion(exe)

        try:
            r = subprocess.run(
                self.construir_comando(exe, objetivo),
                capture_output=True, text=True, timeout=20,
                creationflags=sin_ventana(),
            )
        except (OSError, subprocess.TimeoutExpired) as error:
            raise ErrorBackend(
                f"Wallpaper Engine no respondió: {error}"
            ) from error

        if r.returncode != 0:
            raise ErrorBackend(
                "Wallpaper Engine devolvió un error: "
                + (r.stderr or r.stdout or f"código {r.returncode}").strip()
            )

        return f"Fondo enviado a Wallpaper Engine: {fondo.title or os.path.basename(objetivo)}"
