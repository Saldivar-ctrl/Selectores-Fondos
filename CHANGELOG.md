# Cambios

Formato basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/); versiones según [SemVer](https://semver.org/lang/es/).

## [Sin publicar]

### Cambiado
- La contraseña del modo oculto falla cerrado: si sus datos se borran o alteran queda bloqueado en lugar de restablecerse. Se creó el archivo `.sello`; se quitó `--restablecer-contrasena`.
- La primera contraseña se crea con `F2`; `Ctrl+Shift+H` ya no la crea.

## [1.0.0] — pendiente de fecha de publicación

### Añadido
- Proyecto multiplataforma: Linux (waywallen) y Windows 10/11 (Wallpaper Engine o Lively Wallpaper).
- Núcleo compartido sin Qt (`core/`) y un backend por plataforma (`platforms/`).
- Configuración en JSON fuera del código, editable desde la interfaz (`F2`).
- Contraseña del modo oculto con PBKDF2-HMAC-SHA256 y sal; se crea la primera vez (sin contraseña por defecto) y se cambia desde la interfaz.
- Campo de contraseña minimalista (rectángulo semitransparente, puntos).
- Fondo anterior (`Ctrl+R`, `--restaurar`), `--verificar`, `--listar`.
- Scripts de instalación para Linux y Windows, manual, documentación técnica y pruebas.

### Cambiado
- Los selectores originales (`selector_fondo_circular.py`, `selector_fondo_hexagonal.py`) pasan a `interfaces/`; su diseño y comportamiento visual se conservan.
- Las miniaturas de vídeo se guardan en la caché del usuario con nombre único por ruta (antes colisionaban vídeos con el mismo nombre en carpetas distintas).
- El historial del último fondo pasa de `~/.config/wallpaper-selector.json` a `config.json`.

### Conservado
- `set_video_wallpaper` (plugin de vídeo de KDE) se conserva en `platforms/linux/kde_smart_video.py`; no se usaba en los originales y sigue sin conectarse a nada.

### Eliminado
- La contraseña predeterminada y su huella SHA-256 sin sal, y los datos personales (rutas y números de fondos privados) del código.
