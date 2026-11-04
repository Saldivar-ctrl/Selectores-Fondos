# Manual de usuario

Este manual explica cómo usar los selectores sin saber programar. Para instalar, ve primero a la guía de tu sistema:
[Windows](INSTALACION_WINDOWS.md) · [Linux](INSTALACION_LINUX.md).

## Qué son

Dos ventanas de pantalla completa con tus fondos animados (vídeos, imágenes y fondos de Wallpaper Engine). Eliges uno y se aplica como fondo de escritorio.

- **Circular:** carrusel de tarjetas rectangulares (16:9).
- **Hexagonal:** panal de hexágonos dentro de un marco fijo; solo se mueven los hexágonos.

Quién aplica el fondo depende del sistema:

| Sistema | Programa que aplica el fondo |
|---|---|
| Linux | [waywallen](https://github.com/waywallen/waywallen) |
| Windows | Wallpaper Engine **o** Lively Wallpaper (uno a la vez, nunca los dos) |

## Abrir un selector

```text
python src/main.py circular
python src/main.py hexagonal
python src/main.py            # abre el que tengas en la configuración
```

Dentro del entorno virtual del proyecto: `.venv/bin/python` (Linux) o `.venv\Scripts\python.exe` (Windows).

## Controles

| Acción | Circular | Hexagonal |
|---|---|---|
| Mover | Arrastrar, flechas, `A` / `D` | Arrastrar, flechas, `A` / `D`, rueda del ratón |
| Aplicar el fondo | Clic o `Enter` | Clic o `Enter` |
| Configuración | `F2` | `F2` |
| Modo oculto | `Ctrl+Shift+H` | `Ctrl+Shift+H` |
| Fondo anterior | `Ctrl+R` | `Ctrl+R` |
| Cerrar | `Esc` | `Esc` |

En el hexagonal, el hexágono bajo el puntero crece un poco; si no hay puntero encima, crece el del selector (el tercero de la fila central). La lista no da la vuelta: al llegar al principio o al final se detiene y el selector avanza por las últimas columnas.

## Dónde poner los vídeos

- Por defecto: la carpeta `fondos` dentro de tu carpeta de Vídeos (`~/Vídeos/fondos`, o `Videos\fondos` en Windows).
- Formatos: vídeo `.mp4 .mkv .webm .avi .mov`; imagen `.jpg .jpeg .png .webp`.
- Para usar otras carpetas: `F2` → *Carpetas de vídeos e imágenes* → **Añadir…** → **Guardar**. Puedes tener varias.
- Las miniaturas de los vídeos las genera `ffmpeg` (si no lo tienes, verás una tarjeta gris).

**Fondos de Wallpaper Engine.** Se buscan solos en las bibliotecas de Steam. Si Steam está en otro disco, añádelo en `F2` → *Bibliotecas de Steam extra*.

> En Linux solo se muestran los fondos de Wallpaper Engine que waywallen tiene registrados (así todos los que ves se pueden aplicar). Puedes cambiarlo en `F2`.

## Configuración (`F2`)

Ventana con: sistema de fondos, carpetas, bibliotecas de Steam, rutas de Wallpaper Engine y Lively, monitor, modo oculto y cambio de contraseña. Se guarda en un archivo de tu usuario (ver [CONFIGURACION.md](CONFIGURACION.md)); **nunca** hace falta editar el código.

Si cambias una carpeta de lugar: `F2`, quita la ruta antigua, añade la nueva, **Guardar**.

## Atajos para abrir el selector

Python **no puede** registrar un atajo global en todos los entornos (en Wayland las aplicaciones no pueden capturar teclas fuera de su ventana). Por eso el atajo se crea en tu escritorio, que sí puede lanzar un programa. Un atajo ejecuta un comando: usa la ruta completa del Python del proyecto.

**KDE Plasma** — Configuración del sistema → Atajos → *Añadir nueva → Comando u orden*. Comando:

```text
/ruta/al/proyecto/.venv/bin/python /ruta/al/proyecto/src/main.py hexagonal
```

Crea uno por selector y asígnales la combinación en la pestaña *Atajos*.

**GNOME** — Configuración → Teclado → *Ver y personalizar atajos* → *Atajos personalizados* → **+**. Nombre, comando (el mismo de arriba) y combinación.

**Windows** — Crea un acceso directo (clic derecho en el escritorio → Nuevo → Acceso directo) con destino:

```text
C:\ruta\al\proyecto\.venv\Scripts\pythonw.exe C:\ruta\al\proyecto\src\main.py hexagonal
```

Clic derecho → Propiedades → campo **Tecla de método abreviado**. Funciona solo con accesos directos del escritorio o del menú Inicio. `pythonw.exe` evita la ventana negra de consola.

**Evitar conflictos.** Antes de elegir una combinación, búscala en la configuración de atajos de tu escritorio; si ya está en uso, el sistema te avisa o la sustituye. Una buena opción es una combinación con `Meta` (tecla Windows) + letra poco usada, por ejemplo `Meta+Alt+F`.

Para cambiar un atajo, edítalo en el mismo lugar donde lo creaste. Los programas no guardan atajos globales propios.

## Modo oculto y contraseña

**Qué es.** Algunos fondos se marcan como privados y no aparecen en el selector. Con una combinación invisible y una contraseña se muestran; con la misma combinación se vuelven a ocultar.

**Cómo se marca un fondo como privado.** Cualquiera de estas formas (se pueden combinar):

1. `fondos_ocultos` en la configuración: número de carpeta de Steam, título o nombre de archivo. `python src/main.py --listar` muestra los números.
2. Una carpeta o archivo **vacío** con ese nombre dentro de `privados/` (junto a `config.json`). No hay que mover nada.
3. Una carpeta oculta del sistema (en Linux, un nombre que empieza con punto, como `~/Vídeos/.fondos_privados`), añadida a `carpetas_ocultas`.

**Cómo entrar.** Con el selector abierto, `Ctrl+Shift+H`:

- **Sin contraseña creada:** no hace nada; créala primero con `F2` (mínimo 4 caracteres).
- **Después:** escribe la contraseña y `Enter`. Si es incorrecta no pasa nada y no se avisa. `Esc` cancela.
- `Ctrl+Shift+H` otra vez vuelve a ocultar los privados (sin pedir contraseña).

El campo de contraseña es solo un rectángulo semitransparente con el texto en puntos; el borde se aclara cuando está seleccionado.

**Cambiar la contraseña.** `F2` → **Cambiar contraseña…**. Si ya hay una contraseña, primero hay que escribir la actual; si no es correcta, no se cambia. Así nadie puede cambiarla sin conocerla (salvo con acceso a tu terminal o a tus archivos: ver «Si la olvidas»).

**Dónde se guarda.** En `config.json`, como verificador: sal aleatoria de 16 bytes + hash PBKDF2-HMAC-SHA256 con 600 000 iteraciones. La contraseña nunca se guarda en texto. El repositorio no incluye ninguna contraseña. (Se usó PBKDF2 porque viene con Python; Argon2id obligaría a instalar otra dependencia.)

**Crear la contraseña.** La primera vez, `F2` → **Cambiar contraseña…** (la pide dos veces). Mientras no exista, `Ctrl+Shift+H` no abre nada.

**Borrarla o alterarla no la restablece.** Junto a `config.json` hay un archivo `.sello` con la huella de la contraseña. Si alguien borra las líneas de la contraseña en `config.json`, las cambia o rompe el archivo, el modo oculto queda **bloqueado**: no se abre y tampoco deja crear otra. No hay ningún comando para restablecerla.

**Si la olvidas.** No hay recuperación desde el programa. Solo con acceso a tus archivos: borrar `config.json` **y** `.sello` (carpeta de configuración, ver [CONFIGURACION.md](CONFIGURACION.md)) y crear una nueva. Eso mismo puede hacerlo cualquiera que tenga acceso a tu cuenta; un programa local no puede evitarlo. El modo oculto protege de miradas casuales. Para algo más fuerte, cifra el disco o guarda los fondos privados en otra cuenta de usuario.

**Desactivarlo por completo.** `F2` → desmarca *Habilitar el modo oculto*, o `python src/main.py --desactivar-modo-oculto` (`--activar-modo-oculto` lo reactiva). Desactivado, `Ctrl+Shift+H` no hace nada.

## Volver al fondo anterior

`Ctrl+R` dentro del selector, o desde la terminal `python src/main.py --restaurar`. Se recuerdan los últimos 10 fondos.

## Comandos útiles de terminal

| Comando | Para qué |
|---|---|
| `--verificar` | Revisa dependencias y dice qué falta. No cambia nada. |
| `--listar` | Muestra los fondos visibles. |
| `--restaurar` | Vuelve al fondo anterior. |
| `--backend waywallen\|wallpaper_engine\|lively` | Usa ese sistema solo en esa ejecución. |
| `--catalog` | (Linux) lo que waywallen tiene registrado. |

Si algo falla, mira [SOLUCION_DE_PROBLEMAS.md](SOLUCION_DE_PROBLEMAS.md).
