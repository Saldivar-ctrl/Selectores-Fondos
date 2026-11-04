"""Función heredada de los selectores originales (set_video_wallpaper).

Los selectores originales la traían pero NO la usaban: aplicaban los fondos
con waywallen. Se conserva aquí, separada, para no perder la función.

Qué hace: edita ~/.config/plasma-org.kde.plasma.desktop-appletsrc para
activar el plugin "Smart Video Wallpaper Reborn" de KDE Plasma con un vídeo
y reinicia plasmashell.

ADVERTENCIA: modifica la configuración de Plasma y reinicia el escritorio.
Por eso no está conectada a ningún selector ni a ningún backend; solo se
ejecuta si tú la llamas a propósito.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path


def set_video_wallpaper(video_path):

    config = Path.home() / ".config" / "plasma-org.kde.plasma.desktop-appletsrc"

    text = config.read_text(encoding="utf-8")

    file_url = "file://" + str(video_path)

    # Activar el plugin de video
    text = re.sub(
        r"wallpaperplugin=org\.kde\.image",
        "wallpaperplugin=luisbocanegra.smart.video.wallpaper.reborn",
        text,
        flags=re.IGNORECASE
    )

    text = re.sub(r"LastVideo=.*", f"LastVideo={file_url}", text)
    text = re.sub(r"ResumeLastVideo=.*", "ResumeLastVideo=true", text)

    config.write_text(text, encoding="utf-8")

    subprocess.run(["kquitapp6", "plasmashell"])

    subprocess.Popen(
        ["plasmashell"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
