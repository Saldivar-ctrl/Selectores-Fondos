"""Piezas gráficas que comparten los dos selectores.

  - ThumbnailLoader: miniaturas de vídeo con ffmpeg, en segundo plano.
  - alternar_ocultos: lógica de Ctrl+Shift+H (contraseña y modo oculto).
  - avisar / abrir_configuracion / restaurar_anterior: acciones de teclado.
"""

from __future__ import annotations

import hashlib
import os
import shutil
import subprocess

from PySide6.QtCore import QObject, QRunnable, Signal
from PySide6.QtGui import QImage
from PySide6.QtWidgets import QMessageBox

from ..core import autenticacion
from ..core.configuracion import directorio_cache
from ..platforms.base import sin_ventana
from .dialogo_contrasena import pedir_contrasena


class ThumbnailSignals(QObject):

    loaded = Signal(object, object)


class ThumbnailLoader(QRunnable):
    """Saca un fotograma del vídeo con ffmpeg y lo guarda en la caché.

    Si ffmpeg no está instalado, el cuadro gris provisional se queda
    (no es un error: solo no hay miniatura)."""

    def __init__(self, path, item):
        super().__init__()

        self.path = path
        self.item = item
        self.signals = ThumbnailSignals()

    def _archivo_cache(self):
        try:
            marca = str(os.path.getmtime(self.path))
        except OSError:
            marca = ""

        # Ruta completa + fecha: dos vídeos con el mismo nombre en carpetas
        # distintas no se pisan la miniatura
        clave = hashlib.sha1(
            (os.path.abspath(self.path) + marca).encode("utf-8")
        ).hexdigest()

        return directorio_cache() / "miniaturas" / (clave + ".jpg")

    def run(self):

        thumb = self._archivo_cache()

        if not thumb.exists():

            ffmpeg = shutil.which("ffmpeg")

            if not ffmpeg:
                return

            thumb.parent.mkdir(parents=True, exist_ok=True)

            try:
                subprocess.run(
                    [
                        ffmpeg, "-y", "-loglevel", "error",
                        "-ss", "00:00:00.5",
                        "-i", self.path,
                        "-vframes", "1",
                        str(thumb),
                    ],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=60,
                    creationflags=sin_ventana(),
                )
            except (OSError, subprocess.TimeoutExpired):
                return

        image = QImage(str(thumb))

        if not image.isNull():

            self.signals.loaded.emit(self.item, image)


def avisar(parent, titulo, texto):
    QMessageBox.warning(parent, titulo, texto)


def alternar_ocultos(vista) -> bool:
    """Ctrl+Shift+H. Devuelve True si cambió lo que hay que mostrar.

    - Si los privados ya se ven, se vuelven a ocultar (sin contraseña).
    - Si aún no hay contraseña (se crea con F2) o los datos faltan o fueron
      alterados, no pasa nada.
    - Si hay contraseña y es incorrecta, no pasa nada y no se avisa de nada.
    """
    config = vista.gestor.config

    if vista.show_hidden:
        vista.show_hidden = False
        return True

    if not config.modo_oculto_habilitado:
        return False

    situacion = autenticacion.estado(config)

    if situacion == "bloqueada":
        # Faltan o fueron alterados los datos de la contraseña: no se abre
        return False

    if situacion == "nueva":
        # Aún no hay contraseña: se crea desde F2, no desde aquí
        return False

    texto = pedir_contrasena(vista)

    if texto is None or not autenticacion.verificar(texto, config.autenticacion):
        return False

    vista.show_hidden = True
    return True


def crear_contrasena(parent, config=None):
    """Pide una contraseña nueva (dos veces) y la guarda. None si se cancela."""
    if config is None:
        config = parent.gestor.config

    primera = pedir_contrasena(parent, "Nueva contraseña")

    if primera is None:
        return None

    segunda = pedir_contrasena(parent, "Repite la contraseña")

    if segunda is None:
        return None

    if primera != segunda:
        avisar(parent, "Contraseña", "Las contraseñas no coinciden.")
        return None

    try:
        autenticacion.establecer(config, primera)
    except ValueError as error:
        avisar(parent, "Contraseña", str(error))
        return None

    try:
        config.guardar()
    except OSError as error:
        avisar(parent, "Contraseña",
               f"No se pudo guardar la configuración: {error}")
        return None

    return primera


def abrir_configuracion(vista):
    from .dialogo_configuracion import DialogoConfiguracion

    dialogo = DialogoConfiguracion(vista, vista.gestor.config)

    if dialogo.exec():
        vista.gestor.reiniciar_backend()
        vista.reload_wallpapers()


def restaurar_anterior(vista):
    try:
        mensaje = vista.gestor.restaurar_anterior()
    except Exception as error:
        print(f"No se pudo restaurar el fondo anterior: {error}")
        avisar(vista, "No se pudo restaurar el fondo anterior", str(error))
        return

    print(mensaje)
    vista.close()
