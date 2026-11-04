#!/usr/bin/env python3
"""Selector circular de fondos animados.

Carrusel en 3D: arrastra, usa las flechas / A-D, y Enter o clic aplican el
fondo. Teclas extra: F2 configuración, Ctrl+Shift+H modo oculto,
Ctrl+R fondo anterior, Esc cierra.

Qué hay aquí: solo la interfaz. La lista de fondos y su aplicación están en
core/gestor_fondos.py y platforms/.
"""

import math
import os
import sys

from PySide6.QtWidgets import (
    QApplication,
    QGraphicsView,
    QGraphicsScene,
    QGraphicsPixmapItem,
    QGraphicsItem
)

from PySide6.QtGui import (
    QPixmap,
    QPainter,
    QImage
)

from PySide6.QtCore import (
    Qt,
    QPoint,
    QTimer,
    QThreadPool
)

from ..core.gestor_fondos import IMAGE_EXT, VIDEO_EXT
from .comun import (
    ThumbnailLoader,
    abrir_configuracion,
    alternar_ocultos,
    avisar,
    restaurar_anterior,
)

# Tamaño de todas las miniaturas (rectangulares, proporción 16:9)
CARD_W = 900
CARD_H = 506

def make_card_pixmap(image):
    # Recorta la imagen para llenar todo el rectángulo (sin deformarla),
    # así todas las miniaturas tienen exactamente el mismo tamaño
    pix = QPixmap.fromImage(
        image.scaled(
            CARD_W,
            CARD_H,
            Qt.KeepAspectRatioByExpanding,
            Qt.SmoothTransformation
        )
    )

    return pix.copy(
        (pix.width() - CARD_W) // 2,
        (pix.height() - CARD_H) // 2,
        CARD_W,
        CARD_H
    )


