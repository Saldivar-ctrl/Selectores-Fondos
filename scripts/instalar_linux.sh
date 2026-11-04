#!/usr/bin/env bash
# Instalador para Linux (Bazzite/Fedora, Ubuntu/Debian, Mint, Arch/Manjaro,
# openSUSE y derivadas).
#
# Qué hace:  detecta distribución y sesión, comprueba Python, crea un entorno
#            virtual DENTRO del proyecto (.venv) e instala las dependencias de
#            Python. Comprueba ffmpeg, busctl y waywallen.
# Qué NO hace: no usa sudo, no instala paquetes del sistema, no toca tu
#            configuración. Si falta algo del sistema, te dice el comando.
#
# Uso:  bash scripts/instalar_linux.sh [--si]     (--si = no preguntar)
set -u

SI=0
[ "${1:-}" = "--si" ] && SI=1

RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV="$RAIZ/.venv"

ok()    { printf '  [ OK ]   %s\n' "$*"; }
aviso() { printf '  [AVISO]  %s\n' "$*"; }
falta() { printf '  [FALTA]  %s\n' "$*"; PROBLEMAS=$((PROBLEMAS + 1)); }
PROBLEMAS=0

preguntar() {  # preguntar "texto" -> 0 si sí
  [ "$SI" = 1 ] && return 0
  read -r -p "$1 [s/N] " r
  case "$r" in s|S|si|SI|sí|y|Y) return 0 ;; *) return 1 ;; esac
}

echo "== Selectores de fondos: instalación para Linux =="

# --- Distribución --------------------------------------------------------
ID=""; ID_LIKE=""; NOMBRE="desconocida"
if [ -r /etc/os-release ]; then
  # shellcheck disable=SC1091
  . /etc/os-release
  ID="${ID:-}"; ID_LIKE="${ID_LIKE:-}"; NOMBRE="${PRETTY_NAME:-$ID}"
fi
FAMILIA="otra"
case " $ID $ID_LIKE " in
  *" fedora "*|*" rhel "*|*" bazzite "*) FAMILIA="fedora" ;;
  *" debian "*|*" ubuntu "*)             FAMILIA="debian" ;;
  *" arch "*)                            FAMILIA="arch" ;;
  *" suse "*|*" opensuse "*)             FAMILIA="suse" ;;
esac
INMUTABLE=0
[ -e /run/ostree-booted ] && INMUTABLE=1

echo "Distribución: $NOMBRE (familia: $FAMILIA)"
[ "$INMUTABLE" = 1 ] && echo "Sistema inmutable (rpm-ostree): no se instalan paquetes del sistema; se usa un entorno de usuario."
echo "Sesión: ${XDG_SESSION_TYPE:-desconocida} · Escritorio: ${XDG_CURRENT_DESKTOP:-desconocido}"
case "${XDG_SESSION_TYPE:-}" in
  x11) aviso "Sesión X11: la documentación de waywallen solo describe Wayland. Los selectores abren, pero waywallen podría no funcionar." ;;
esac

# --- Comandos de instalación sugeridos por familia (solo se muestran) ----
sugerencia() {  # sugerencia <paquete-logico>
  case "$FAMILIA:$1" in
    debian:python)  echo "sudo apt install python3 python3-venv python3-pip" ;;
    debian:ffmpeg)  echo "sudo apt install ffmpeg" ;;
    debian:flatpak) echo "sudo apt install flatpak" ;;
    fedora:python)  [ "$INMUTABLE" = 1 ] && echo "(Python viene en la imagen; revisa tu variante)" || echo "sudo dnf install python3 python3-pip" ;;
    fedora:ffmpeg)  [ "$INMUTABLE" = 1 ] && echo "(en Bazzite suele venir incluido; si no, usa distrobox o brew)" || echo "sudo dnf install ffmpeg  (requiere RPM Fusion)" ;;
    fedora:flatpak) echo "(Flatpak ya viene en Fedora/Bazzite)" ;;
    arch:python)    echo "sudo pacman -S python python-pip" ;;
    arch:ffmpeg)    echo "sudo pacman -S ffmpeg" ;;
    arch:flatpak)   echo "sudo pacman -S flatpak" ;;
    suse:python)    echo "sudo zypper install python3 python3-pip" ;;
    suse:ffmpeg)    echo "sudo zypper install ffmpeg  (puede requerir el repositorio Packman)" ;;
    suse:flatpak)   echo "sudo zypper install flatpak" ;;
    *)              echo "instálalo con el gestor de paquetes de tu distribución" ;;
  esac
}

