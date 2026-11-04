"""Ventana de configuración (tecla F2 en cualquiera de los selectores).

Permite cambiar rutas, el sistema de fondos y la contraseña sin tocar el
código ni editar JSON a mano. Se guarda en config.json (ver
core/configuracion.py).
"""

from __future__ import annotations

import os

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ..core import autenticacion
from ..core.configuracion import BACKENDS_VALIDOS
from ..platforms import ids_validos
from .comun import avisar, crear_contrasena
from .dialogo_contrasena import pedir_contrasena

NOMBRES_BACKEND = {
    "auto": "Automático (según tu sistema)",
    "waywallen": "waywallen (Linux)",
    "wallpaper_engine": "Wallpaper Engine (Windows)",
    "lively": "Lively Wallpaper (Windows)",
}


class ListaRutas(QWidget):
    """Lista de carpetas con botones Añadir / Quitar."""

    def __init__(self, rutas, parent=None):
        super().__init__(parent)

        self.lista = QListWidget()
        self.lista.addItems(rutas)
        self.lista.setMaximumHeight(90)

        anadir = QPushButton("Añadir…")
        quitar = QPushButton("Quitar")
        anadir.clicked.connect(self._anadir)
        quitar.clicked.connect(self._quitar)

        botones = QVBoxLayout()
        botones.addWidget(anadir)
        botones.addWidget(quitar)
        botones.addStretch()

        disposicion = QHBoxLayout(self)
        disposicion.setContentsMargins(0, 0, 0, 0)
        disposicion.addWidget(self.lista)
        disposicion.addLayout(botones)

    def _anadir(self):
        carpeta = QFileDialog.getExistingDirectory(self, "Elige una carpeta")

        if carpeta:
            self.lista.addItem(carpeta)

    def _quitar(self):
        for item in self.lista.selectedItems():
            self.lista.takeItem(self.lista.row(item))

    def rutas(self):
        return [self.lista.item(i).text() for i in range(self.lista.count())]


class CampoArchivo(QWidget):
    """Línea de texto + botón Examinar para elegir un ejecutable."""

    def __init__(self, valor, filtro, parent=None):
        super().__init__(parent)

        self.filtro = filtro
        self.texto = QLineEdit(valor)

        examinar = QPushButton("Examinar…")
        examinar.clicked.connect(self._examinar)

        disposicion = QHBoxLayout(self)
        disposicion.setContentsMargins(0, 0, 0, 0)
        disposicion.addWidget(self.texto)
        disposicion.addWidget(examinar)

    def _examinar(self):
        ruta, _ = QFileDialog.getOpenFileName(
            self, "Elige el archivo", os.path.dirname(self.texto.text()),
            self.filtro,
        )

        if ruta:
            self.texto.setText(ruta)


class DialogoConfiguracion(QDialog):

    def __init__(self, parent, config):
        super().__init__(parent)

        self.config = config
        self.setWindowTitle("Configuración")
        self.setMinimumWidth(560)

        # Sistema de fondos
        self.backend = QComboBox()
        permitidos = ("auto",) + tuple(ids_validos())

        for ident in BACKENDS_VALIDOS:
            if ident in permitidos:
                self.backend.addItem(NOMBRES_BACKEND[ident], ident)

        indice = self.backend.findData(config.backend)
        self.backend.setCurrentIndex(max(0, indice))

        self.videos = ListaRutas(config.carpetas_videos)
        self.steam = ListaRutas(config.carpetas_steam)

        filtro_exe = (
            "Ejecutables (*.exe)" if os.name == "nt" else "Todos (*)"
        )
        self.ruta_we = CampoArchivo(config.ruta_wallpaper_engine, filtro_exe)
        self.ruta_lively = CampoArchivo(config.ruta_lively, filtro_exe)

        self.monitor = QLineEdit(config.monitor)
        self.monitor.setPlaceholderText("vacío = predeterminado")

        self.solo_registrados = QCheckBox(
            "Mostrar solo fondos de Wallpaper Engine registrados en waywallen"
        )
        self.solo_registrados.setChecked(config.ocultar_no_registrados)

        self.modo_oculto = QCheckBox("Habilitar el modo oculto (Ctrl+Shift+H)")
        self.modo_oculto.setChecked(config.modo_oculto_habilitado)

        cambiar = QPushButton("Cambiar contraseña…")
        cambiar.clicked.connect(self._cambiar_contrasena)

        formulario = QFormLayout()
        formulario.addRow("Sistema de fondos", self.backend)
        formulario.addRow("Carpetas de vídeos\ne imágenes", self.videos)
        formulario.addRow("Bibliotecas de\nSteam extra", self.steam)
        formulario.addRow("Wallpaper Engine", self.ruta_we)
        formulario.addRow("Lively Wallpaper", self.ruta_lively)
        formulario.addRow("Monitor", self.monitor)
        formulario.addRow("", self.solo_registrados)
        formulario.addRow("", self.modo_oculto)
        formulario.addRow("", cambiar)

        nota = QLabel(
            "Los cambios se aplican al pulsar Guardar.\n"
            f"Archivo: {config.archivo}"
        )
        nota.setStyleSheet("color: gray;")

        botones = QDialogButtonBox(
            QDialogButtonBox.Save | QDialogButtonBox.Cancel
        )
        botones.accepted.connect(self._guardar)
        botones.rejected.connect(self.reject)

        disposicion = QVBoxLayout(self)
        disposicion.addLayout(formulario)
        disposicion.addWidget(nota)
        disposicion.addWidget(botones)

    def _cambiar_contrasena(self):
        situacion = autenticacion.estado(self.config)

        if situacion == "bloqueada":
            avisar(self, "Contraseña",
                   "Los datos de la contraseña faltan o fueron alterados. "
                   "No se puede cambiar.")
            return

        if situacion == "ok":
            actual = pedir_contrasena(self, "Contraseña actual")

            if actual is None:
                return

            if not autenticacion.verificar(actual, self.config.autenticacion):
                avisar(self, "Contraseña", "La contraseña actual no es correcta.")
                return

        if crear_contrasena(self, self.config) is not None:
            avisar(self, "Contraseña", "Contraseña actualizada.")

    def _guardar(self):
        self.config.backend = self.backend.currentData()
        self.config.carpetas_videos = self.videos.rutas()
        self.config.carpetas_steam = self.steam.rutas()
        self.config.ruta_wallpaper_engine = self.ruta_we.texto.text().strip()
        self.config.ruta_lively = self.ruta_lively.texto.text().strip()
        self.config.monitor = self.monitor.text().strip()
        self.config.ocultar_no_registrados = self.solo_registrados.isChecked()
        self.config.modo_oculto_habilitado = self.modo_oculto.isChecked()

        try:
            self.config.guardar()
        except OSError as error:
            avisar(self, "Configuración",
                   f"No se pudo guardar la configuración:\n{error}")
            return

        self.accept()
