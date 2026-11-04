# Solución de problemas

Primero ejecuta `python src/main.py --verificar`: dice qué falta sin cambiar nada.

| Síntoma | Causa probable | Qué hacer |
|---|---|---|
| `Falta PySide6` | Dependencias sin instalar, o usas el Python equivocado | Usa el Python del entorno virtual: `.venv/bin/python` (Linux) o `.venv\Scripts\python.exe` (Windows) y `-m pip install -r requirements.txt`. |
| El selector abre pero no hay fondos | Carpeta vacía o inexistente | `F2` → revisa *Carpetas de vídeos e imágenes*. `--listar` muestra lo que se ve. |
| Las tarjetas de vídeo salen grises | No hay `ffmpeg` | Instálalo (ver guía de tu sistema). |
| **Linux:** «waywallen no está listo» / no responde | waywallen no está en ejecución | Ábrelo (o inícialo con la sesión) y reintenta. |
| **Linux:** «Falta busctl» | Sin systemd | `busctl` viene con systemd; sin él no se puede controlar waywallen. |
| **Linux:** «Falta websockets» | Dependencia sin instalar | `.venv/bin/python -m pip install websockets` |
| **Linux:** «no está registrado en waywallen» | waywallen no conoce ese archivo | Añádelo a la biblioteca de waywallen. `--catalog` muestra lo registrado. |
| **Linux:** un fondo de Wallpaper Engine no aparece | No está registrado en waywallen (se oculta a propósito) | Regístralo, o desmarca *solo registrados* en `F2`. |
| **Linux:** escenas pesadas tardan | waywallen carga lentamente | El selector no lo toma por error: avisa «se está cargando». Espera unos segundos. |
| **Linux:** sesión X11 | waywallen solo documenta Wayland | Inicia sesión en Wayland si puedes. |
| **Windows:** «No se encontró Wallpaper Engine» | Ruta no detectada | `F2` → *Wallpaper Engine* → **Examinar…** → `wallpaper64.exe`. |
| **Windows:** Wallpaper Engine «no arrancó a tiempo» | Steam cerrado o arranque lento | Abre Wallpaper Engine a mano y reintenta. |
| **Windows:** «No se encontró Lively» | Ruta no detectada | `F2` → *Lively Wallpaper* → **Examinar…**. |
| **Windows:** Lively no abre un fondo de Wallpaper Engine | Lively no los entiende | Cambia el sistema a `wallpaper_engine`, o usa vídeos/imágenes. |
| `Ctrl+Shift+H` no hace nada | Modo oculto desactivado, o la contraseña es incorrecta (no avisa) | `F2` → *Habilitar el modo oculto*. |
| Olvidé la contraseña, o dice «datos alterados» | No hay restablecimiento por comando (a propósito) | Ver «Si la olvidas» en el [manual](MANUAL_USUARIO.md#modo-oculto-y-contraseña). |
| Moví una carpeta y desapareció | Ruta antigua guardada | `F2`: quita la antigua, añade la nueva. |
| «No se pudo leer … config.json» | Archivo dañado | Se usan valores por defecto. Corrige el JSON. (Si ya tenías contraseña, el modo oculto queda bloqueado mientras el archivo esté dañado o sin ella.) |
| La ventana no es transparente | Sin compositor activo | Activa el compositor del escritorio. |
| Un atajo de teclado no abre nada | Ruta mal escrita en el atajo | Usa rutas completas y prueba el comando en la terminal primero. |

## Pedir ayuda

Abre un *issue* en GitHub con: sistema y versión, Python (`python --version`), la salida de `--verificar` y el mensaje de error. **No pegues** tu `config.json` (contiene el verificador de la contraseña).
