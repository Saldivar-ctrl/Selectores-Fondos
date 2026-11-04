"""Campo de contraseña del modo oculto.

Solo un rectángulo semitransparente con el texto dentro (los caracteres se
ven como puntos). Sin botones, sin etiquetas, sin adornos. Al enfocarlo, el
borde se aclara un poco. Enter acepta, Esc cancela.

Apariencia: se cambia en ESTILO (más abajo).
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QLabel, QLineEdit, QVBoxLayout

ESTILO = """
QLineEdit {
    background-color: rgba(20, 20, 20, 150);
    color: white;
    border: 1px solid rgba(255, 255, 255, 50);
    border-radius: 8px;
    padding: 0 16px;
    font-size: 18px;
    selection-background-color: rgba(255, 255, 255, 60);
}
QLineEdit:focus {
    background-color: rgba(30, 30, 30, 185);
    border: 1px solid rgba(255, 255, 255, 170);
}
"""


class DialogoContrasena(QDialog):

    def __init__(self, parent=None, marcador=""):
        super().__init__(parent)

        self.setWindowFlags(
            Qt.Dialog | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setModal(True)
        self.setFixedSize(360, 52)

        self.campo = QLineEdit(self)
        self.campo.setEchoMode(QLineEdit.Password)  # puntos
        self.campo.setAlignment(Qt.AlignCenter)
        self.campo.setFixedSize(360, 52)  # el rectángulo ocupa todo el cuadro
        self.campo.setStyleSheet(ESTILO)


        # Texto de ayuda propio (el de Qt no se ve con el campo enfocado):
        # se muestra mientras el campo está vacío y desaparece al escribir
        self.ayuda = QLabel(marcador, self.campo)
        self.ayuda.setAlignment(Qt.AlignCenter)
        self.ayuda.setGeometry(0, 0, 360, 52)
        self.ayuda.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.ayuda.setStyleSheet(
            "background: transparent; border: none; font-size: 18px;"
            "color: rgba(255, 255, 255, 140);"
        )
        self.ayuda.setVisible(bool(marcador))
        self.campo.textChanged.connect(
            lambda texto: self.ayuda.setVisible(bool(marcador) and not texto)
        )

        disposicion = QVBoxLayout(self)
        disposicion.setContentsMargins(0, 0, 0, 0)
        disposicion.addWidget(self.campo)

        self.campo.returnPressed.connect(self.accept)

    def showEvent(self, event):
        super().showEvent(event)

        # Centrado sobre la ventana del selector
        if self.parent() is not None:
            centro = self.parent().frameGeometry().center()
            self.move(centro - self.rect().center())

        self.activateWindow()
        self.campo.setFocus()


def pedir_contrasena(parent=None, marcador=""):
    """Devuelve el texto escrito, o None si se canceló (Esc)."""
    dialogo = DialogoContrasena(parent, marcador)

    if dialogo.exec() == QDialog.Accepted:
        return dialogo.campo.text()

    return None
