#!/usr/bin/env python3
# Selector de fondos: estilo CUADRÍCULA (cuadros rectangulares que se deslizan de lado)

import sys
import json
import hashlib
import hmac
import math
import os
import re
import subprocess
import tempfile

from PySide6.QtWidgets import (
    QApplication,
    QGraphicsView,
    QGraphicsScene,
    QGraphicsPixmapItem,
    QGraphicsItem,
    QDialog,
    QLabel,
    QMessageBox,
    QVBoxLayout,
    QLineEdit
)

from PySide6.QtGui import (
    QPixmap,
    QPainter,
    QImage,
    QPainterPath,
    QPen,
    QBrush,
    QColor,
    QFont,
    QCursor,
    QPalette
)

from PySide6.QtCore import (
    Qt,
    QPoint,
    QPointF,
    QRectF,
    QTimer,
    QThreadPool,
    QRunnable
)
from PySide6.QtCore import (
    QObject,
    Signal
)

# Carpeta donde están todos los wallpapers
FOLDER = os.path.expanduser("~/Vídeos/fondos")
# Carpetas de Wallpaper Engine (Steam Workshop, juego 431960).
# Agrega aquí la ruta si tu biblioteca de Steam está en otro disco:
#   "/run/media/TU_USUARIO/MiDisco/SteamLibrary/steamapps/workshop/content/431960"
WORKSHOP_FOLDERS = [
    # Wallpapers que trae Wallpaper Engine y los tuyos
    "~/.steam/steam/steamapps/common/wallpaper_engine/projects/defaultprojects",
    "~/.steam/steam/steamapps/common/wallpaper_engine/projects/myprojects",
    "~/.local/share/Steam/steamapps/common/wallpaper_engine/projects/defaultprojects",
    "~/.local/share/Steam/steamapps/common/wallpaper_engine/projects/myprojects",
    # Wallpapers descargados del Workshop
    "~/.local/share/Steam/steamapps/workshop/content/431960",
    "~/.steam/steam/steamapps/workshop/content/431960",
    "~/.var/app/com.valvesoftware.Steam/.local/share/Steam/steamapps/workshop/content/431960",
]
# True = solo muestra los wallpapers de Wallpaper Engine que Waywallen
# tiene registrados (así todos los que veas se pueden aplicar).
# False = muestra todos, aunque algunos no se puedan aplicar.
HIDE_UNREGISTERED = True
# Wallpapers que NO quieres ver en el selector. Escribe el número de su
# carpeta (ej. "3753921460") o su título. Para ver la lista de todos tus
# wallpapers de Wallpaper Engine con sus números, ejecuta el selector así:
#   python nombre_del_archivo.py --listar
HIDDEN_WALLPAPERS = [
    # "3753921460",
    # "Título de otro wallpaper",
]
# Carpetas de fondos privados. Todo lo que tengan dentro (carpetas, enlaces o
# archivos vacíos) se oculta del selector si su nombre es el número de
# carpeta del wallpaper (ej. 3753921460), su título o el nombre de su archivo.
# No hace falta mover los wallpapers: basta crear aquí una carpeta vacía
# con ese número, por ejemplo:  mkdir ~/.local/share/wallpaper-selector/privados/3753921460
# Puede haber varias; se usan todas las que existan. La primera está en
# una ruta oculta (los nombres que empiezan con punto no se ven en el
# administrador de archivos, salvo que actives "mostrar archivos ocultos").
HIDDEN_FOLDERS = [
    "~/Vídeos/.fondos_privados",
    "~/.local/share/wallpaper-selector/privados",
    "~/Vídeos/fondos_privados",
]
# Contraseña (guardada como huella, no en texto) para ver los fondos
# privados. Interruptor escondido: Ctrl + Shift + H
# Contraseña inicial: "cambiar". Cámbiala lo primero con F2.
PASSWORD_HASH = "d3fd787ac1c5e27fb71acd2e207ed438c0cda22234d2e5a2ca3d201d657b3d30"
# Extensiones consideradas como video
VIDEO_EXT = (
    ".mp4",
    ".mkv",
    ".webm",
    ".avi",
    ".mov"
)
# Extensiones consideradas como imagen
IMAGE_EXT = (
    ".jpg",
    ".jpeg",
    ".png",
    ".webp"
)
# Archivo donde guardaremos el último fondo aplicado
CURRENT_WALLPAPER = os.path.expanduser(
    "~/.config/wallpaper-selector.json"
)

# ---- Geometría de la cuadrícula (diseñada para una pantalla de 1080 px) ----
# Tamaño del pixmap de cada cuadro (16:9)
CARD_W = 480
CARD_H = 270
# Escala base con la que se dibuja cada cuadro
CARD_SCALE = 0.75
# Separación entre cuadros
CARD_GAP = 12
# Cuadros por columna
ROWS = 3
# Cuánto crece el cuadro seleccionado
SELECTED_SCALE = 1.12
# Cuánto crece el cuadro cuando el mouse pasa por encima
HOVER_SCALE = 1.12
# Columnas completamente visibles dentro del marco del selector
FULL_COLS = 4
# Columna extra, casi invisible, al final del marco
FADE_OPACITY = 0.35
# Lugar (empezando en 0) de la columna donde está el selector
CURSOR_SLOT = 2


def _ww_read_varint(data, pos):
    value = 0
    shift = 0

    while pos < len(data):
        byte = data[pos]
        pos += 1
        value |= (byte & 0x7F) << shift

        if byte < 0x80:
            return value, pos

        shift += 7
        if shift >= 70:
            raise ValueError("Varint protobuf inválido")

    raise ValueError("Respuesta protobuf incompleta")


def _ww_fields(data):
    pos = 0

    while pos < len(data):
        key, pos = _ww_read_varint(data, pos)
        number, wire = key >> 3, key & 7

        if number == 0:
            raise ValueError("Campo protobuf inválido")

        if wire == 0:
            value, pos = _ww_read_varint(data, pos)
        elif wire == 1:
            value = data[pos:pos + 8]
            pos += 8
        elif wire == 2:
            length, pos = _ww_read_varint(data, pos)
            value = data[pos:pos + length]
            pos += length
        elif wire == 5:
            value = data[pos:pos + 4]
            pos += 4
        else:
            raise ValueError(f"Tipo protobuf no reconocido: {wire}")

        if pos > len(data):
            raise ValueError("Campo protobuf incompleto")

        yield number, wire, value