class Carousel(QGraphicsView):

    def __init__(self, gestor):
        super().__init__()
        # Lista y aplica los fondos (core/gestor_fondos.py)
        self.gestor = gestor
        # Evita recalcular posiciones antes de que todo esté creado
        self._ready = False
        self.velocity = 0.0
        self.thread_pool = QThreadPool.globalInstance()
        self.thread_pool.setMaxThreadCount(4)
        self.inertia_timer = QTimer(self)
        self.inertia_timer.timeout.connect(self.animate_inertia)
        self.inertia_timer.start(16)  # ~60 FPS
        self.mouse_moved = False
        # Índice del wallpaper actualmente seleccionado
        self.selected_index = 0
        self.setWindowTitle("Wallpaper Selector")
        # Hace la ventana ligeramente transparente
        self.setWindowOpacity(0.95)
        self.setFrameShape(QGraphicsView.NoFrame)
        self.setWindowFlags(
            # Quita barra de título y bordes
            Qt.FramelessWindowHint |
            # Mantiene la ventana por encima de las demás
            Qt.WindowStaysOnTopHint
        )

        self.setRenderHint(QPainter.Antialiasing)
        # Fondo transparente
        self.setAttribute(Qt.WA_TranslucentBackground)
        # Actualiza toda la escena cada frame
        self.setViewportUpdateMode(
            QGraphicsView.SmartViewportUpdate)
        self.setOptimizationFlags(
            QGraphicsView.DontSavePainterState)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setStyleSheet("""
        background-color: rgba(15,15,15,120);
        border:none;
        """)

        self.resize(1920, 1080)

        self.scene = QGraphicsScene()
        self.setScene(self.scene)
        # La escena se ancla arriba a la izquierda: las coordenadas de la
        # escena coinciden con las del viewport y el carrusel no se
        # reencuadra cuando cambian los items o el tamaño de la ventana
        self.setAlignment(Qt.AlignLeft | Qt.AlignTop)

        self.items = []

        # True cuando se desbloquearon los fondos privados
        self.show_hidden = False

        self.rotation = 0.0

        self.dragging = False
        self.last_x = 0

        self.load_wallpapers()

        self.update_selected()
        self._ready = True
        self._relayout()
        QTimer.singleShot(
            0,
            self._relayout
        )

    def _relayout(self):
        # Ajusta la escena al tamaño real visible y recoloca el carrusel
        w = self.viewport().width()
        h = self.viewport().height()

        if w <= 0 or h <= 0:
            return

        self.scene.setSceneRect(0, 0, w, h)
        self.update_positions()

    def resizeEvent(self, event):
        super().resizeEvent(event)

        if self._ready:
            self._relayout()

    def showEvent(self, event):
        super().showEvent(event)

        if self._ready:
            # En Wayland el tamaño final de pantalla completa puede llegar
            # unos instantes después de mostrar la ventana
            QTimer.singleShot(0, self._relayout)
            QTimer.singleShot(100, self._relayout)

    def animate_inertia(self):
        
        if abs(self.velocity) < 0.0001:
            self.velocity = 0
            return

        self.rotation += self.velocity
        self.velocity *= 0.92
        
        self.update_selected()
        self.update_positions()
        
    def update_thumbnail(self, item, image):

        # Si el fondo ya no está en el selector, se ignora
        if item not in self.items:
            return

        pix = make_card_pixmap(image)

        item.setPixmap(pix)
        item.cached_width = pix.width()
        item.cached_height = pix.height()

        self.update_positions()
     
    def load_wallpapers(self):
        # Los fondos los entrega el gestor (carpetas del usuario y
        # Wallpaper Engine); aquí solo se convierten en miniaturas
        for fondo in self.gestor.listar(mostrar_ocultos=self.show_hidden):

            path = fondo.path
            preview = fondo.preview

            ext = os.path.splitext(path)[1].lower()

            is_video = False

            # Si tiene vista previa (Wallpaper Engine) se usa esa imagen
            image = QImage(preview) if preview else QImage()

            if not image.isNull():

                pix = make_card_pixmap(image)

            elif ext in IMAGE_EXT:
                
                image = QImage(path)

                if image.isNull():
                    continue
                
                pix = make_card_pixmap(image)


            elif ext in VIDEO_EXT:

    # Imagen temporal gris mientras carga
                pix = QPixmap(CARD_W, CARD_H)
                pix.fill(Qt.darkGray)
                is_video = True

            else:
                continue
            # Escala todas las miniaturas

            item = QGraphicsPixmapItem(pix)
            item.setCacheMode(
                QGraphicsItem.DeviceCoordinateCache
                )
            item.cached_width = pix.width()
            item.cached_height = pix.height()

            item.original_path = path
            item.fondo = fondo

            self.scene.addItem(item)

            self.items.append(item)
            
            if is_video:

                loader = ThumbnailLoader(path, item)
                
                loader.signals.loaded.connect(
                    self.update_thumbnail)
                self.thread_pool.start(loader)
       
    def update_selected(self):
        # Busca cuál elemento está más al frente
        # usando el valor Z calculado con cos()
        # Cuando "Z" vale "1" significa que esta justo enfrente
        best_index = 0
        best_z = -999

        for i in range(len(self.items)):

            angle = (
                (2 * math.pi * i / len(self.items))
                + self.rotation
            )

            z = math.cos(angle)

            if z > best_z:
                best_z = z
                best_index = i

        self.selected_index = best_index
    
    def update_positions(self):

        if not self.items:
            return

        # Centro del área realmente visible (viewport)
        cx = self.viewport().width() / 2
        cy = self.viewport().height() / 2
        #Radio   #Que tan abierto esta el carrusel
        radius = 1100

        total = len(self.items)

        for i, item in enumerate(self.items):

            angle = (
                (2 * math.pi * i / total)
                + self.rotation
            )

            x = math.sin(angle)
            z = math.cos(angle)
            #Escala
            scale = 0.55 + ((z + 1) / 2) * 0.65

            final_scale = scale

            if i == self.selected_index:
                final_scale *= 1.08
                item.setOpacity(1.0)
            else:
                 #Opacidad: que tan trasparente es
                item.setOpacity(
                     #Atras   #Delante
                    0.45 + ((z + 1) / 2) * 0.55
                )
            if abs(item.scale() - final_scale) > 0.01:
                item.setScale(final_scale)
                
            item.setZValue(z)

            pos_x = cx + x * radius
             #Altura
            pos_y = cy - z * 40

            new_x = (
                pos_x -
                item.cached_width * final_scale / 2
            )
            
            new_y = (
                pos_y -
                item.cached_height * final_scale / 2
            )
            
            if (
                abs(item.x() - new_x) > 0.5 or
                abs(item.y() - new_y) > 0.5
            ):
                item.setPos(new_x, new_y)



    def apply_wallpaper(self):
        if not self.items:
            return

        fondo = self.items[self.selected_index].fondo

        try:
            mensaje = self.gestor.aplicar(fondo)
        except Exception as error:
            print(f"No se pudo aplicar el fondo: {error}")
            avisar(self, "No se pudo aplicar el fondo", str(error))
            return

        print(mensaje)
        self.close()

    def rotate_left(self):

        self.rotation -= 0.25

        self.update_selected()

        self.update_positions()

    def rotate_right(self):

        self.rotation += 0.25

        self.update_selected()

        self.update_positions()
        
    def mousePressEvent(self, event):

        if event.button() == Qt.LeftButton:

            self.dragging = True
            self.mouse_moved = False
            self.last_x = event.position().x()
            self.velocity = 0
            
    def mouseMoveEvent(self, event):

        if not self.dragging:
            return

        dx = event.position().x() - self.last_x

        if abs(dx) > 3:
            self.mouse_moved = True

        delta = dx * 0.003

        self.rotation += delta
        self.velocity = delta

        self.last_x = event.position().x()

        self.update_selected()
        self.update_positions()

    def mouseReleaseEvent(self, event):

        self.dragging = False

        # Si no se arrastró, se considera un clic
        if not self.mouse_moved:

            item = self.itemAt(
                event.position().toPoint()
            )
 
            if item and item in self.items:

                self.selected_index = self.items.index(item)

                self.update_positions()

                self.apply_wallpaper()

    def toggle_hidden(self):
        # Ctrl + Shift + H: pide la contraseña y muestra los fondos
        # privados; si ya están visibles, los vuelve a ocultar
        # (la lógica está en comun.alternar_ocultos)
        if alternar_ocultos(self):
            self.reload_wallpapers()

    def reload_wallpapers(self):
        # Vuelve a cargar los fondos (con o sin los privados)
        for item in self.items:
            self.scene.removeItem(item)

        self.items = []
        self.rotation = 0.0
        self.velocity = 0

        for name, value in (
            ("target_rotation", None),
            ("cursor_offset", 0),
            ("hover_index", None),
        ):
            if hasattr(self, name):
                setattr(self, name, value)

        self.load_wallpapers()

        self.update_selected()
        self.update_positions()

    def keyPressEvent(self, event):

        # Interruptor escondido de los fondos privados
        if (
            event.key() == Qt.Key_H and
            event.modifiers() & Qt.ControlModifier and
            event.modifiers() & Qt.ShiftModifier
        ):
            self.toggle_hidden()
            return

        # F2: ventana de configuración
        if event.key() == Qt.Key_F2:
            abrir_configuracion(self)
            return

        # Ctrl + R: vuelve al fondo anterior
        if (
            event.key() == Qt.Key_R and
            event.modifiers() & Qt.ControlModifier
        ):
            restaurar_anterior(self)
            return

        if event.key() == Qt.Key_Left:
            self.rotate_left()

        elif event.key() == Qt.Key_Right:
            self.rotate_right()

        elif event.key() == Qt.Key_A:
            self.rotate_left()

        elif event.key() == Qt.Key_D:
            self.rotate_right()

        elif event.key() == Qt.Key_Escape:
            self.close()
        
        elif event.key() in (
            Qt.Key_Return,
            Qt.Key_Enter
        ):

            self.apply_wallpaper()



def ejecutar(gestor):
    app = QApplication.instance() or QApplication(sys.argv)

    w = Carousel(gestor)
    w.showFullScreen()

    return app.exec()
