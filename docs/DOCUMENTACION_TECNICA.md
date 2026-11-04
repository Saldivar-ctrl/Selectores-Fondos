# Documentación técnica

## Arquitectura

Los dos selectores comparten un mismo núcleo sin dependencias de Qt (se prueba sin pantalla). Las interfaces solo dibujan y mandan órdenes.

```text
src/
├── main.py                      lanzador (también entrada para PyInstaller)
└── selectores_fondos/
    ├── main.py                  opciones de terminal y arranque
    ├── core/                    lógica sin interfaz gráfica
    │   ├── configuracion.py     config.json por usuario (guardado atómico)
    │   ├── gestor_rutas.py      carpetas de vídeos y de Steam
    │   ├── gestor_fondos.py     lista de fondos, ocultos, aplicar, restaurar
    │   ├── autenticacion.py     contraseña (PBKDF2 con sal)
    │   └── diagnostico.py       --verificar
    ├── platforms/               una carpeta por sistema; no se mezclan
    │   ├── base.py              Backend, Estado, ErrorBackend
    │   ├── __init__.py          crear_backend(): elige según el sistema
    │   ├── linux/waywallen.py
    │   ├── linux/kde_smart_video.py   método antiguo, no usado por defecto
    │   ├── windows/wallpaper_engine.py
    │   └── windows/lively_wallpaper.py
    └── interfaces/              PySide6
        ├── selector_circular.py
        ├── selector_hexagonal.py
        ├── comun.py             miniaturas, modo oculto, restaurar
        ├── dialogo_contrasena.py     campo de contraseña
        └── dialogo_configuracion.py  ventana F2
```

**Por qué esta estructura.** La propuesta inicial ponía `src/core`, `src/interfaces` y `src/platforms` sueltos; se movieron a un paquete (`selectores_fondos`) para poder importar con rutas relativas sin choques de nombres. Se añadió `base.py` (contrato común de los backends) y `diagnostico.py`; la autenticación quedó separada de la interfaz.

## Archivos y funciones importantes

| Archivo | Qué hace |
|---|---|
| `core/configuracion.py` | `Configuracion.cargar()/guardar()`; un archivo ausente o dañado no rompe nada. Guarda con archivo temporal + `os.replace` y permisos 600 en Linux. `registrar_aplicado()` mantiene el historial (10). |
| `core/gestor_rutas.py` | `carpetas_videos()`, `bibliotecas_steam()` (lee `libraryfolders.vdf`, registro de Windows, rutas de Flatpak), `carpetas_wallpaper_engine()`. Compara con `realpath` para no duplicar por enlaces simbólicos. **Aquí se cambian las rutas por defecto.** |
| `core/gestor_fondos.py` | `GestorFondos.listar()` junta vídeos/imágenes, proyectos de Wallpaper Engine y carpetas de Lively; filtra ocultos y no registrados; `aplicar()` delega en el backend y guarda el historial; `restaurar_anterior()`. |
| `core/autenticacion.py` | `crear_verificador`, `verificar` (tiempo constante), `establecer` (guarda también el `.sello`), `estado()` (`nueva`, `ok` o `bloqueada`: falla cerrado si el verificador falta o cambió). |
| `platforms/base.py` | `Backend` con `comprobar()`, `filtrar_registrados()`, `aplicar()`. |
| `interfaces/comun.py` | `ThumbnailLoader` (ffmpeg en segundo plano, caché en `~/.cache/selectores-fondos`), `alternar_ocultos()`, `crear_contrasena()`, `abrir_configuracion()`. |

## Cómo se aplica un fondo

`Selector` → `GestorFondos.aplicar(fondo)` → `backend.aplicar(fondo)` → (Linux) D-Bus / (Windows) línea de comandos → `config.registrar_aplicado()` y `config.guardar()`. Los errores son `ErrorBackend` con un mensaje en español; la interfaz los muestra en una ventana y no se cierra.

Todas las llamadas externas usan listas de argumentos (nunca `shell=True`), así que espacios y caracteres especiales en rutas no se interpretan.

## waywallen (Linux)

