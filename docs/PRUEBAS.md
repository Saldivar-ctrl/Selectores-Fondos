# Pruebas realizadas y pendientes

Entorno de las pruebas: Linux (contenedor en la nube), Python 3.13, **sin PySide6** (no se pudo instalar), sin waywallen, sin Wallpaper Engine, sin Lively, sin Windows.

## Verificado

| Qué | Cómo | Resultado |
|---|---|---|
| Lógica del núcleo (configuración, rutas, fondos, autenticación) | `python -m unittest discover -s tests -v` (60 pruebas) | Correcto |
| Contraseña: PBKDF2 con sal, verificación, contraseñas erróneas y datos dañados | pruebas automáticas | Correcto |
| waywallen: lectura del catálogo protobuf, emparejado por ruta/título/número/tamaño, llamada a `busctl` sin shell, tiempo de espera, errores | pruebas con un daemon simulado | Correcto |
| Wallpaper Engine y Lively: el comando exacto coincide con su documentación; sin shell; errores de proceso; no instalado; Lively rechaza proyectos de Wallpaper Engine | pruebas con procesos simulados | Correcto |
| Todos los archivos compilan | `python -m compileall` | Correcto |
| `scripts/instalar_linux.sh` | `bash -n` (sintaxis) | Correcto |
| Flujos de los selectores (aplicar, modo oculto con contraseña, F2, `Ctrl+R`, primera contraseña) | script de humo con PySide6 **simulado** | Correcto — no es la interfaz real |
| Tarjetas del circular del mismo tamaño y rectangulares | revisión del código (`CARD_W/CARD_H`, recorte centrado) | Correcto en el código; ver pendientes |

## Pendiente de verificar (no se afirma que funcione)

| Qué | Por qué |
|---|---|
| **Aspecto real de ambas interfaces** (circular, hexagonal, campo de contraseña semitransparente, efecto al enfocar) | No hay PySide6 ni pantalla aquí. Los diseños se conservaron del código que el autor ya usaba, pero el campo de contraseña nuevo y las tarjetas rectangulares **hay que verlos en tu equipo**. |
| Linux + waywallen reorganizado | La lógica viene del código que funcionaba en Bazzite + KDE Plasma; falta una prueba real completa del proyecto nuevo. |
| Otras distribuciones (Fedora, Ubuntu, Debian, Mint, Arch, Manjaro, openSUSE) | Sin probar; los comandos son los habituales de cada familia. |
| GNOME, Hyprland, Sway, COSMIC, X11 | Sin probar; X11 ni siquiera lo documenta waywallen. |
| Windows 10 y 11 con Wallpaper Engine | Comando de la documentación oficial; sin probar en Windows. |
| Windows 10 y 11 con Lively | Igual; la ruta de instalación habitual es una suposición; `Lively.exe` como alternativa a `livelycu.exe` no está confirmado. |
| `scripts/instalar_windows.ps1` | No se pudo ejecutar PowerShell aquí. |
| Ejecutable con PyInstaller | No probado. |
| Atajos de teclado en KDE, GNOME y Windows | Los pasos son los de la documentación de cada escritorio; no se probaron. |

## Cómo ayudar a verificar

Ejecuta `python src/main.py --verificar` y abre un *issue* con sistema, resultado y qué funcionó. Se irá actualizando esta tabla.
