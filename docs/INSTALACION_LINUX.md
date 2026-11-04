# Instalación en Linux

> **Estado:** la comunicación con waywallen viene del código que ya funcionaba en Bazzite + KDE Plasma (Wayland) del autor. Las demás distribuciones **no se han probado**; los comandos son los habituales de cada familia (ver [PRUEBAS.md](PRUEBAS.md)).

## 1. Qué es waywallen y qué necesita

[waywallen](https://github.com/waywallen/waywallen) es un gestor de fondos dinámicos para Linux (imagen, vídeo con decodificación por hardware Vulkan/VA-API; escenas y web mediante un complemento externo de Wallpaper Engine). Corre como un *daemon* y se integra con:

| Escritorio | Integración (según su README) |
|---|---|
| KDE Plasma, GNOME | `waywallen-display` |
| Hyprland, Niri, Wayfire, COSMIC | `waywallen-display/layer_shell` |
| Sway | `layer_shell` (sin pausa automática) |

- **Wayland** es lo documentado. **X11 no aparece en su documentación**: los selectores abren en X11, pero no hay garantía de que waywallen funcione; el instalador te avisa.
- **No necesita Podman ni Docker.** Se instala como Flatpak (`org.waywallen.waywallen`), AppImage o desde el código fuente.
- El README público de waywallen **no documenta** su interfaz D-Bus ni el protocolo del catálogo; el proyecto usa los que ya funcionaban en el equipo del autor. Una versión futura de waywallen podría cambiarlos.
- Los selectores hablan con waywallen con `busctl` (de systemd) y la biblioteca de Python `websockets`.

## 2. Requisitos

Python 3.9+ (recomendado 3.12), `python3-venv`/`pip`, `busctl` (paquete systemd), waywallen en ejecución, y opcionalmente `ffmpeg` para miniaturas.

## 3. Instalar por distribución

Instalar paquetes del sistema necesita permisos de administrador; el instalador del proyecto **no lo hace**, solo te muestra el comando.

**Fedora**
```bash
sudo dnf install python3 python3-pip ffmpeg
flatpak install flathub org.waywallen.waywallen
```
(En Fedora, `ffmpeg` completo viene de RPM Fusion.)

**Bazzite (y otros sistemas inmutables rpm-ostree)** — no uses `rpm-ostree install` para esto. Python y systemd ya vienen; usa Flatpak y un entorno virtual de usuario:
```bash
flatpak install flathub org.waywallen.waywallen
bash scripts/instalar_linux.sh
```
Si falta `ffmpeg`, Bazzite lo trae normalmente; si no, usa un Flatpak o un contenedor `distrobox` (no hace falta nada de eso para el selector en sí).

**Ubuntu / Debian / Linux Mint**
```bash
sudo apt install python3 python3-venv python3-pip ffmpeg flatpak
flatpak install flathub org.waywallen.waywallen
```
(Si falta Flathub: `flatpak remote-add --if-not-exists flathub https://dl.flathub.org/repo/flathub.flatpakrepo`.)

**Arch / Manjaro**
```bash
sudo pacman -S python python-pip ffmpeg flatpak
flatpak install flathub org.waywallen.waywallen
```

**openSUSE**
```bash
sudo zypper install python3 python3-pip ffmpeg flatpak
flatpak install flathub org.waywallen.waywallen
```

Alternativas a Flatpak: el AppImage de [Releases](https://github.com/waywallen/waywallen/releases) o compilar con su `BUILD.md`.

## 4. Instalar el proyecto

```bash
git clone https://github.com/Saldivar-ctrl/Selectores-Fondos.git
cd Selectores-Fondos
bash scripts/instalar_linux.sh        # --si para no preguntar
```

El script detecta la distribución, la sesión (Wayland/X11) y el escritorio, comprueba Python, crea `.venv` **dentro del proyecto**, instala las dependencias de Python y comprueba ffmpeg, busctl y waywallen. No usa `sudo` ni toca tu configuración.

A mano:
```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

## 5. Comprobar que waywallen funciona

```bash
.venv/bin/python src/main.py --verificar
.venv/bin/python src/main.py --catalog      # lista lo que waywallen tiene registrado
```

Para que waywallen conozca tus vídeos, añade tu carpeta a su biblioteca desde su propia interfaz. El selector solo aplica fondos que waywallen tiene registrados.

## 6. Rutas de los fondos

Por defecto `~/Vídeos/fondos` (se respeta `~/.config/user-dirs.dirs`). Para más carpetas: `F2` → *Carpetas de vídeos e imágenes*. Los fondos de Wallpaper Engine se buscan en las bibliotecas de Steam normales y en las de Flatpak (`~/.var/app/com.valvesoftware.Steam/...`); otros discos, en `F2` → *Bibliotecas de Steam extra*. Los enlaces simbólicos se resuelven (Bazzite: `/home` → `/var/home`).

## 7. Ejecutar

```bash
.venv/bin/python src/main.py circular
.venv/bin/python src/main.py hexagonal
```

## 8. Accesos directos y atajos de teclado

**Lanzador de menú** — crea `~/.local/share/applications/selector-fondos.desktop`:

```ini
[Desktop Entry]
Type=Application
Name=Selector de fondos (hexagonal)
Exec=/RUTA/Selectores-Fondos/.venv/bin/python /RUTA/Selectores-Fondos/src/main.py hexagonal
Path=/RUTA/Selectores-Fondos
Terminal=false
Categories=Utility;
```

Sustituye `/RUTA` por la ruta real (sin `~`; usa la ruta completa). Haz uno por selector.

**Atajo de teclado** — Python no puede registrar atajos globales en Wayland; se configura en el escritorio:

- **KDE Plasma:** Configuración del sistema → Atajos → *Añadir nueva → Comando u orden*; pega el `Exec` de arriba y asigna la combinación.
- **GNOME:** Configuración → Teclado → *Ver y personalizar atajos* → *Atajos personalizados* → **+**.
- Otros (Hyprland, Sway…): en su archivo de configuración, un `bind` que ejecute el mismo comando.

Para evitar conflictos, comprueba que la combinación no esté ya en uso; las que usan `Meta` suelen estar libres.

**Inicio automático (opcional):** copia el `.desktop` a `~/.config/autostart/`. Solo si quieres que el selector se abra al iniciar sesión.

## 9. Desinstalar

Borra la carpeta del proyecto, `~/.config/selectores-fondos/` (configuración) y `~/.cache/selectores-fondos/` (miniaturas). No se instaló nada fuera de la carpeta del proyecto.
