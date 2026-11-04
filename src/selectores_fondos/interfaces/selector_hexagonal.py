#!/usr/bin/env python3
"""Selector hexagonal de fondos animados.

Panal de hexágonos dentro de un marco fijo e invisible: solo se mueven los
hexágonos. Arrastra, usa flechas / A-D / rueda, y Enter o clic aplican el
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
    QImage,
    QPainterPath,
    QPen,
    QBrush,
    QColor,
    QCursor
)

from PySide6.QtCore import (
    Qt,
    QPointF,
    QRectF,
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

# ---- Geometría del panal (diseñada para una pantalla de 1080 px) ----
# Tamaño del pixmap de cada hexágono (proporción de hexágono regular)
HEX_W = 420
HEX_H = 364
# Escala base con la que se dibuja cada hexágono
HEX_SCALE = 0.66
# Separación entre hexágonos
HEX_GAP = 10
# Hexágonos por columna
ROWS = 3
# Cuánto crece el hexágono seleccionado
SELECTED_SCALE = 1.30
# Cuánto crece el hexágono cuando el mouse pasa por encima
HOVER_SCALE = 1.30
# Columnas completamente visibles dentro del marco del selector
FULL_COLS = 5
# Columna extra, casi invisible, al final del marco
FADE_OPACITY = 0.35
# Lugar (empezando en 0) de la columna donde está el selector
CURSOR_SLOT = 2


def make_hex_pixmap(image):
    # Recorta la imagen para cubrir todo el hexágono (sin deformarla)
    pix = QPixmap.fromImage(
        image.scaled(
            HEX_W,
            HEX_H,
            Qt.KeepAspectRatioByExpanding,
            Qt.SmoothTransformation
        )
    )

    return pix.copy(
        (pix.width() - HEX_W) // 2,
        (pix.height() - HEX_H) // 2,
        HEX_W,
        HEX_H
    )


class HexItem(QGraphicsPixmapItem):
    # Miniatura con forma de hexágono (puntas a izquierda y derecha)

    def __init__(self, pix):
        super().__init__(pix)

        self.highlight = False

    def hex_path(self):
        w = self.pixmap().width()
        h = self.pixmap().height()

        path = QPainterPath()
        path.moveTo(w * 0.25, 0)
        path.lineTo(w * 0.75, 0)
        path.lineTo(w, h * 0.5)
        path.lineTo(w * 0.75, h)
        path.lineTo(w * 0.25, h)
        path.lineTo(0, h * 0.5)
        path.closeSubpath()

        return path

    def boundingRect(self):
        # Un poco más grande para que quepa el borde
        return QRectF(
            -4,
            -4,
            self.pixmap().width() + 8,
            self.pixmap().height() + 8
        )

    def shape(self):
        # Los clics solo cuentan dentro del hexágono
        return self.hex_path()

    def paint(self, painter, option, widget=None):

        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setRenderHint(QPainter.SmoothPixmapTransform, True)

        path = self.hex_path()

        # Imagen recortada con la forma del hexágono
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(self.pixmap()))
        painter.drawPath(path)

        # Borde claro y fino (más marcado si está seleccionado)
        if self.highlight:
            painter.setPen(QPen(QColor(255, 255, 255, 235), 4))
        else:
            painter.setPen(QPen(QColor(225, 235, 255, 150), 3))

        painter.setBrush(Qt.NoBrush)
        painter.drawPath(path)


class Carousel(QGraphicsView):

    def __init__(self, gestor):
        super().__init__()
        # Lista y aplica los fondos (core/gestor_fondos.py)
        self.gestor = gestor
        self.velocity = 0.0
        # Cuántas columnas se ha movido el selector de su lugar normal
        # (solo cambia al llegar a un límite de la lista)
        self.cursor_offset = 0
        # Hexágono bajo el mouse (None si no hay ninguno)
        self.hover_index = None
        # Posición a la que se deslizan los hexágonos con las flechas
        self.target_rotation = None
        # Indica que aún hay hexágonos animando su tamaño
        self.settling = False
        self.thread_pool = QThreadPool.globalInstance()
        self.thread_pool.setMaxThreadCount(4)
        self.inertia_timer = QTimer(self)
        self.inertia_timer.timeout.connect(self.animate_inertia)
        self.inertia_timer.start(16)  # ~60 FPS
        self.mouse_moved = False
        # Índice del wallpaper actualmente seleccionado
        self.selected_index = 0
        self.setWindowTitle("Wallpaper Selector")
        # Ventana completamente visible; el fondo es transparente
        self.setWindowOpacity(1.0)
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
        self.viewport().setAttribute(Qt.WA_TranslucentBackground)
        self.viewport().setAutoFillBackground(False)
        self.setBackgroundBrush(Qt.NoBrush)
        # Para que los hexágonos reaccionen al pasar el mouse
        self.setMouseTracking(True)
        self.viewport().setMouseTracking(True)
        # Actualiza toda la escena cada frame
        self.setViewportUpdateMode(
            QGraphicsView.SmartViewportUpdate)
        self.setOptimizationFlags(
            QGraphicsView.DontSavePainterState)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self.setStyleSheet("""
        background: transparent;
        border:none;
        """)

        self.resize(1920, 1080)

        self.scene = QGraphicsScene()
        self.scene.setSceneRect(0, 0, 1920, 1080)
        self.setScene(self.scene)

        # Marco fijo del selector (invisible): recorta todo lo que
        # se salga de él
        self.frame = self.scene.addRect(0, 0, 1, 1, Qt.NoPen, Qt.NoBrush)
        self.frame.setFlag(QGraphicsItem.ItemClipsChildrenToShape, True)

        self.items = []

        # True cuando se desbloquearon los fondos privados
        self.show_hidden = False

        # Desplazamiento horizontal del panal (en píxeles)
        # 0 = la primera columna queda al inicio de la pantalla
        self.rotation = 0.0

        self.dragging = False
        self.last_x = 0

        self.load_wallpapers()

        self.update_selected()
        QTimer.singleShot(
            0,
            self.update_positions
        )

    def animate_inertia(self):

        moving = abs(self.velocity) >= 0.05

        if (
            not moving and
            not self.dragging and
            self.target_rotation is None and
            self.items
        ):
            # Al terminar de deslizar, acomoda las columnas en su lugar
            unit, base, dx, dy, start_x = self.layout_metrics()

            k = max(0, min(self.max_scroll(), round(self.rotation / dx)))
            aligned = k * dx

            if abs(aligned - self.rotation) > 0.5:
                self.velocity = 0
                self.target_rotation = aligned

        if (
            not moving and
            not self.settling and
            self.target_rotation is None
        ):
            self.velocity = 0
            return

        sliding = self.target_rotation is not None or moving

        if self.target_rotation is not None:
            # Las columnas se deslizan suavemente hasta su nuevo lugar
            # (el marco del selector no se mueve)
            diff = self.target_rotation - self.rotation

            if abs(diff) < 0.5:
                self.rotation = self.target_rotation
                self.target_rotation = None
            else:
                self.rotation += diff * 0.2

            self.clamp_rotation()
            self.update_selected()

        elif moving:
            self.rotation += self.velocity
            self.velocity *= 0.92
            self.clamp_rotation()
            self.update_selected()

        if sliding:
            self.refresh_hover()

        self.update_positions()

    def refresh_hover(self):
        # Mientras las columnas se deslizan, el hexágono que queda bajo
        # el mouse (aunque el mouse no se mueva) es el que crece
        if self.dragging:
            return

        point = self.viewport().mapFromGlobal(QCursor.pos())

        if self.viewport().rect().contains(point):
            item = self.itemAt(point)
        else:
            item = None

        if item and item in self.items:
            self.hover_index = self.items.index(item)
        else:
            self.hover_index = None

    def update_thumbnail(self, item, image):

        # Si el fondo ya no está en el selector, se ignora
        if item not in self.items:
            return

        pix = make_hex_pixmap(image)

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

                pix = make_hex_pixmap(image)

            elif ext in IMAGE_EXT:

                image = QImage(path)

                if image.isNull():
                    continue

                pix = make_hex_pixmap(image)

            elif ext in VIDEO_EXT:

    # Imagen temporal gris mientras carga
                pix = QPixmap(HEX_W, HEX_H)
                pix.fill(Qt.darkGray)
                is_video = True

            else:
                continue

            item = HexItem(pix)
            item.setCacheMode(
                QGraphicsItem.DeviceCoordinateCache
                )
            item.cached_width = pix.width()
            item.cached_height = pix.height()
            # Escala actual (se anima hasta la escala objetivo)
            item.current_scale = None

            item.original_path = path
            item.fondo = fondo

            item.setParentItem(self.frame)

            self.items.append(item)

            if is_video:

                loader = ThumbnailLoader(path, item)

                loader.signals.loaded.connect(
                    self.update_thumbnail)
                self.thread_pool.start(loader)

    def layout_metrics(self):
        # Tamaños del panal según la altura de la pantalla
        unit = self.height() / 1080
        base = HEX_SCALE * unit

        # Distancia entre columnas y entre filas
        dx = (HEX_W * 0.75 + HEX_GAP * 0.866) * base
        dy = (HEX_H + HEX_GAP) * base

        # Las columnas del marco quedan centradas en la pantalla;
        # start_x es el centro de la primera columna (lugar 0)
        start_x = self.width() / 2 - (FULL_COLS) * dx / 2

        return unit, base, dx, dy, start_x

    def column_count(self):
        return math.ceil(len(self.items) / ROWS)

    def max_scroll(self):
        # Cuántas columnas se pueden deslizar: la lista no da la vuelta,
        # se detiene cuando la última columna llega al último lugar
        return max(0, self.column_count() - FULL_COLS)

    def column_slot(self, col, dx):
        # Lugar de una columna dentro del marco (con decimales mientras
        # se desliza): 0 = primera, 4 = quinta, 5 = la casi invisible.
        return col - self.rotation / dx

    def item_center(self, i, dx, dy, start_x):
        # Centro de cada hexágono en pantalla (columna por columna)
        col = i // ROWS
        row = i % ROWS

        pos_x = start_x + self.column_slot(col, dx) * dx

        pos_y = (
            self.height() / 2
            + (row - (ROWS - 1) / 2) * dy
            # Las columnas impares bajan media fila (panal)
            + (dy / 2 if col % 2 else 0)
            - dy / 4
        )

        return pos_x, pos_y



    def clamp_rotation(self):
        # La lista no da la vuelta: se detiene en el primer y último límite
        if not self.items:
            return

        unit, base, dx, dy, start_x = self.layout_metrics()

        high = self.max_scroll() * dx

        if self.rotation < 0:
            self.rotation = 0.0
            self.velocity = 0

        elif self.rotation > high:
            self.rotation = high
            self.velocity = 0

    def update_selected(self):
        # El selector es el hexágono del medio de una columna. Normalmente
        # está en el lugar CURSOR_SLOT y no se mueve; solo al llegar a
        # un límite de la lista baja o sube por las últimas columnas.
        if not self.items:
            return

        unit, base, dx, dy, start_x = self.layout_metrics()

        columns = self.column_count()

        k = max(0, min(self.max_scroll(), round(self.rotation / dx)))

        col = k + CURSOR_SLOT + self.cursor_offset
        col = max(0, min(columns - 1, col))

        # Mantiene coherente el desplazamiento del selector
        self.cursor_offset = col - k - CURSOR_SLOT

        self.selected_index = min(
            len(self.items) - 1,
            col * ROWS + ROWS // 2
        )

    def update_positions(self):

        if not self.items:
            return

        unit, base, dx, dy, start_x = self.layout_metrics()

        cy = self.height() / 2

        # Marco fijo del selector: nada se dibuja fuera de él
        half_w = HEX_W * base / 2
        margin = dx * 0.2
        left = start_x - half_w - margin
        right = start_x + (FULL_COLS) * dx + half_w + margin
        half_h = 1.25 * dy + HEX_H * base / 2 + dy * 0.1

        self.frame.setRect(
            QRectF(left, cy - half_h, right - left, 2 * half_h)
        )

        settling = False

        for i, item in enumerate(self.items):

            pos_x, pos_y = self.item_center(i, dx, dy, start_x)

            # Escala: el seleccionado se expande
            target = base

            if self.hover_index is not None:
                # Con el mouse sobre un hexágono, solo ese crece
                if i == self.hover_index:
                    target *= HOVER_SCALE
                    item.setZValue(10)
                else:
                    item.setZValue(0)

            elif i == self.selected_index:
                # Sin mouse encima, crece el hexágono del selector
                target *= SELECTED_SCALE
                item.setZValue(10)

            else:
                item.setZValue(0)

            if item.highlight != (i == self.selected_index):
                item.highlight = (i == self.selected_index)
                item.update()

            if item.current_scale is None:
                item.current_scale = target

            item.current_scale += (target - item.current_scale) * 0.28

            if abs(target - item.current_scale) < 0.002:
                item.current_scale = target
            else:
                settling = True

            final_scale = item.current_scale

            if abs(item.scale() - final_scale) > 0.0005:
                item.setScale(final_scale)

            # Lugar de la columna dentro del marco
            slot = (pos_x - start_x) / dx

            if slot <= -1:
                # Ya salió: invisible
                opacity = 0.0

            elif slot < 0:
                # Primera columna saliendo: se desvanece
                opacity = slot + 1

            elif slot <= FULL_COLS - 1:
                # Columnas 1 a 5: totalmente visibles
                opacity = 1.0

            elif slot <= FULL_COLS:
                # Columna 6: casi invisible
                t = slot - (FULL_COLS - 1)
                opacity = 1.0 - t * (1.0 - FADE_OPACITY)

            else:
                # Columna entrando por la derecha
                opacity = max(
                    0.0,
                    FADE_OPACITY * (FULL_COLS + 1 - slot)
                )

            item.setOpacity(opacity)
            item.setVisible(opacity > 0.01)

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

        self.settling = settling

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

    def move_selection(self, columns):
        # Desliza las columnas; el marco del selector no se mueve.
        # Al llegar a un límite, el selector avanza por las últimas
        # columnas en lugar de seguir girando.
        if not self.items:
            return

        unit, base, dx, dy, start_x = self.layout_metrics()

        self.velocity = 0

        current = (
            self.target_rotation
            if self.target_rotation is not None
            else self.rotation
        )

        k = max(0, min(self.max_scroll(), round(current / dx)))

        col = max(0, min(
            self.column_count() - 1,
            k + CURSOR_SLOT + self.cursor_offset
        ))
        self.cursor_offset = col - k - CURSOR_SLOT

        if columns > 0:

            if self.cursor_offset < 0:
                self.cursor_offset += 1

            elif k < self.max_scroll():
                k += 1

            elif col < self.column_count() - 1:
                self.cursor_offset += 1

        else:

            if self.cursor_offset > 0:
                self.cursor_offset -= 1

            elif k > 0:
                k -= 1

            elif col > 0:
                self.cursor_offset -= 1

        self.target_rotation = k * dx

        self.update_selected()
        self.animate_inertia()
        self.update_positions()

    def rotate_left(self):

        self.move_selection(-1)

    def rotate_right(self):

        self.move_selection(1)

    def resizeEvent(self, event):

        super().resizeEvent(event)

        self.scene.setSceneRect(0, 0, self.width(), self.height())

        self.clamp_rotation()
        self.update_selected()
        self.update_positions()

    def wheelEvent(self, event):

        delta = event.angleDelta().y() or event.angleDelta().x()

        # Rueda hacia arriba = izquierda, hacia abajo = derecha
        if delta > 0:
            self.rotate_left()
        elif delta < 0:
            self.rotate_right()

    def mousePressEvent(self, event):

        if event.button() == Qt.LeftButton:

            self.dragging = True
            self.mouse_moved = False
            self.last_x = event.position().x()
            self.velocity = 0
            self.target_rotation = None
            self.cursor_offset = 0
            # Mientras se arrastra, ningún hexágono crece por el mouse
            self.hover_index = None

    def leaveEvent(self, event):

        # Si el mouse sale de la ventana, el hexágono vuelve a su tamaño
        self.hover_index = None
        self.update_positions()

        super().leaveEvent(event)

    def mouseMoveEvent(self, event):

        if not self.dragging:

            # Al pasar el mouse sobre un hexágono se agranda un poco.
            # El selector no sigue al mouse: se queda en su lugar.
            item = self.itemAt(
                event.position().toPoint()
            )

            if item and item in self.items:
                index = self.items.index(item)
            else:
                index = None

            if index != self.hover_index:
                self.hover_index = index
                self.update_positions()

            return

        dx = event.position().x() - self.last_x

        if abs(dx) > 3:
            self.mouse_moved = True

        # El panal sigue al mouse mientras se mantiene el clic
        delta = -dx

        self.rotation += delta
        self.velocity = delta

        self.last_x = event.position().x()

        self.clamp_rotation()
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