1. `busctl --user get-property org.waywallen.waywallen.Daemon /org/waywallen/waywallen/Daemon org.waywallen.waywallen.Daemon1 WsPort` → puerto.
2. WebSocket `ws://127.0.0.1:<puerto>` con una petición protobuf mínima escrita a mano (sin generar código) → catálogo de fondos (`id`, nombre, tipo, recurso, tamaño).
3. `find_waywallen_id()` empareja el archivo local con el catálogo: ruta exacta → carpeta del proyecto → número de Steam → título → nombre y tamaño.
4. `busctl --user call … Daemon1 ApplyById s <id>`. Si no contesta en 15 s se interpreta como «cargando» (las escenas pesadas tardan).

**Limitación:** el README público de waywallen no documenta esta interfaz; sale del código que ya funcionaba en el equipo del autor. Si waywallen la cambia, solo hay que tocar `platforms/linux/waywallen.py`.

## Wallpaper Engine (Windows)

`wallpaper64.exe -control openWallpaper -file <project.json|archivo> [-monitor N]` ([documentación oficial](https://help.wallpaperengine.io/en/functionality/cli.html)). Si el programa no corre, se inicia y se espera. Detección del ejecutable: ruta configurada → bibliotecas de Steam. Solo se aceptan rutas `.exe`.

## Lively Wallpaper (Windows)

`livelycu setwp --file <ruta> [--monitor N]` ([documentación oficial](https://github.com/rocksdanister/lively/wiki/Command-Line-Controls)). Se busca primero `Livelycu.exe`; `Lively.exe` es segunda opción y que acepte los mismos argumentos no está confirmado. No entiende proyectos de Wallpaper Engine y solo muestra vídeos, imágenes y carpetas de Lively.

**Los dos sistemas de Windows nunca se mezclan:** `config.backend` elige uno; con `auto` se usa Wallpaper Engine si existe y, si no, Lively.

## Selector circular

`QGraphicsView` con tarjetas `QGraphicsPixmapItem` repartidas en un círculo: el ángulo de cada una es `2π·i/n + rotación`; la escala y la opacidad dependen de `cos(ángulo)` (la que está al frente es la mayor y la seleccionada). Todas las tarjetas se recortan a 900×506 con `KeepAspectRatioByExpanding` + recorte centrado, para que sean del mismo tamaño y rectangulares. Inercia con un `QTimer` de 16 ms. **Apariencia:** constantes `CARD_W/CARD_H`, `radius` y las escalas en `update_positions()`.

## Selector hexagonal

Panal de hexágonos «punta plana» (3 filas) en un marco invisible fijo que recorta (`ItemClipsChildrenToShape`); solo se mueven los hexágonos. 5 columnas completas más una casi invisible; la primera se desvanece al salir. El selector está en el lugar `CURSOR_SLOT` y no se mueve salvo en los extremos (la lista no da la vuelta). **Apariencia:** constantes al inicio del archivo (`HEX_*`, `SELECTED_SCALE`, `HOVER_SCALE`, `FULL_COLS`, `FADE_OPACITY`).

## Modo oculto

`Ctrl+Shift+H` → `comun.alternar_ocultos()`. Sin contraseña creada (se crea con F2): no hace nada. Estado `bloqueada`: no hace nada. Con contraseña: `DialogoContrasena` (solo un `QLineEdit` semitransparente en modo contraseña, sin botones) y `autenticacion.verificar()`. Los fondos ocultos se deciden en `GestorFondos.nombres_ocultos()` por nombre de carpeta Steam, título o archivo, desde `fondos_ocultos`, `privados/` y `carpetas_ocultas`.

**Apariencia del campo:** constante `ESTILO` en `interfaces/dialogo_contrasena.py`.

## Atajos

Dentro de la ventana, se gestionan en `keyPressEvent` de cada selector. Los atajos **globales** para abrir los selectores los define el escritorio (ver el [manual](MANUAL_USUARIO.md#atajos-para-abrir-el-selector)); Python no puede registrarlos en Wayland.

## Dependencias

`PySide6` (interfaz) y `websockets` (solo Linux). El resto es la biblioteca estándar. `ffmpeg` es opcional. Sin Docker ni Podman.