# --- Python ---------------------------------------------------------------
PY=""
for c in python3 python; do
  if command -v "$c" >/dev/null 2>&1; then PY="$c"; break; fi
done

if [ -z "$PY" ]; then
  falta "Python 3 no está instalado. Instálalo con: $(sugerencia python)"
  exit 1
fi

if "$PY" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)'; then
  ok "Python $("$PY" -c 'import platform; print(platform.python_version())') ($PY)"
else
  falta "Se necesita Python 3.9 o superior (recomendado 3.12)."
  exit 1
fi

if ! "$PY" -c 'import venv, ensurepip' >/dev/null 2>&1; then
  falta "Falta el módulo venv/ensurepip. Instálalo con: $(sugerencia python)"
  exit 1
fi

# --- Entorno virtual -------------------------------------------------------
if [ -x "$VENV/bin/python" ]; then
  ok "Entorno virtual existente: $VENV (se reutiliza)"
else
  if preguntar "Crear el entorno virtual en $VENV?"; then
    "$PY" -m venv "$VENV" && ok "Entorno virtual creado" || { falta "No se pudo crear el entorno virtual"; exit 1; }
  else
    echo "Cancelado. No se cambió nada."; exit 0
  fi
fi

if preguntar "Instalar/actualizar dependencias de Python (requirements.txt)?"; then
  if "$VENV/bin/python" -m pip install -r "$RAIZ/requirements.txt"; then
    ok "Dependencias de Python instaladas"
  else
    falta "Falló pip. Revisa tu conexión y vuelve a intentarlo."
  fi
fi

# --- Dependencias del sistema (solo comprobar) ------------------------------
command -v ffmpeg >/dev/null 2>&1 \
  && ok "ffmpeg encontrado" \
  || aviso "ffmpeg no encontrado (miniaturas de vídeo): $(sugerencia ffmpeg)"

command -v busctl >/dev/null 2>&1 \
  && ok "busctl encontrado (systemd)" \
  || falta "busctl no encontrado: viene con systemd; sin él no se puede hablar con waywallen."

if command -v waywallen >/dev/null 2>&1; then
  ok "waywallen encontrado en el PATH"
elif command -v flatpak >/dev/null 2>&1 && flatpak info org.waywallen.waywallen >/dev/null 2>&1; then
  ok "waywallen instalado por Flatpak"
else
  falta "waywallen no detectado. Opciones (README oficial): Flatpak de Flathub o AppImage."
  if command -v flatpak >/dev/null 2>&1; then
    echo "         flatpak install flathub org.waywallen.waywallen"
  else
    echo "         Primero instala Flatpak: $(sugerencia flatpak)"
  fi
  echo "         Web: https://github.com/waywallen/waywallen"
fi

# --- Resultado --------------------------------------------------------------
echo
"$VENV/bin/python" "$RAIZ/scripts/verificar_dependencias.py" || true
echo
if [ "$PROBLEMAS" -eq 0 ]; then
  echo "Listo. Para abrir un selector:"
else
  echo "Hay $PROBLEMAS punto(s) por resolver (arriba). Después, para abrir un selector:"
fi
echo "  $VENV/bin/python $RAIZ/src/main.py circular"
echo "  $VENV/bin/python $RAIZ/src/main.py hexagonal"
