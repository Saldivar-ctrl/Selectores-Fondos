# Configuración

## Dónde está

| Sistema | Archivo |
|---|---|
| Linux | `$XDG_CONFIG_HOME/selectores-fondos/config.json` (normalmente `~/.config/selectores-fondos/config.json`) |
| Windows | `%APPDATA%\SelectoresFondos\config.json` |
| Otro | la ruta de la variable de entorno `SELECTORES_FONDOS_CONFIG` (tiene prioridad en todos los sistemas) |

La caché de miniaturas está en `~/.cache/selectores-fondos/miniaturas` (Linux) o `%LOCALAPPDATA%\SelectoresFondos\cache\miniaturas` (Windows). Se puede borrar sin problema.

El archivo **no existe hasta que guardes** algo. Si falta o está dañado, el programa usa los valores por defecto y avisa (no se rompe).

## Cómo editarla

Lo normal es la ventana de configuración (`F2` en cualquier selector). Editar el JSON a mano también vale (con los selectores cerrados). Los valores de tipo incorrecto se ignoran.

## Claves

| Clave | Tipo | Por defecto | Significado |
|---|---|---|---|
| `backend` | texto | `"auto"` | `auto`, `waywallen`, `wallpaper_engine` o `lively`. `auto`: waywallen en Linux; en Windows, Wallpaper Engine si está instalado, si no Lively. |
| `interfaz` | texto | `"circular"` | Selector que se abre sin indicar otro (`circular` o `hexagonal`). |
| `carpetas_videos` | lista | `[]` | Carpetas con vídeos e imágenes. Vacío = `<Vídeos>/fondos`. |
| `carpetas_steam` | lista | `[]` | Bibliotecas de Steam extra (donde Wallpaper Engine guarda sus fondos). Las normales se detectan solas. |
| `ruta_wallpaper_engine` | texto | `""` | Ruta de `wallpaper64.exe` (o `wallpaper32.exe`). Vacío = autodetección. |
| `ruta_lively` | texto | `""` | Ruta de `Lively.exe` o `livelycu.exe`. Vacío = autodetección. |
| `monitor` | texto | `""` | Número de monitor (0, 1, …). Vacío = el predeterminado. |
| `carpetas_ocultas` | lista | `[]` | Carpetas cuyo **contenido (por nombre)** marca fondos como privados. Siempre se usa además `privados/` junto a `config.json`. |
| `fondos_ocultos` | lista | `[]` | Números de carpeta de Steam, títulos o nombres de archivo privados. |
| `modo_oculto_habilitado` | booleano | `true` | `false` desactiva por completo `Ctrl+Shift+H`. |
| `autenticacion` | objeto | `{}` | Verificador de la contraseña (sal, hash, iteraciones). **No editar a mano.** |
| `ocultar_no_registrados` | booleano | `true` | (waywallen) muestra solo fondos de Wallpaper Engine registrados en waywallen, para que todos los visibles se puedan aplicar. |
| `ultimo_fondo`, `historial` | texto / lista | — | Los gestiona el programa (para `Ctrl+R`). |

Ejemplo:

```json
{
  "backend": "auto",
  "interfaz": "hexagonal",
  "carpetas_videos": ["~/Vídeos/fondos", "/mnt/disco/Mis fondos"],
  "carpetas_steam": ["/run/media/usuario/Juegos/SteamLibrary"],
  "carpetas_ocultas": ["~/Vídeos/.fondos_privados"],
  "fondos_ocultos": ["3753921460"]
}
```

Las rutas aceptan `~`, variables de entorno, espacios y acentos. En Windows, escribe las barras como `C:/Mis Vídeos` o duplica la barra invertida (`C:\\Mis Vídeos`) dentro del JSON.

## Dónde se guardan las rutas por defecto del código

Si quieres cambiar dónde busca por defecto: `src/selectores_fondos/core/gestor_rutas.py` (Vídeos, bibliotecas de Steam).

## Cuando cambias una carpeta de lugar

1. `F2` → quita la ruta antigua y añade la nueva → **Guardar**.
2. Si usas Steam en otro disco, añádelo en "Bibliotecas de Steam extra".
3. Si algo no aparece, `python src/main.py --verificar` dice qué carpeta no existe.

## Cómo ocultar fondos (modo oculto)

Tres formas, combinables:

1. **Lista:** `fondos_ocultos` con el número de carpeta de Steam (`python src/main.py --listar` lo muestra), el título o el nombre del archivo.
2. **Carpeta privada sin mover nada:** crea una carpeta o archivo **vacío** con ese nombre dentro de `privados/` (junto a `config.json`) o de una carpeta de `carpetas_ocultas`. Ejemplo: `mkdir ~/.config/selectores-fondos/privados/3753921460`.
3. **Carpeta oculta del sistema:** en Linux, un nombre que empieza con punto (`~/Vídeos/.fondos_privados`) no se ve en el gestor de archivos salvo con `Ctrl+H`. Añádela a `carpetas_ocultas`.

Ver el apartado de [modo oculto](MANUAL_USUARIO.md#modo-oculto-y-contraseña) del manual.
