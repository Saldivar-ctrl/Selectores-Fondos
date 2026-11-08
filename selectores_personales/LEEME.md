# Selectores con barra, favoritos y ocultar

Cinco estilos independientes (un solo archivo cada uno): `circular`, `hexagonal`, `cuadrado`, `tiras` y `paralelogramo`. Usan **waywallen** (Linux) y PySide6.

```bash
python selectores_personales/selector_fondo_circular.py
```

- Carpeta de fondos por defecto: `~/Vídeos/fondos` (cámbiala en `FOLDER`, al inicio del archivo).
- **Contraseña inicial: `cambiar`.** Es pública: cámbiala lo primero con `F2` (pide la actual). Se usa para `Ctrl+Shift+H` (mostrar fondos privados).
- Favoritos y fondos ocultos se guardan en `~/.config/wallpaper-selector-data.json`.

| Tecla | Acción |
|---|---|
| Flechas / `A` `D` / rueda (circular) | Moverse |
| `Enter` o clic | Aplicar el fondo |
| `F` | Favorito (★) |
| `Supr` | Ocultar el fondo señalado (`Ctrl+Z` deshace) |
| `Ctrl+Shift+H` | Mostrar/ocultar los fondos privados (pide contraseña) |
| `Ctrl+F` / `B` | Buscar / mostrar la barra superior |
| `Esc` | Limpiar filtros; si no hay, salir |
| `F2` | Cambiar la contraseña |

La barra superior ofrece Todos, ★ Favoritos, filtros por tipo (Imagen, Escena, Vídeo, Web), tira de colores y búsqueda.
