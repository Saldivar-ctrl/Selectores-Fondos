# Instalación en Windows 10 y 11

> **Estado:** los comandos de Wallpaper Engine y Lively están tomados de su documentación oficial y probados con pruebas automáticas que simulan los programas. **No se han probado en un Windows real** (ver [PRUEBAS.md](PRUEBAS.md)). Si lo pruebas, reporta el resultado.

## 1. Qué necesitas

| Programa | Para qué | Dónde |
|---|---|---|
| Python 3.9 o superior (recomendado **3.12**) | Ejecutar los selectores | [python.org/downloads](https://www.python.org/downloads/) |
| Git (opcional) | Descargar con `git clone` | [git-scm.com](https://git-scm.com/) |
| **Wallpaper Engine** (Steam, de pago) **o** [Lively Wallpaper](https://github.com/rocksdanister/lively) (gratuito, código abierto) | Aplicar los fondos | Steam / Microsoft Store / GitHub |
| ffmpeg (opcional) | Miniaturas de vídeos | `winget install Gyan.FFmpeg` |

Elige **uno** de los dos sistemas de fondos. No instales ni uses los dos a la vez como fondo: se pisarían.

## 2. Instalar Python

1. Descarga el instalador de 64 bits desde python.org.
2. Marca **Add python.exe to PATH** y pulsa *Install Now*.
3. Comprueba en PowerShell:

```powershell
python --version
```

(Si no responde, prueba `py --version`; el instalador del proyecto detecta ambos.)

## 3. Descargar el proyecto

Con Git:

```powershell
git clone https://github.com/Saldivar-ctrl/Selectores-Fondos.git
cd Selectores-Fondos
```

Sin Git: en GitHub, *Code → Download ZIP*, descomprime y abre PowerShell en esa carpeta.

## 4. Instalar dependencias

Automático (no necesita administrador ni cambia la configuración del sistema):

```powershell
powershell -ExecutionPolicy Bypass -File scripts\instalar_windows.ps1
```

La política `Bypass` vale solo para esa ejecución. El script comprueba Python, crea `.venv`, instala `requirements.txt` y revisa Wallpaper Engine y Lively.

A mano:

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## 5. Ejecutar

```powershell
.venv\Scripts\python.exe src\main.py circular
.venv\Scripts\python.exe src\main.py hexagonal
.venv\Scripts\python.exe src\main.py --verificar
```

## 6. Configurar Wallpaper Engine

1. Instala Wallpaper Engine desde Steam y ábrelo al menos una vez.
2. El programa busca `wallpaper64.exe` en las bibliotecas de Steam (lee `libraryfolders.vdf`), así que normalmente no hay que hacer nada.
3. Si no lo encuentra: `F2` → *Wallpaper Engine* → **Examinar…** → elige `wallpaper64.exe` (en `…\steamapps\common\wallpaper_engine\`). Solo se aceptan archivos `.exe`.
4. Tus fondos de Wallpaper Engine aparecen solos. Si Steam está en otro disco, añádelo en *Bibliotecas de Steam extra*.

Cómo aplica el fondo (comando oficial, [documentación](https://help.wallpaperengine.io/en/functionality/cli.html)):

```text
wallpaper64.exe -control openWallpaper -file "<project.json o archivo>" [-monitor N]
```

Si Wallpaper Engine no está abierto, el selector lo inicia y espera. Si falla, muestra el mensaje en una ventana.

## 7. Configurar Lively Wallpaper

1. Instala Lively (Microsoft Store o instalador de GitHub) y ábrelo una vez.
2. El selector busca `Livelycu.exe` / `Lively.exe` en las rutas habituales. Si no lo encuentra: `F2` → *Lively Wallpaper* → **Examinar…**.
3. `F2` → *Sistema de fondos* → **lively** (o déjalo en `auto`: usa Wallpaper Engine si está instalado, si no Lively).

Comando oficial ([documentación](https://github.com/rocksdanister/lively/wiki/Command-Line-Controls)):

```text
livelycu setwp --file "<ruta>" [--monitor N]
```

Lively solo entiende vídeos e imágenes de tus carpetas; **no** abre los fondos de Wallpaper Engine (escenas/web). El selector lo avisa en lugar de fallar en silencio.

> Versión de la Microsoft Store: la biblioteca de Lively vive bajo la carpeta del paquete (`LocalCache`); si algo no se encuentra, indica la ruta a mano en `F2`.

## 8. Rutas de los vídeos

`F2` → *Carpetas de vídeos e imágenes* → **Añadir…**. Por defecto: `C:\Users\<tu usuario de Windows>\Videos\fondos`. Las rutas con espacios y acentos están soportadas.

## 9. Accesos directos

- **Escritorio / Inicio:** Nuevo → Acceso directo. Destino:
  `C:\ruta\Selectores-Fondos\.venv\Scripts\pythonw.exe C:\ruta\Selectores-Fondos\src\main.py hexagonal`
  Iniciar en: `C:\ruta\Selectores-Fondos`.
- **Atajo de teclado:** Propiedades del acceso directo → *Tecla de método abreviado*.
- **Al iniciar sesión (opcional):** `Win+R` → `shell:startup` → copia ahí el acceso directo. Solo si de verdad quieres que se abra solo.

## 10. Generar un ejecutable (opcional, sin probar)

```powershell
.venv\Scripts\python.exe -m pip install pyinstaller
.venv\Scripts\pyinstaller.exe --noconfirm --windowed --name SelectoresFondos --paths src src\main.py
```

Resultado en `dist\SelectoresFondos\`. No está probado en este proyecto; los ejecutables de PyInstaller a veces los marca el antivirus como sospechosos. Alternativa más segura: usar los accesos directos de arriba. Si distribuyes el ejecutable, revisa la licencia de PySide6 (LGPL).
