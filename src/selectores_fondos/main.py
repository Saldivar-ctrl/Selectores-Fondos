"""Punto de entrada: elige el selector y atiende las opciones de terminal.

    python src/main.py                    abre el selector configurado
    python src/main.py circular           abre el selector circular
    python src/main.py hexagonal          abre el selector hexagonal
    python src/main.py --verificar        revisa dependencias (no cambia nada)
    python src/main.py --listar           muestra los fondos que se ven
    python src/main.py --restaurar        vuelve al fondo anterior
    python src/main.py --catalog          (Linux) lo que waywallen tiene registrado
"""

from __future__ import annotations

import argparse
import sys

from . import __version__
from .core import autenticacion, diagnostico
from .core.configuracion import BACKENDS_VALIDOS, Configuracion
from .core.gestor_fondos import GestorFondos
from .platforms import ErrorBackend


def crear_parser():
    p = argparse.ArgumentParser(
        prog="selectores-fondos",
        description="Selectores de fondos animados (circular y hexagonal).",
    )
    p.add_argument("interfaz", nargs="?", choices=("circular", "hexagonal"),
                   help="selector a abrir (por defecto el de la configuración)")
    p.add_argument("--backend", choices=BACKENDS_VALIDOS,
                   help="usa este sistema solo en esta ejecución")
    p.add_argument("--verificar", action="store_true",
                   help="comprueba dependencias y sale")
    p.add_argument("--listar", action="store_true",
                   help="lista los fondos visibles y sale")
    p.add_argument("--restaurar", action="store_true",
                   help="vuelve a aplicar el fondo anterior y sale")
    p.add_argument("--catalog", action="store_true",
                   help="(Linux) muestra el catálogo de waywallen y sale")
    p.add_argument("--activar-modo-oculto", action="store_true")
    p.add_argument("--desactivar-modo-oculto", action="store_true")
    p.add_argument("--version", action="version", version=__version__)
    return p


def _confirmar(pregunta: str) -> bool:
    try:
        return input(pregunta + " [s/N] ").strip().lower() in ("s", "si", "sí", "y", "yes")
    except EOFError:
        return False


def main(argv=None) -> int:
    args = crear_parser().parse_args(argv)

    config = Configuracion.cargar()

    if config.aviso:
        print(config.aviso, file=sys.stderr)

    if args.backend:
        config.backend = args.backend  # solo en memoria

    gestor = GestorFondos(config)

    try:
        if args.verificar:
            resultado = diagnostico.ejecutar(config)
            marcas = {"ok": "[ OK ]", "aviso": "[AVISO]", "error": "[ERROR]"}

            for nivel, texto in resultado:
                print(marcas[nivel], texto)

            return 1 if any(n == "error" for n, _ in resultado) else 0

        if args.activar_modo_oculto or args.desactivar_modo_oculto:
            config.modo_oculto_habilitado = bool(args.activar_modo_oculto)
            config.guardar()
            print("Modo oculto " + ("activado" if config.modo_oculto_habilitado else "desactivado"))
            return 0

        if args.catalog:
            from .platforms.linux.waywallen import waywallen_catalog

            for entrada in waywallen_catalog():
                print(entrada["id"], entrada["type"], entrada["size"], entrada["resource"])
            return 0

        if args.listar:
            for fondo in gestor.listar(mostrar_ocultos=False):
                print(fondo.tipo, "|", fondo.id or "-", "|", fondo.title, "|", fondo.path)
            return 0

        if args.restaurar:
            print(gestor.restaurar_anterior())
            return 0

    except ErrorBackend as error:
        print(f"Error: {error}", file=sys.stderr)
        return 2

    return _abrir_interfaz(args.interfaz or config.interfaz, gestor)


def _abrir_interfaz(nombre, gestor) -> int:
    try:
        from PySide6 import QtCore  # noqa: F401
    except ImportError:
        print(
            "Falta PySide6. Instálalo con:\n"
            "  python -m pip install -r requirements.txt",
            file=sys.stderr,
        )
        return 3

    # Avisa pronto si el sistema no está listo, pero deja abrir el selector
    # (se puede arreglar desde la configuración, tecla F2)
    try:
        estado = gestor.backend.comprobar()

        if not estado.ok:
            print("AVISO:", estado.mensaje, file=sys.stderr)
            for detalle in estado.detalles:
                print("  ", detalle, file=sys.stderr)
    except ErrorBackend as error:
        print(f"AVISO: {error}", file=sys.stderr)

    if nombre == "hexagonal":
        from .interfaces.selector_hexagonal import ejecutar
    else:
        from .interfaces.selector_circular import ejecutar

    return ejecutar(gestor)


if __name__ == "__main__":
    sys.exit(main())
