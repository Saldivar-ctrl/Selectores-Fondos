"""Lista y aplica fondos. Es el "cerebro" que comparten los dos selectores.

Fuentes de fondos:
  1. Archivos de vídeo/imagen en las carpetas del usuario.
  2. Wallpaper Engine (proyectos con project.json en las bibliotecas de
     Steam), si el sistema elegido los entiende.
  3. Carpetas de Lively (LivelyInfo.json), si se usa Lively.

Modo oculto: un fondo es "privado" si su nombre de archivo, su número de
carpeta de Steam o su título aparece en `fondos_ocultos`, o si existe una
entrada con ese nombre dentro de alguna carpeta de `carpetas_ocultas`
(basta con crear una carpeta o un archivo VACÍO con ese nombre).
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

from ..platforms import ErrorBackend, crear_backend
from . import gestor_rutas

VIDEO_EXT = (".mp4", ".mkv", ".webm", ".avi", ".mov")
IMAGE_EXT = (".jpg", ".jpeg", ".png", ".webp")


@dataclass
class Fondo:
    path: str              # archivo principal (lo que usa waywallen)
    preview: str = ""      # imagen de vista previa (Wallpaper Engine/Lively)
    title: str = ""
    id: str = ""           # número de carpeta de Steam, si lo tiene
    tipo: str = ""         # "video", "imagen", "wallpaper_engine", "lively"
    oculto: bool = False
    proyecto: str = ""     # project.json / carpeta Lively (para esos backends)


class GestorFondos:

    def __init__(self, config, backend=None):
        self.config = config
        self._backend = backend

    # ------------------------------------------------------------ backend
    @property
    def backend(self):
        if self._backend is None:
            self._backend = crear_backend(self.config)

        return self._backend

    def reiniciar_backend(self):
        """Volver a elegir el backend (p. ej. tras cambiar la configuración)."""
        self._backend = None

    def _backend_o_none(self):
        try:
            return self.backend
        except ErrorBackend:
            return None

    # -------------------------------------------------------- modo oculto
    def nombres_ocultos(self) -> set:
        nombres = {
            str(x).strip().casefold() for x in self.config.fondos_ocultos
        }

        for carpeta in self.config.carpetas_ocultas_efectivas():
            carpeta = gestor_rutas.expandir(carpeta)

            if carpeta.is_dir():
                for entrada in os.listdir(carpeta):
                    nombres.add(entrada.casefold())
                    nombres.add(os.path.splitext(entrada)[0].casefold())

        return nombres

    # ------------------------------------------------------------ listado
    def archivos_locales(self, mostrar_ocultos=False) -> list:
        privados = self.nombres_ocultos()
        fondos, vistos = [], set()

        for carpeta in gestor_rutas.carpetas_videos(self.config):
            if not carpeta.is_dir():
                continue

            for nombre in sorted(os.listdir(carpeta)):
                ruta = carpeta / nombre
                ext = ruta.suffix.lower()

                if ext not in VIDEO_EXT + IMAGE_EXT or not ruta.is_file():
                    continue

                real = os.path.realpath(ruta)

                if real in vistos:
                    continue

                oculto = (
                    nombre.casefold() in privados
                    or ruta.stem.casefold() in privados
                )

                if oculto and not mostrar_ocultos:
                    continue

                vistos.add(real)
                fondos.append(Fondo(
                    path=str(ruta),
                    title=ruta.stem,
                    tipo="video" if ext in VIDEO_EXT else "imagen",
                    oculto=oculto,
                ))

        return fondos

    def proyectos_wallpaper_engine(self, mostrar_ocultos=False) -> list:
        """Cada fondo es una carpeta con un project.json que indica su
        archivo principal, su vista previa y su título."""
        privados = self.nombres_ocultos()
        fondos = []

        for carpeta in gestor_rutas.carpetas_wallpaper_engine(self.config):

            for nombre in sorted(os.listdir(carpeta)):

                directorio = carpeta / nombre
                proyecto = directorio / "project.json"

                if not proyecto.is_file():
                    continue

                try:
                    with open(proyecto, "r", encoding="utf-8-sig") as f:
                        datos = json.load(f)
                except Exception:
                    continue

                if not isinstance(datos, dict):
                    continue

                principal = datos.get("file") or ""
                ruta = directorio / principal if principal else proyecto

                if not ruta.is_file():
                    ruta = proyecto

                vista = datos.get("preview") or ""
                vista = directorio / vista if vista else None

                titulo = str(datos.get("title") or nombre)

                oculto = (
                    nombre.casefold() in privados
                    or titulo.casefold() in privados
                )

                # Los ocultos no se muestran ni se consultan en el backend
                if oculto and not mostrar_ocultos:
                    continue

                fondos.append(Fondo(
                    path=str(ruta),
                    preview=str(vista) if vista and vista.is_file() else "",
                    title=titulo,
                    id=nombre,
                    tipo="wallpaper_engine",
                    oculto=oculto,
                    proyecto=str(proyecto),
                ))

        fondos.sort(key=lambda f: f.title.casefold())

        return fondos

    def carpetas_lively(self, mostrar_ocultos=False) -> list:
        privados = self.nombres_ocultos()
        fondos = []

        for carpeta in gestor_rutas.carpetas_videos(self.config):
            if not carpeta.is_dir():
                continue

            for nombre in sorted(os.listdir(carpeta)):
                directorio = carpeta / nombre
                info = directorio / "LivelyInfo.json"

                if not info.is_file():
                    continue

                try:
                    with open(info, "r", encoding="utf-8-sig") as f:
                        datos = json.load(f)
                except Exception:
                    datos = {}

                titulo = str(datos.get("Title") or nombre) if isinstance(datos, dict) else nombre
                miniatura = directorio / str(datos.get("Thumbnail") or "") \
                    if isinstance(datos, dict) and datos.get("Thumbnail") else None

                oculto = (
                    nombre.casefold() in privados
                    or titulo.casefold() in privados
                )

                if oculto and not mostrar_ocultos:
                    continue

                fondos.append(Fondo(
                    path=str(directorio),
                    preview=str(miniatura) if miniatura and miniatura.is_file() else "",
                    title=titulo,
                    tipo="lively",
                    oculto=oculto,
                    proyecto=str(directorio),
                ))

        return fondos

    def listar(self, mostrar_ocultos=False) -> list:
        """Fondos que se mostrarán, en el orden en que aparecen."""
        backend = self._backend_o_none()

        # Los archivos sueltos de Lively no son carpetas: se listan igual
        fondos = self.archivos_locales(mostrar_ocultos)

        if backend is not None and backend.usa_wallpaper_engine:
            fondos += backend.filtrar_registrados(
                self.proyectos_wallpaper_engine(mostrar_ocultos)
            )

        if backend is not None and backend.usa_lively:
            fondos += self.carpetas_lively(mostrar_ocultos)

        return fondos

    # ------------------------------------------------------------ acciones
    def aplicar(self, fondo) -> str:
        mensaje = self.backend.aplicar(fondo)

        self.config.registrar_aplicado(fondo.path)

        try:
            self.config.guardar()
        except OSError as error:
            mensaje += f" (no se pudo guardar el historial: {error})"

        return mensaje

    def restaurar_anterior(self) -> str:
        """Vuelve a aplicar el fondo que estaba antes del actual."""
        ruta = self.config.fondo_anterior()

        if not ruta:
            raise ErrorBackend("Todavía no hay un fondo anterior que restaurar.")

        fondo = next(
            (f for f in self.listar(mostrar_ocultos=True) if f.path == ruta),
            None,
        )

        if fondo is None:
            if not os.path.exists(ruta):
                raise ErrorBackend(f"El fondo anterior ya no existe: {ruta}")

            fondo = Fondo(path=ruta, title=Path(ruta).stem)

        return self.aplicar(fondo)
