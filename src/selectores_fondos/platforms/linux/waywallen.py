"""Linux: waywallen (https://github.com/waywallen/waywallen).

Cómo se conecta (esto es lo que hacían los selectores originales):

 1. waywallen corre como un daemon con un servicio D-Bus de sesión
    (org.waywallen.waywallen.Daemon). Se lee su puerto WebSocket con
    `busctl --user get-property ... WsPort`.
 2. Por ese WebSocket se pide el catálogo (mensajes protobuf mínimos
    escritos a mano, sin dependencias) para saber el id de cada fondo.
 3. Para aplicar un fondo se llama por D-Bus: `busctl --user call ...
    ApplyById s <id>`.

Nota de verificación: el README público de waywallen no documenta la
interfaz D-Bus ni el protocolo del catálogo. Los nombres de abajo salen
del código que ya funcionaba en el equipo del autor (Bazzite + KDE Plasma +
waywallen por Flatpak). Una versión futura de waywallen podría cambiarlos.

No requiere Docker ni Podman: solo `busctl` (viene con systemd) y la
biblioteca de Python `websockets`.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess

from ..base import Backend, ErrorBackend, Estado

BUS = "org.waywallen.waywallen.Daemon"
RUTA_OBJETO = "/org/waywallen/waywallen/Daemon"
INTERFAZ = "org.waywallen.waywallen.Daemon1"
FLATPAK_ID = "org.waywallen.waywallen"

# Escritorios que el README de waywallen lista como integrados
ESCRITORIOS_DOCUMENTADOS = (
    "kde", "gnome", "hyprland", "niri", "wayfire", "sway", "cosmic",
)


# ------------------------------------------------------------ protobuf
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


def parsear_respuesta_catalogo(frame):
    """Convierte un frame protobuf en la lista del catálogo.

    Devuelve None si el frame no es la respuesta a nuestra petición (id 1).
    Lanza RuntimeError si waywallen respondió con un error.
    """
    for number, wire, payload in _ww_fields(frame):
        if number != 1 or wire != 2:
            continue

        response = list(_ww_fields(payload))

        request_id = next(
            (v for f, k, v in response if f == 1 and k == 0), None
        )

        if request_id != 1:
            continue

        listing = next(
            (v for f, k, v in response if f == 19 and k == 2), None
        )

        if listing is None:
            message = next(
                (
                    v.decode("utf-8", errors="replace")
                    for f, k, v in response if f == 3 and k == 2
                ),
                "Waywallen no devolvió el catálogo",
            )
            raise RuntimeError(message)

        catalog = []

        for field, kind, entry_data in _ww_fields(listing):
            if field != 1 or kind != 2:
                continue

            entry = {}

            for num, wire_type, value in _ww_fields(entry_data):
                if num in (1, 2, 3, 4) and wire_type == 2:
                    entry[num] = value.decode("utf-8", errors="replace")
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

    return None


# ------------------------------------------------------------- daemon
def puerto_websocket() -> int:
    salida = subprocess.check_output([
        "busctl", "--user", "get-property",
        BUS, RUTA_OBJETO, INTERFAZ, "WsPort",
    ], text=True, timeout=5, stderr=subprocess.PIPE)

    return int(salida.split()[-1])


def waywallen_catalog():
    try:
        from websockets.sync.client import connect
    except ImportError as error:
        raise ErrorBackend(
            "Falta la biblioteca 'websockets'. Instálala con:\n"
            "  python -m pip install websockets"
        ) from error

    try:
        port = puerto_websocket()
    except FileNotFoundError as error:
        raise ErrorBackend(
            "No se encontró 'busctl' (parte de systemd)."
        ) from error
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired,
            ValueError, IndexError) as error:
        raise ErrorBackend(
            "No se pudo hablar con waywallen. ¿Está instalado y en "
            "ejecución en esta sesión?"
        ) from error

    request = bytes([8, 1, 154, 1, 0])

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

            try:
                catalog = parsear_respuesta_catalogo(frame)
            except RuntimeError as error:
                raise ErrorBackend(str(error)) from error

            if catalog is not None:
                return catalog


def find_waywallen_id(path, catalog):
    """Busca el id de waywallen de un archivo local.

    Para Wallpaper Engine prueba, en orden: ruta exacta, misma carpeta,
    número de carpeta de Steam y título. Para archivos sueltos: nombre y
    tamaño. Se comparan rutas reales (realpath) porque ~/.steam/steam es
    un enlace simbólico en muchas distribuciones.
    """
    filename = os.path.basename(path)
    local_size = os.path.getsize(path)
    directory = os.path.normpath(os.path.dirname(path))

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

        workshop_id = os.path.basename(directory)

        if workshop_id.isdigit():

            by_id = [
                item for item in catalog
                if ("/" + workshop_id + "/") in item["resource"]
                or item["resource"].rstrip("/").endswith("/" + workshop_id)
            ]

            if len(by_id) == 1:
                return by_id[0]["id"]

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
                if item["name"].strip().casefold() == title.strip().casefold()
            ]

            if len(by_title) == 1:
                return by_title[0]["id"]

    candidates = [
        item for item in catalog
        if os.path.basename(item["resource"]) == filename
    ]

    if not candidates:
        raise ValueError(
            f"'{filename}' no está registrado en Waywallen ({path}). "
            "Añádelo a su biblioteca y vuelve a intentarlo."
        )

    exact = [item for item in candidates if item["size"] == local_size]

    if len(exact) == 1:
        return exact[0]["id"]

    if len(exact) > 1:
        raise ValueError(f"Hay varios recursos coincidentes para '{filename}'.")

    if len(candidates) == 1 and candidates[0]["size"] == 0:
        return candidates[0]["id"]

    raise ValueError(f"No se encontró una coincidencia inequívoca para '{filename}'.")


# ------------------------------------------------------------ detección
def waywallen_instalado() -> str:
    """Describe cómo está instalado waywallen ('' si no se detecta)."""
    if shutil.which("waywallen"):
        return "binario en el PATH"

    flatpak = shutil.which("flatpak")

    if flatpak:
        try:
            r = subprocess.run(
                [flatpak, "info", FLATPAK_ID],
                capture_output=True, text=True, timeout=10,
            )
            if r.returncode == 0:
                return "Flatpak (" + FLATPAK_ID + ")"
        except (OSError, subprocess.TimeoutExpired):
            pass

    return ""


class WaywallenBackend(Backend):
    id = "waywallen"
    nombre = "waywallen (Linux, Wayland)"
    usa_wallpaper_engine = True  # con el plugin open-wallpaper-engine

    def comprobar(self) -> Estado:
        detalles = []
        ok = True

        sesion = os.environ.get("XDG_SESSION_TYPE", "desconocida")
        escritorio = os.environ.get("XDG_CURRENT_DESKTOP", "desconocido")
        detalles.append(f"Sesión: {sesion} · Escritorio: {escritorio}")

        if sesion.lower() == "x11":
            detalles.append(
                "AVISO: la documentación de waywallen solo describe "
                "compositores Wayland; X11 no está documentado."
            )

        if not any(e in escritorio.lower() for e in ESCRITORIOS_DOCUMENTADOS):
            detalles.append(
                "AVISO: tu escritorio no está en la lista de integraciones "
                "documentadas de waywallen (" +
                ", ".join(ESCRITORIOS_DOCUMENTADOS) + ")."
            )

        if not shutil.which("busctl"):
            ok = False
            detalles.append(
                "FALTA 'busctl' (paquete systemd). Sin él no se puede "
                "hablar con waywallen."
            )

        try:
            import websockets  # noqa: F401
        except ImportError:
            ok = False
            detalles.append(
                "FALTA la biblioteca 'websockets': "
                "python -m pip install websockets"
            )

        if ok:
            try:
                puerto = puerto_websocket()
                detalles.append(f"waywallen responde (puerto WebSocket {puerto}).")
            except Exception:
                ok = False
                instalado = waywallen_instalado()

                if instalado:
                    detalles.append(
                        f"waywallen está instalado ({instalado}) pero no "
                        "responde: ábrelo/inícialo en esta sesión."
                    )
                else:
                    detalles.append(
                        "waywallen no está instalado o no se detecta. "
                        "Instálalo desde Flathub (flatpak install flathub "
                        f"{FLATPAK_ID}) o con el AppImage de su página de "
                        "Releases: https://github.com/waywallen/waywallen"
                    )

        return Estado(
            ok,
            "waywallen listo" if ok else "waywallen no está listo",
            detalles,
        )

    def filtrar_registrados(self, fondos: list) -> list:
        if not fondos or not self.config.ocultar_no_registrados:
            return fondos

        try:
            catalogo = waywallen_catalog()
        except Exception as error:
            # Sin waywallen no se puede comprobar: se muestran todos
            print(f"No se pudo leer el catálogo de Waywallen: {error}")
            return fondos

        registrados = []

        for fondo in fondos:
            try:
                find_waywallen_id(fondo.path, catalogo)
            except Exception:
                print(f"Oculto (no está en Waywallen): {fondo.path}")
                continue

            registrados.append(fondo)

        return registrados

    def aplicar(self, fondo) -> str:
        if not os.path.exists(fondo.path):
            raise ErrorBackend(f"El archivo ya no existe: {fondo.path}")

        catalogo = waywallen_catalog()

        try:
            wallpaper_id = find_waywallen_id(fondo.path, catalogo)
        except (ValueError, OSError) as error:
            raise ErrorBackend(str(error)) from error

        try:
            resultado = subprocess.run([
                "busctl", "--user", "call",
                BUS, RUTA_OBJETO, INTERFAZ,
                "ApplyById", "s", wallpaper_id,
            ], capture_output=True, text=True, check=True, timeout=15)

            salida = resultado.stdout.strip()

        except subprocess.TimeoutExpired:
            # Las escenas pesadas tardan en cargar: waywallen ya recibió
            # el pedido, solo no contestó a tiempo
            salida = "waywallen tarda en responder; el fondo se está cargando"

        except subprocess.CalledProcessError as error:
            raise ErrorBackend(
                "waywallen rechazó el fondo: "
                + (error.stderr or str(error)).strip()
            ) from error

        return f"Fondo enviado a waywallen: {os.path.basename(fondo.path)} {salida}".strip()