def waywallen_catalog():
    import subprocess
    from websockets.sync.client import connect

    output = subprocess.check_output([
        "busctl", "--user", "get-property",
        "org.waywallen.waywallen.Daemon",
        "/org/waywallen/waywallen/Daemon",
        "org.waywallen.waywallen.Daemon1",
        "WsPort",
    ], text=True, timeout=5)

    port = int(output.split()[-1])
    request = bytes([8, 1, 154, 1, 0])

    catalog = []

    with connect(
        f"ws://127.0.0.1:{port}",
        open_timeout=5,
        close_timeout=2,
        max_size=16 * 1024 * 1024,
    ) as ws:
        ws.send(request)

        while True:
            frame = ws.recv(timeout=10)

            if isinstance(frame, str):
                continue

            for number, wire, payload in _ww_fields(frame):
                if number != 1 or wire != 2:
                    continue

                response = list(_ww_fields(payload))

                request_id = next(
                    (
                        value for field, kind, value in response
                        if field == 1 and kind == 0
                    ),
                    None,
                )

                if request_id != 1:
                    continue

                listing = next(
                    (
                        value for field, kind, value in response
                        if field == 19 and kind == 2
                    ),
                    None,
                )

                if listing is None:
                    message = next(
                        (
                            value.decode("utf-8", errors="replace")
                            for field, kind, value in response
                            if field == 3 and kind == 2
                        ),
                        "Waywallen no devolvió el catálogo",
                    )
                    raise RuntimeError(message)

                for field, kind, entry_data in _ww_fields(listing):
                    if field != 1 or kind != 2:
                        continue

                    entry = {}

                    for num, wire_type, value in _ww_fields(entry_data):
                        if num in (1, 2, 3, 4) and wire_type == 2:
                            entry[num] = value.decode(
                                "utf-8", errors="replace"
                            )
                        elif num == 7 and wire_type == 0:
                            entry[7] = value

                    if entry.get(1) and entry.get(4):
                        catalog.append({
                            "id": entry[1],
                            "name": entry.get(2, ""),
                            "type": entry.get(3, ""),
                            "resource": entry[4],
                            "size": entry.get(7, 0),
                        })

                return catalog


def find_waywallen_id(path, catalog):
    filename = os.path.basename(path)
    local_size = os.path.getsize(path)
    directory = os.path.normpath(os.path.dirname(path))

    # Wallpaper Engine: cada wallpaper vive en su propia carpeta (con
    # project.json); Waywallen puede registrar el archivo o la carpeta.
    if os.path.isfile(os.path.join(directory, "project.json")):

        real_path = os.path.realpath(path)
        real_directory = os.path.realpath(directory)

        exact_path = [
            item for item in catalog
            if os.path.realpath(item["resource"]) == real_path
        ]

        if len(exact_path) == 1:
            return exact_path[0]["id"]

        same_folder = [
            item for item in catalog
            if os.path.realpath(item["resource"]) == real_directory
            or os.path.dirname(
                os.path.realpath(item["resource"])
            ) == real_directory
        ]

        if len(same_folder) == 1:
            return same_folder[0]["id"]

        # Por el número de Steam de la carpeta (ej. .../431960/123456/)
        workshop_id = os.path.basename(directory)

        if workshop_id.isdigit():

            by_id = [
                item for item in catalog
                if ("/" + workshop_id + "/") in item["resource"]
                or item["resource"].rstrip("/").endswith("/" + workshop_id)
            ]

            if len(by_id) == 1:
                return by_id[0]["id"]

        # Por el título del wallpaper (el nombre que muestra Waywallen)
        try:
            with open(
                os.path.join(directory, "project.json"),
                "r", encoding="utf-8-sig"
            ) as f:
                title = str(json.load(f).get("title") or "")
        except Exception:
            title = ""

        if title:

            by_title = [
                item for item in catalog
                if item["name"].strip().casefold()
                == title.strip().casefold()
            ]

            if len(by_title) == 1:
                return by_title[0]["id"]

    # Primero filtra por nombre y extensión del recurso.
    candidates = [
        item for item in catalog
        if os.path.basename(item["resource"]) == filename
    ]

    if not candidates:
        raise ValueError(
            f"'{filename}' no está registrado en Waywallen ({path}). "
            "Añádelo a su biblioteca y vuelve a intentarlo."
        )

    # Si existen archivos con el mismo nombre, compara sus tamaños.
    exact = [
        item for item in candidates
        if item["size"] == local_size
    ]

    if len(exact) == 1:
        return exact[0]["id"]

    if len(exact) > 1:
        raise ValueError(
            f"Hay varios recursos coincidentes para '{filename}'."
        )

    if len(candidates) == 1 and candidates[0]["size"] == 0:
        return candidates[0]["id"]

    raise ValueError(
        f"No se encontró una coincidencia inequívoca para '{filename}'."
    )


def hidden_names():
    # Nombres que no deben mostrarse: los de la lista HIDDEN_WALLPAPERS
    # y los de todo lo que esté dentro de HIDDEN_FOLDERS
    names = {
        str(hidden).strip().casefold() for hidden in HIDDEN_WALLPAPERS
    }

    for folder in HIDDEN_FOLDERS:

        folder = os.path.expanduser(folder)

        if os.path.isdir(folder):

            for entry in os.listdir(folder):
                names.add(entry.casefold())
                names.add(os.path.splitext(entry)[0].casefold())

    return names


def workshop_wallpapers(include_hidden=False):
    # Busca los wallpapers de Wallpaper Engine descargados de Steam.
    # Cada uno es una carpeta con un project.json que indica su
    # archivo principal, su imagen de vista previa y su título.
    found = []
    seen = set()

    private = hidden_names()

    for folder in WORKSHOP_FOLDERS:

        # La ruta se deja tal cual (Waywallen guarda esa misma ruta);
        # solo se resuelven los enlaces para no repetir una carpeta
        folder = os.path.expanduser(folder)
        real_folder = os.path.realpath(folder)

        if real_folder in seen or not os.path.isdir(folder):
            continue

        seen.add(real_folder)

        for name in sorted(os.listdir(folder)):

            directory = os.path.join(folder, name)
            project = os.path.join(directory, "project.json")

            if not os.path.isfile(project):
                continue

            try:
                with open(project, "r", encoding="utf-8-sig") as f:
                    data = json.load(f)
            except Exception:
                continue

            main = data.get("file") or ""
            path = os.path.join(directory, main) if main else project

            if not os.path.isfile(path):
                path = project

            preview = data.get("preview") or ""
            preview = os.path.join(directory, preview) if preview else ""

            if not os.path.isfile(preview):
                preview = ""

            title = str(data.get("title") or name)

            hidden = (
                name.casefold() in private
                or title.casefold() in private
            )

            # Los ocultos no se muestran ni se consultan en Waywallen
            if hidden and not include_hidden:
                continue

            found.append({
                "path": path,
                "preview": preview,
                "title": title,
                "id": name,
                "type": str(data.get("type") or ""),
                "hidden": hidden,
            })

    found.sort(key=lambda wallpaper: wallpaper["title"].casefold())

    return found

