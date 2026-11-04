# Publicar en GitHub

## Antes de subir

1. `LICENSE` y los enlaces ya tienen tu nombre y tu usuario (Saldivar-ctrl); revísalos si quieres cambiarlos.
2. Comprueba que no vas a subir nada personal:

```bash
git status --ignored
grep -rIn "/home/\|Rigby\|@gmail" . --exclude-dir=.git --exclude-dir=originales_respaldo
```

El `.gitignore` ya excluye `.venv/`, cachés, `config.json` y la carpeta `privados/`. La carpeta `originales_respaldo/` contiene tus programas originales **con la huella SHA-256 de tu contraseña antigua y rutas de tu equipo**: el `.gitignore` ya la excluye, así que no se sube; no la quites de ahí.

3. Agrega capturas a `assets/images/` si quieres mostrarlas en el README.

## Licencia

Se incluye **MIT**: permisiva, permite uso, copia, modificación y venta con tal de conservar el aviso de copyright; sin garantía. Alternativa: **GPL-3.0** si quieres que las versiones derivadas también sean libres. PySide6 tiene su propia licencia (LGPL/GPL/comercial); revísala si distribuyes ejecutables.

## Comandos

```bash
cd Selectores-Fondos
git init -b main
git add .
git status                       # revisa qué se va a subir
git commit -m "Primera versión: selectores circular y hexagonal"
```

Crea el repositorio vacío en GitHub (botón **New**; sin README ni licencia) y vincúlalo:

```bash
git remote add origin https://github.com/Saldivar-ctrl/Selectores-Fondos.git
git push -u origin main
```

Con la CLI de GitHub (`gh`) también puedes hacerlo así: `gh repo create Selectores-Fondos --public --source=. --push`.

## Versiones y lanzamientos

La versión está en `src/selectores_fondos/__init__.py` (`__version__`) y los cambios en `CHANGELOG.md` (formato [Keep a Changelog](https://keepachangelog.com/es-ES/) y [versionado semántico](https://semver.org/lang/es/)).

```bash
# 1. sube la versión en __init__.py y anota el CHANGELOG
git add -A && git commit -m "Versión 1.0.0"
git tag -a v1.0.0 -m "Versión 1.0.0"
git push origin main --tags

# 2. crea el lanzamiento (release)
gh release create v1.0.0 --title "v1.0.0" --notes-file CHANGELOG.md
```

Sin `gh`: en GitHub → *Releases → Draft a new release* → elige la etiqueta `v1.0.0`.

## Después de publicar

- Pide a quien pruebe en Windows u otras distribuciones que reporte el resultado y actualiza `docs/PRUEBAS.md`.
- Si alguna vez subes por error una contraseña o ruta privada, cambiarla es lo primero; borrar el commit no basta porque el historial de Git la conserva.