def set_video_wallpaper(video_path):

    config = os.path.expanduser(
        "~/.config/plasma-org.kde.plasma.desktop-appletsrc"
    )

    with open(config, "r", encoding="utf-8") as f:
        text = f.read()

    file_url = "file://" + video_path

    # Evita reiniciar Plasma si ya es el video actual
    '''if f"LastVideo={file_url}" in text:
        return'''

    # Activar el plugin de video
    text = re.sub(
        r"wallpaperplugin=org\.kde\.image",
        "wallpaperplugin=luisbocanegra.smart.video.wallpaper.reborn",
        text,
        flags=re.IGNORECASE
    )

    text = re.sub(
        r"LastVideo=.*",
        f"LastVideo={file_url}",
        text
    )

    text = re.sub(
        r"ResumeLastVideo=.*",
        "ResumeLastVideo=true",
        text
    )

    with open(config, "w", encoding="utf-8") as f:
        f.write(text)

    subprocess.run([
        "kquitapp6",
        "plasmashell"
    ])

    subprocess.Popen(
        ["plasmashell"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

def make_card_pixmap(image):
    # Recorta la imagen para cubrir todo el cuadro (sin deformarla)
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


class CardItem(QGraphicsPixmapItem):
    # Miniatura rectangular con las esquinas ligeramente redondeadas

    def __init__(self, pix):
        super().__init__(pix)

        self.highlight = False

    def card_path(self):
        path = QPainterPath()
        path.addRoundedRect(
            QRectF(0, 0, self.pixmap().width(), self.pixmap().height()),
            8,
            8
        )

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
        # Los clics solo cuentan dentro del cuadro
        return self.card_path()

    def paint(self, painter, option, widget=None):

        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setRenderHint(QPainter.SmoothPixmapTransform, True)

        path = self.card_path()

        # Imagen recortada con la forma del cuadro
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(self.pixmap()))
        painter.drawPath(path)

        # Borde claro y fino (más marcado si está seleccionado)
        if self.highlight:
            painter.setPen(QPen(QColor(255, 255, 255, 235), 4))
        else:
            painter.setPen(QPen(QColor(225, 235, 255, 150), 2))

        painter.setBrush(Qt.NoBrush)
        painter.drawPath(path)


# Contraseña cambiada con F2: se guarda aquí como huella con sal (PBKDF2).
# Mientras no la cambies, se usa PASSWORD_HASH (la de siempre). Una vez
# cambiada, si este archivo se borra o altera, queda BLOQUEADO (no vuelve
# a la original).
PASSWORD_FILE = os.path.expanduser(
    "~/.config/wallpaper-selector-password.json"
)


PASSWORD_SEAL = os.path.expanduser(
    "~/.config/wallpaper-selector-password.seal"
)


def _seal_of(data):
    return hashlib.sha256(
        (str(data.get("salt")) + str(data.get("hash"))).encode("utf-8")
    ).hexdigest()


def _read_seal():
    try:
        with open(PASSWORD_SEAL, "r", encoding="ascii") as f:
            return f.read().strip()
    except OSError:
        return ""


def check_password(text):
    # True si el texto es la contraseña vigente.
    # Si la contraseña ya se cambió con F2 y su archivo falta o fue alterado,
    # NO se vuelve a la contraseña original: queda bloqueado (devuelve False).
    seal = _read_seal()

    try:
        with open(PASSWORD_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        salt = bytes.fromhex(data["salt"])
        expected = bytes.fromhex(data["hash"])
        iterations = int(data["iterations"])

    except FileNotFoundError:
        if seal:
            return False

        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()

        return hmac.compare_digest(digest, PASSWORD_HASH)

    except Exception:
        return False

    if seal and seal != _seal_of(data):
        return False

    digest = hashlib.pbkdf2_hmac(
        "sha256", text.encode("utf-8"), salt, iterations
    )

    return hmac.compare_digest(digest, expected)


def save_password(new):
    salt = os.urandom(16)
    iterations = 600000

    digest = hashlib.pbkdf2_hmac(
        "sha256", new.encode("utf-8"), salt, iterations
    )

    data = {
        "salt": salt.hex(),
        "hash": digest.hex(),
        "iterations": iterations,
    }

    os.makedirs(os.path.dirname(PASSWORD_FILE), exist_ok=True)

    with open(PASSWORD_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f)

    with open(PASSWORD_SEAL, "w", encoding="ascii") as f:
        f.write(_seal_of(data))

    os.chmod(PASSWORD_FILE, 0o600)
    os.chmod(PASSWORD_SEAL, 0o600)


class PasswordDialog(QDialog):
    # Campo de contraseña: solo un rectángulo semitransparente con el texto
    # (puntos) dentro. Sin botones. Enter acepta, Esc cancela.
    STYLE = """
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

    def __init__(self, parent=None, hint=""):
        super().__init__(parent)

        self.setWindowFlags(
            Qt.Dialog | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setModal(True)
        self.setFixedSize(360, 52)

        self.field = QLineEdit(self)
        self.field.setEchoMode(QLineEdit.Password)
        self.field.setAlignment(Qt.AlignCenter)
        self.field.setFixedSize(360, 52)  # el rectángulo ocupa todo el cuadro
        self.field.setStyleSheet(self.STYLE)


        # Texto de ayuda propio (el de Qt no se ve con el campo enfocado):
        # se muestra mientras el campo está vacío y desaparece al escribir
        self.hint_label = QLabel(hint, self.field)
        self.hint_label.setAlignment(Qt.AlignCenter)
        self.hint_label.setGeometry(0, 0, 360, 52)
        self.hint_label.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.hint_label.setStyleSheet(
            "background: transparent; border: none; font-size: 18px;"
            "color: rgba(255, 255, 255, 140);"
        )
        self.hint_label.setVisible(bool(hint))
        self.field.textChanged.connect(
            lambda texto: self.hint_label.setVisible(bool(hint) and not texto)
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.field)

        self.field.returnPressed.connect(self.accept)

    def showEvent(self, event):
        super().showEvent(event)

        if self.parent() is not None:
            center = self.parent().frameGeometry().center()
            self.move(center - self.rect().center())

        self.activateWindow()
        self.field.setFocus()


def ask_password(parent=None, hint=""):
    # Devuelve el texto escrito, o None si se canceló
    dialog = PasswordDialog(parent, hint)

    if dialog.exec() == QDialog.Accepted:
        return dialog.field.text()

    return None


# ---- Barra superior, favoritos y fondos ocultos (se manejan desde el selector) ----
import colorsys

from PySide6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QPushButton,
    QGraphicsSimpleTextItem
)
from PySide6.QtWidgets import QLabel, QLineEdit, QGraphicsView
from PySide6.QtCore import (
    Qt, QPropertyAnimation, QEasingCurve, QPointF, QPoint, QRectF, QTimer,
    Signal
)
from PySide6.QtGui import (
    QPolygonF, QPainter, QPen, QBrush, QColor, QFont, QImage
)

# Aquí se guardan tus favoritos y los fondos que ocultaste con la tecla
# Supr (así no tienes que editar archivos ni código)
DATA_FILE = os.path.expanduser("~/.config/wallpaper-selector-data.json")

# Posición y tamaño de la estrella / marca de oculto sobre cada tarjeta
BADGE_POS = (14, 10)  # BADGE
BADGE_SIZE = 30  # BADGE

COLOR_NAMES = [
    "Rojo", "Naranja", "Amarillo", "Verde",
    "Azul", "Morado", "Rosa", "Gris"
]
COLOR_SWATCH = [
    "#e5484d", "#f08a24", "#f5d90a", "#30a46c",
    "#3e8bff", "#8e4ec6", "#e93d82", "#8b8d98"
]


TYPE_NAMES = [
    ("imagen", "Imagen"),
    ("escena", "Escena"),
    ("video", "Vídeo"),
    ("web", "Web"),
]


def kind_of(is_engine, is_video, wtype):
    # Tipo del fondo: imagen, escena, vídeo o web
    if is_engine:
        wtype = wtype.casefold()

        if wtype == "scene":
            return "escena"
        if wtype == "video":
            return "video"
        if wtype in ("image", "picture"):
            return "imagen"

        return "web"

    return "video" if is_video else "imagen"


def wp_key(path):
    # Identifica un fondo por su ruta real (resuelve enlaces simbólicos)
    try:
        return os.path.realpath(path)
    except OSError:
        return path


def load_data():
    data = {"favoritos": [], "ocultos": []}

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as file:
            stored = json.load(file)

        for name in data:
            values = stored.get(name, [])

            if isinstance(values, list):
                data[name] = [v for v in values if isinstance(v, str)]

    except (OSError, ValueError, AttributeError):
        pass

    return data


def save_data():
    try:
        os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
        temp = DATA_FILE + ".tmp"

        with open(temp, "w", encoding="utf-8") as file:
            json.dump(DATA, file, ensure_ascii=False, indent=1)

        os.chmod(temp, 0o600)
        os.replace(temp, DATA_FILE)

    except OSError as error:
        print(f"No se pudo guardar favoritos/ocultos: {error}")


DATA = load_data()


def classify_hue(hue):
    # Tono (0-360) a una de las 7 familias de color
    if hue < 15 or hue >= 345:
        return 0
    if hue < 45:
        return 1
    if hue < 70:
        return 2
    if hue < 170:
        return 3
    if hue < 255:
        return 4
    if hue < 290:
        return 5
    return 6


def dominant_color(image):
    # Color que domina en la imagen: 0-6 = familias de color, 7 = gris
    try:
        small = image.scaled(
            24, 24, Qt.IgnoreAspectRatio, Qt.FastTransformation
        ).convertToFormat(QImage.Format_RGB32)

        votes = [0.0] * 7
        colored = 0

        for y in range(24):
            for x in range(24):
                c = QColor(small.pixel(x, y))
                h, s, v = colorsys.rgb_to_hsv(
                    c.red() / 255, c.green() / 255, c.blue() / 255
                )

                if s < 0.18 or v < 0.15:
                    continue

                colored += 1
                votes[classify_hue(h * 360)] += s * v

    except Exception:
        return None

    if colored < 24 * 24 * 0.25:
        return 7

    return max(range(7), key=lambda i: votes[i])


class SearchBox(QLineEdit):

    escaped = Signal()

    def __init__(self):
        super().__init__()
        self.setFixedSize(190, 28)
        self.setFocusPolicy(Qt.ClickFocus)
        self.setStyleSheet(
            "QLineEdit{color:#f2f2f4;background:rgba(255,255,255,22);"
            "border:none;border-radius:14px;padding:0 12px;"
            "font-size:13px;}"
        )
        # Texto de ayuda propio (el de Qt a veces no se ve)
        self.hint = QLabel("Buscar…  (Ctrl+F)", self)
        self.hint.setStyleSheet(
            "color:rgba(255,255,255,150);background:transparent;"
            "font-size:13px;"
        )
        self.hint.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.hint.setGeometry(13, 0, 170, 28)
        self.textChanged.connect(
            lambda text: self.hint.setVisible(not text)
        )

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.escaped.emit()
            return

        super().keyPressEvent(event)


class ColorStrip(QWidget):
    # Barras diagonales de color, todas juntas sin espacio entre ellas
    STEP = 12
    SLANT = 6
    HEIGHT = 28

    def __init__(self, on_pick):
        super().__init__()
        self.on_pick = on_pick
        self.selected = None
        self.hover = None
        self.setMouseTracking(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setFocusPolicy(Qt.NoFocus)
        self.setFixedSize(
            self.STEP * len(COLOR_SWATCH) + self.SLANT, self.HEIGHT
        )

    def bar_at(self, point):
        y = point.y()

        if not 0 <= y <= self.HEIGHT:
            return None

        left = self.SLANT * (1 - y / self.HEIGHT)
        index = int((point.x() - left) // self.STEP)

        if 0 <= index < len(COLOR_SWATCH) and point.x() >= left:
            return index

        return None

    def polygon(self, i):
        x = i * self.STEP
        h = self.HEIGHT
        return QPolygonF([
            QPointF(x + self.SLANT, 0), QPointF(x + self.SLANT + self.STEP, 0),
            QPointF(x + self.STEP, h), QPointF(x, h)
        ])

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(Qt.NoPen)

        for i, code in enumerate(COLOR_SWATCH):
            painter.setBrush(QColor(code))
            painter.drawPolygon(self.polygon(i))

        # La barra elegida (o la que tiene el mouse) se marca con borde
        for index, alpha, width in (
            (self.hover, 170, 1.5), (self.selected, 255, 2.2)
        ):
            if index is not None:
                painter.setPen(QPen(QColor(255, 255, 255, alpha), width))
                painter.setBrush(Qt.NoBrush)
                painter.drawPolygon(self.polygon(index))

        painter.end()

    def mouseMoveEvent(self, event):
        index = self.bar_at(event.position())

        if index != self.hover:
            self.hover = index
            self.setToolTip(COLOR_NAMES[index] if index is not None else "")
            self.update()

    def leaveEvent(self, event):
        self.hover = None
        self.update()
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        index = self.bar_at(event.position())

        if index is not None:
            self.on_pick(index)


class FilterPanel(QWidget):
    # Ventanita "Filtros / Tipos" con casillas: Imagen, Escena, Vídeo, Web

    def __init__(self, view):
        super().__init__(view)
        self.view = view
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFocusPolicy(Qt.NoFocus)
        self.setStyleSheet(
            "QLabel{color:#f2f2f4;background:transparent;}"
            "QPushButton{color:#ececee;background:rgba(255,255,255,26);"
            "border:none;border-radius:10px;padding:0 16px;"
            "font-size:15px;min-height:34px;}"
            "QPushButton:hover{background:rgba(255,255,255,50);}"
            "QPushButton:!checked{color:rgba(255,255,255,120);}"
        )

        column = QVBoxLayout(self)
        column.setContentsMargins(22, 16, 22, 20)
        column.setSpacing(10)

        title = QLabel("Filtros")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size:22px;color:#f2f2f4;")
        column.addWidget(title)

        label = QLabel("Tipos")
        label.setStyleSheet("font-size:15px;color:rgba(255,255,255,200);")
        column.addWidget(label)

        row = QHBoxLayout()
        row.setSpacing(10)
        self.chips = {}

        for key, name in TYPE_NAMES:
            chip = QPushButton("✓ " + name)
            chip.setCheckable(True)
            chip.setChecked(True)
            chip.setFocusPolicy(Qt.NoFocus)
            chip.setCursor(Qt.PointingHandCursor)
            chip.clicked.connect(
                lambda checked=False, k=key, n=name, c=chip:
                self.toggle(k, n, c)
            )
            self.chips[key] = chip
            row.addWidget(chip)

        column.addLayout(row)
        self.adjustSize()
        self.hide()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(QPen(QColor(255, 255, 255, 36), 1))
        painter.setBrush(QColor(38, 38, 40, 238))
        painter.drawRoundedRect(
            QRectF(0.5, 0.5, self.width() - 1, self.height() - 1), 20, 20
        )
        painter.end()

    def toggle(self, key, name, chip):
        chip.setText(("✓ " if chip.isChecked() else "") + name)

        if chip.isChecked():
            self.view.filter_types.add(key)
        else:
            self.view.filter_types.discard(key)

        self.view.apply_filters()

    def sync(self):
        for key, name in TYPE_NAMES:
            chip = self.chips[key]
            chip.setChecked(key in self.view.filter_types)
            chip.setText(("✓ " if chip.isChecked() else "") + name)

    def open_at(self, x, y):
        self.adjustSize()
        self.move(x, y)
        self.show()
        self.raise_()


class TopBar(QWidget):

    MODES = [
        ("todos", "Todos"),
        ("fav", "★ Favoritos"),
    ]

    def __init__(self, view):
        super().__init__(view)
        self.view = view
        self.shown = False
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFocusPolicy(Qt.NoFocus)
        self.setStyleSheet(
            "QPushButton{color:#ececee;background:rgba(255,255,255,20);"
            "border:none;border-radius:14px;padding:0 14px;"
            "font-size:13px;min-height:28px;}"
            "QPushButton:hover{background:rgba(255,255,255,48);}"
            "QPushButton:checked{background:rgba(255,255,255,215);"
            "color:#141416;}"
            "QLabel{color:rgba(255,255,255,170);font-size:13px;"
            "background:transparent;}"
        )

        row = QHBoxLayout(self)
        row.setContentsMargins(18, 9, 18, 9)
        row.setSpacing(7)

        self.mode_buttons = {}

        for key, text in self.MODES:
            button = QPushButton(text)
            button.setCheckable(True)
            button.setFocusPolicy(Qt.NoFocus)
            button.setCursor(Qt.PointingHandCursor)
            button.clicked.connect(
                lambda checked=False, k=key: self.set_mode(k)
            )
            self.mode_buttons[key] = button
            row.addWidget(button)

        self.mode_buttons["todos"].setChecked(True)
        row.addSpacing(12)

        # Botón que abre la ventana de filtros por tipo
        self.filter_button = QPushButton("Filtros ▾")
        self.filter_button.setCheckable(True)
        self.filter_button.setFocusPolicy(Qt.NoFocus)
        self.filter_button.setCursor(Qt.PointingHandCursor)
        self.filter_button.clicked.connect(self.toggle_panel)
        row.addWidget(self.filter_button)

        row.addSpacing(12)

        self.strip = ColorStrip(self.set_color)
        row.addWidget(self.strip)

        row.addSpacing(12)

        self.search = SearchBox()
        self.search.textChanged.connect(self.on_text)
        self.search.escaped.connect(self.on_escape)
        self.search.returnPressed.connect(self.view.setFocus)
        row.addWidget(self.search)

        self.counter = QLabel("")
        self.counter.setMinimumWidth(74)
        self.counter.setAlignment(Qt.AlignCenter)
        row.addWidget(self.counter)

        self.panel = FilterPanel(view)
        self.adjustSize()

        self.slide = QPropertyAnimation(self, b"pos")
        self.slide.setDuration(220)
        self.slide.setEasingCurve(QEasingCurve.OutCubic)
        self.slide.finished.connect(self.after_slide)

        self.hide_timer = QTimer(self)
        self.hide_timer.setSingleShot(True)
        self.hide_timer.timeout.connect(self.auto_hide)

        self.counter_timer = QTimer(self)
        self.counter_timer.timeout.connect(self.update_counter)
        self.counter_timer.start(250)

        self.hide()

    # ---- apariencia ----
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(QPen(QColor(255, 255, 255, 38), 1))
        painter.setBrush(QColor(18, 20, 24, 210))
        painter.drawRoundedRect(
            QRectF(0.5, 0.5, self.width() - 1, self.height() - 1),
            self.height() / 2, self.height() / 2
        )
        painter.end()

    def home(self):
        return QPoint((self.view.width() - self.width()) // 2, 16)

    def away(self):
        return QPoint((self.view.width() - self.width()) // 2,
                      -self.height() - 6)

    # ---- mostrar y ocultar ----
    def reveal(self):
        self.hide_timer.start(1800)

        if self.shown:
            return

        self.shown = True
        self.slide.stop()
        if not self.isVisible():
            self.move(self.away())
            self.show()
        self.raise_()
        self.slide.setStartValue(self.pos())
        self.slide.setEndValue(self.home())
        self.slide.start()

    def conceal(self):
        if not self.shown:
            return

        self.shown = False
        self.panel.hide()
        self.filter_button.setChecked(False)
        self.search.clearFocus()
        self.view.setFocus()
        self.slide.stop()
        self.slide.setStartValue(self.pos())
        self.slide.setEndValue(self.away())
        self.slide.start()

    def after_slide(self):
        if not self.shown:
            self.hide()

    def toggle(self):
        if self.shown:
            self.conceal()
        else:
            self.reveal()

    def auto_hide(self):
        # No se esconde mientras se usa, o si hay un filtro activo
        if (
            self.underMouse() or
            self.search.hasFocus() or
            self.panel.isVisible() or
            self.view.filters_active()
        ):
            self.hide_timer.start(1800)
            return

        self.conceal()

    def enterEvent(self, event):
        self.hide_timer.stop()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.hide_timer.start(1800)
        super().leaveEvent(event)

    def focus_search(self):
        self.reveal()
        self.hide_timer.stop()
        self.search.setFocus()
        self.search.selectAll()

    # ---- filtros ----
    def set_mode(self, key):
        for name, button in self.mode_buttons.items():
            button.setChecked(name == key)

        self.view.filter_mode = key
        self.view.apply_filters()

    def set_color(self, index):
        current = self.view.filter_color
        new = None if current == index else index

        self.strip.selected = new
        self.strip.update()
        self.view.filter_color = new
        self.view.apply_filters()

    def toggle_panel(self):
        if self.panel.isVisible():
            self.panel.hide()
            self.filter_button.setChecked(False)
        else:
            self.panel.open_at(
                max(10, self.x()), self.y() + self.height() + 8
            )
            self.filter_button.setChecked(True)

    def on_text(self, text):
        self.view.filter_text = text.strip()
        self.view.apply_filters()

    def on_escape(self):
        if self.search.text():
            self.search.clear()
        else:
            self.view.setFocus()

    def sync(self):
        # Refleja en los botones el estado de los filtros
        for name, button in self.mode_buttons.items():
            button.setChecked(name == self.view.filter_mode)

        self.strip.selected = self.view.filter_color
        self.strip.update()
        self.panel.sync()

        if self.search.text() != self.view.filter_text:
            self.search.setText(self.view.filter_text)

    def update_counter(self):
        total = len(self.view.items)

        if total:
            self.counter.setText(
                f"{self.view.selected_index + 1} / {total}"
            )
        else:
            self.counter.setText("0 / 0")


class ThumbnailSignals(QObject):

    loaded = Signal(object, object)

class ThumbnailLoader(QRunnable):

    def __init__(self, path, item):
        super().__init__()

        self.path = path
        self.item = item
        self.signals = ThumbnailSignals()

    def run(self):

        cache_dir = "/tmp/wallpaper_selector_cache"

        os.makedirs(cache_dir, exist_ok=True)

        name = os.path.basename(self.path)

        thumb = os.path.join(
            cache_dir,
            name + ".jpg"
        )

        if not os.path.exists(thumb):

            subprocess.run(
                [
                    "ffmpeg",
                    "-y",
                    "-ss", "00:00:00.5",
                    "-i", self.path,
                    "-vframes", "1",
                    thumb
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        image = QImage(thumb)

        if not image.isNull():

            self.signals.loaded.emit(
                self.item,
                image
            )
class Carousel(QGraphicsView):

    def __init__(self):
        super().__init__()
        self.velocity = 0.0
        # Cuántas columnas se ha movido el selector de su lugar normal
        # (solo cambia al llegar a un límite de la lista)
        self.cursor_offset = 0
        # Cuadro bajo el mouse (None si no hay ninguno)
        self.hover_index = None
        # Posición a la que se deslizan los cuadros con las flechas
        self.target_rotation = None
        # Indica que aún hay cuadros animando su tamaño
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
        # Para que los cuadros reaccionen al pasar el mouse
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
        self.init_bar()

        # True cuando se desbloquearon los fondos privados
        self.show_hidden = False

        # Desplazamiento horizontal del cuadrícula (en píxeles)
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
        # Mientras las columnas se deslizan, el cuadro que queda bajo
        # el mouse (aunque el mouse no se mueva) es el que crece
        if self.dragging:
            return

        point = self.viewport().mapFromGlobal(QCursor.pos())

        if self.viewport().rect().contains(point):
            item = self.item_at(point)
        else:
            item = None

        if item and item in self.items:
            self.hover_index = self.items.index(item)
        else:
            self.hover_index = None

    # ---------- Barra superior, favoritos y ocultar ----------
    def init_bar(self):
        # Todos los fondos creados / los que se ven con el filtro actual
        self.all_items = []
        self.filter_mode = "todos"
        self.filter_color = None
        self.filter_text = ""
        self.filter_types = {key for key, name in TYPE_NAMES}
        # Fondos que ocultaste en esta sesión (para deshacer con Ctrl+Z)
        self.hide_stack = []
        self.target_rotation = None

        self.toast = QLabel(self)
        self.toast.setStyleSheet(
            "color:#f2f2f4;background:rgba(18,20,24,225);"
            "border:1px solid rgba(255,255,255,45);border-radius:17px;"
            "padding:8px 20px;font-size:14px;"
        )
        self.toast.hide()
        self.toast_timer = QTimer(self)
        self.toast_timer.setSingleShot(True)
        self.toast_timer.timeout.connect(self.toast.hide)

        self.bar = TopBar(self)

    def show_toast(self, text):
        self.toast.setText(text)
        self.toast.adjustSize()
        self.toast.move(
            (self.width() - self.toast.width()) // 2,
            self.height() - self.toast.height() - 70
        )
        self.toast.show()
        self.toast.raise_()
        self.toast_timer.start(2800)

    def bar_hint(self, y):
        # Al acercar el mouse al borde superior aparece la barra
        if y < 50:
            self.bar.reveal()

    def item_at(self, point):
        # Si el mouse está sobre la estrella/marca, cuenta la tarjeta
        found = QGraphicsView.itemAt(self, point)

        if found is not None:
            parent = found.parentItem()

            if parent is not None and parent in self.items:
                return parent

        return found

    def filters_active(self):
        return bool(
            self.filter_mode != "todos" or
            self.filter_color is not None or
            self.filter_text or
            len(self.filter_types) < len(TYPE_NAMES)
        )

    def clear_filters(self):
        self.filter_mode = "todos"
        self.filter_color = None
        self.filter_text = ""
        self.filter_types = {key for key, name in TYPE_NAMES}
        self.bar.sync()
        self.apply_filters()

    def item_matches(self, item):
        if self.filter_mode == "fav":
            if item.key not in DATA["favoritos"]:
                return False

        if item.kind not in self.filter_types:
            return False

        if self.filter_color is not None:
            if item.color != self.filter_color:
                return False

        if self.filter_text:
            if self.filter_text.casefold() not in item.name.casefold():
                return False

        return True

    def reset_view(self):
        self.rotation = 0.0
        self.velocity = 0

        for name, value in (
            ("target_rotation", None),
            ("cursor_offset", 0),
            ("hover_index", None),
            ("selected_index", 0),
        ):
            if hasattr(self, name):
                setattr(self, name, value)

    def apply_filters(self, reset=True):
        shown = []

        for item in self.all_items:
            ok = self.item_matches(item)
            item.setVisible(ok)

            if ok:
                shown.append(item)

        self.items = shown

        if reset:
            self.reset_view()
        else:
            self.selected_index = min(
                self.selected_index, max(0, len(shown) - 1)
            )
            if hasattr(self, "hover_index"):
                self.hover_index = None
            self.clamp_rotation()

        self.update_selected()
        self.update_positions()

        if not shown and self.all_items:
            self.show_toast("Ningún fondo coincide con el filtro")

    def target_item(self):
        # El fondo bajo el mouse; si no hay, el seleccionado
        hover = getattr(self, "hover_index", None)

        if hover is not None and 0 <= hover < len(self.items):
            return self.items[hover]

        if self.items and 0 <= self.selected_index < len(self.items):
            return self.items[self.selected_index]

        return None

    def refresh_badge(self, item):
        if item.key in DATA["ocultos"]:
            text, color = "✖", QColor(235, 70, 70)
        elif item.key in DATA["favoritos"]:
            text, color = "★", QColor(255, 255, 255)
        else:
            text, color = "", None

        badge = getattr(item, "badge", None)

        if not text:
            if badge is not None:
                badge.setVisible(False)
            return

        if badge is None:
            badge = QGraphicsSimpleTextItem(item)
            font = QFont()
            font.setPixelSize(BADGE_SIZE)
            font.setBold(True)
            badge.setFont(font)
            badge.setPen(QPen(QColor(0, 0, 0, 190), 1.5))
            badge.setPos(BADGE_POS[0], BADGE_POS[1])
            badge.setAcceptedMouseButtons(Qt.NoButton)
            item.badge = badge

        badge.setText(text)
        badge.setBrush(QBrush(color))
        badge.setVisible(True)

    def toggle_favorite(self):
        item = self.target_item()

        if item is None:
            return

        favorites = DATA["favoritos"]

        if item.key in favorites:
            favorites.remove(item.key)
            message = "Quitado de favoritos"
        else:
            favorites.append(item.key)
            message = "★ Añadido a favoritos"

        save_data()
        self.refresh_badge(item)

        if self.filter_mode == "fav":
            self.apply_filters(reset=False)

        self.show_toast(message)

    def toggle_item_hidden(self):
        # Tecla Supr: oculta el fondo señalado
        item = self.target_item()

        if item is None:
            return

        hidden = DATA["ocultos"]

        if self.show_hidden:
            # Con los privados visibles solo se pone o quita la marca
            if item.key in hidden:
                hidden.remove(item.key)
                message = "Ya no está oculto"
            else:
                hidden.append(item.key)
                message = "✖ Marcado como oculto"

            save_data()
            self.refresh_badge(item)
            self.show_toast(message)
            return

        # Bloqueado: desaparece hasta Ctrl+Shift+H (con contraseña)
        if item.key not in hidden:
            hidden.append(item.key)

        self.hide_stack.append(item.key)
        save_data()

        self.all_items.remove(item)
        self.scene.removeItem(item)
        self.apply_filters(reset=False)
        self.show_toast(
            "Fondo oculto · Ctrl+Z deshace · "
            "Ctrl+Shift+H lo muestra de nuevo"
        )

    def undo_hide(self):
        while self.hide_stack:
            key = self.hide_stack.pop()

            if key in DATA["ocultos"]:
                DATA["ocultos"].remove(key)
                save_data()
                self.reload_wallpapers()
                self.show_toast("Fondo restaurado")
                return

    def update_thumbnail(self, item, image):

        # Si el fondo ya no está en el selector, se ignora
        if item not in self.all_items:
            return

        pix = make_card_pixmap(image)

        item.setPixmap(pix)
        item.cached_width = pix.width()
        item.cached_height = pix.height()
        item.color = dominant_color(image)

        if self.filter_color is not None:
            self.apply_filters(reset=False)
        else:
            self.update_positions()

    def load_wallpapers(self):
        # Lista de fondos: (archivo, imagen de vista previa o "")
        sources = []

        # Obtiene todos los archivos de la carpeta
        if os.path.isdir(FOLDER):

            private = hidden_names()

            for file in sorted(os.listdir(FOLDER)):

                if not self.show_hidden and (
                    file.casefold() in private
                    or os.path.splitext(file)[0].casefold() in private
                ):
                    continue

                sources.append((os.path.join(FOLDER, file), ""))

        # Wallpapers de Wallpaper Engine (Steam Workshop)
        workshop = workshop_wallpapers(
            include_hidden=self.show_hidden
        )
        titles = {w["path"]: w["title"] for w in workshop}
        wtypes = {w["path"]: w["type"] for w in workshop}
        engine = [(w["path"], w["preview"]) for w in workshop]

        if HIDE_UNREGISTERED and engine:

            try:
                catalog = waywallen_catalog()
            except Exception as error:
                # Sin Waywallen no se puede comprobar: se muestran todos
                print(f"No se pudo leer el catálogo de Waywallen: {error}")
                catalog = None

            if catalog is not None:

                registered = []

                for path, preview in engine:

                    try:
                        find_waywallen_id(path, catalog)
                    except Exception:
                        print(f"Oculto (no está en Waywallen): {path}")
                        continue

                    registered.append((path, preview))

                engine = registered

        sources.extend(engine)
        engine_paths = {path for path, _ in engine}

        # Fondos que ocultaste con la tecla Supr
        if not self.show_hidden:
            mine = set(DATA["ocultos"])
            sources = [
                s for s in sources if wp_key(s[0]) not in mine
            ]

        for path, preview in sources:

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

            item = CardItem(pix)
            item.setCacheMode(
                QGraphicsItem.DeviceCoordinateCache
                )
            item.cached_width = pix.width()
            item.cached_height = pix.height()
            # Escala actual (se anima hasta la escala objetivo)
            item.current_scale = None

            item.original_path = path
            item.key = wp_key(path)
            item.name = (
                titles.get(path) or
                os.path.splitext(os.path.basename(path))[0]
            )
            item.kind = kind_of(
                path in engine_paths, is_video,
                wtypes.get(path, "")
            )
            item.color = None if is_video else dominant_color(image)

            item.setParentItem(self.frame)

            self.all_items.append(item)
            self.refresh_badge(item)

            if is_video:

                loader = ThumbnailLoader(path, item)

                loader.signals.loaded.connect(
                    self.update_thumbnail)
                self.thread_pool.start(loader)

        self.apply_filters()

    def layout_metrics(self):
        # Tamaños del cuadrícula según la altura de la pantalla
        unit = self.height() / 1080
        base = CARD_SCALE * unit

        # Distancia entre columnas y entre filas
        dx = (CARD_W + CARD_GAP) * base
        dy = (CARD_H + CARD_GAP) * base

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
        # Centro de cada cuadro en pantalla (columna por columna)
        col = i // ROWS
        row = i % ROWS

        pos_x = start_x + self.column_slot(col, dx) * dx

        pos_y = (
            self.height() / 2
            + (row - (ROWS - 1) / 2) * dy
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
        # El selector es el cuadro del medio de una columna. Normalmente
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
        half_w = CARD_W * base / 2
        margin = dx * 0.2
        left = start_x - half_w - margin
        right = start_x + (FULL_COLS) * dx + half_w + margin
        half_h = dy + CARD_H * base * SELECTED_SCALE / 2 + 10

        self.frame.setRect(
            QRectF(left, cy - half_h, right - left, 2 * half_h)
        )

        settling = False

        for i, item in enumerate(self.items):

            pos_x, pos_y = self.item_center(i, dx, dy, start_x)

            # Escala: el seleccionado se expande
            target = base

            if self.hover_index is not None:
                # Con el mouse sobre un cuadro, solo ese crece
                if i == self.hover_index:
                    target *= HOVER_SCALE
                    item.setZValue(10)
                else:
                    item.setZValue(0)

            elif i == self.selected_index:
                # Sin mouse encima, crece el cuadro del selector
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

        path = self.items[self.selected_index].original_path

        try:
            catalog = waywallen_catalog()
            wallpaper_id = find_waywallen_id(path, catalog)

            try:
                result = subprocess.run([
                    "busctl", "--user", "call",
                    "org.waywallen.waywallen.Daemon",
                    "/org/waywallen/waywallen/Daemon",
                    "org.waywallen.waywallen.Daemon1",
                    "ApplyById", "s", wallpaper_id
                ], capture_output=True, text=True, check=True, timeout=15)

                output = result.stdout.strip()

            except subprocess.TimeoutExpired:
                # Las escenas pesadas tardan en cargar: Waywallen ya
                # recibió el pedido, solo no contestó a tiempo
                output = "Waywallen tarda en responder, el fondo se está cargando"

            os.makedirs(
                os.path.dirname(CURRENT_WALLPAPER),
                exist_ok=True
            )

            with open(CURRENT_WALLPAPER, "w") as f:
                f.write(path)

            print(f"Fondo enviado a Waywallen: {os.path.basename(path)}")
            print(output)
            self.close()

        except Exception as error:
            print(f"No se pudo aplicar el fondo: {error}")

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
            # Mientras se arrastra, ningún cuadro crece por el mouse
            self.hover_index = None

    def leaveEvent(self, event):

        # Si el mouse sale de la ventana, el cuadro vuelve a su tamaño
        self.hover_index = None
        self.update_positions()

        super().leaveEvent(event)

    def mouseMoveEvent(self, event):
        self.bar_hint(event.position().y())


        if not self.dragging:

            # Al pasar el mouse sobre un cuadro se agranda un poco.
            # El selector no sigue al mouse: se queda en su lugar.
            item = self.item_at(
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

        # El cuadrícula sigue al mouse mientras se mantiene el clic
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

            item = self.item_at(
                event.position().toPoint()
            )

            if item and item in self.items:

                self.selected_index = self.items.index(item)

                self.update_positions()

                self.apply_wallpaper()

    def toggle_hidden(self):
        # Ctrl + Shift + H: pide la contraseña y muestra los fondos
        # privados; si ya están visibles, los vuelve a ocultar
        if self.show_hidden:
            self.show_hidden = False

        else:
            password = ask_password(self)

            if password is None:
                return

            # Si es incorrecta no avisa de nada
            if not check_password(password):
                return

            self.show_hidden = True

        self.reload_wallpapers()

    def change_password(self):
        # F2: para cambiar la contraseña hay que escribir primero la actual
        current = ask_password(self, "Contraseña actual")

        if current is None:
            return

        if not check_password(current):
            QMessageBox.warning(
                self, "Contraseña", "La contraseña actual no es correcta."
            )
            return

        first = ask_password(self, "Contraseña nueva")

        if first is None:
            return

        if len(first) < 4:
            QMessageBox.warning(
                self, "Contraseña", "Debe tener al menos 4 caracteres."
            )
            return

        second = ask_password(self, "Repita la contraseña")

        if second is None:
            return

        if first != second:
            QMessageBox.warning(
                self, "Contraseña", "Las contraseñas no coinciden."
            )
            return

        try:
            save_password(first)
        except OSError as error:
            QMessageBox.warning(
                self, "Contraseña", f"No se pudo guardar: {error}"
            )
            return

        QMessageBox.information(self, "Contraseña", "Contraseña actualizada.")

    def reload_wallpapers(self):
        # Vuelve a cargar los fondos (con o sin los privados)
        for item in self.all_items:
            self.scene.removeItem(item)

        self.all_items = []
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

        # Barra superior, favoritos y ocultar
        key = event.key()
        ctrl = bool(event.modifiers() & Qt.ControlModifier)
        shift = bool(event.modifiers() & Qt.ShiftModifier)

        if ctrl and not shift and key == Qt.Key_F:
            self.bar.focus_search()
            return

        if ctrl and not shift and key == Qt.Key_Z:
            self.undo_hide()
            return

        if not ctrl:
            if key == Qt.Key_F:
                self.toggle_favorite()
                return

            if key == Qt.Key_Delete:
                self.toggle_item_hidden()
                return

            if key == Qt.Key_B:
                self.bar.toggle()
                return

            if key == Qt.Key_Escape and self.filters_active():
                self.clear_filters()
                return

        # Interruptor escondido de los fondos privados
        if (
            event.key() == Qt.Key_H and
            event.modifiers() & Qt.ControlModifier and
            event.modifiers() & Qt.ShiftModifier
        ):
            self.toggle_hidden()
            return

        # F2: cambiar la contraseña (pide la actual)
        if event.key() == Qt.Key_F2:
            self.change_password()
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

if __name__ == "__main__":

    # python selector2_fondo.py --catalog
    # muestra lo que Waywallen tiene registrado (para revisar rutas)
    if "--catalog" in sys.argv:

        for entry in waywallen_catalog():
            print(
                entry["id"], entry["type"],
                entry["size"], entry["resource"]
            )

        sys.exit(0)

    # python nombre_del_archivo.py --listar
    # muestra tus wallpapers de Wallpaper Engine con su número de carpeta
    if "--listar" in sys.argv:

        for wallpaper in workshop_wallpapers(include_hidden=True):
            print(
                wallpaper["id"], "|", wallpaper["title"], "|",
                wallpaper["type"],
                "| (oculto)" if wallpaper["hidden"] else ""
            )

        sys.exit(0)

    app = QApplication(sys.argv)

    w = Carousel()
    w.showFullScreen()

    sys.exit(app.exec())
