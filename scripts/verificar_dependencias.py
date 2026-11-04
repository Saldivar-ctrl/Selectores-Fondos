#!/usr/bin/env python3
"""Comprueba dependencias y configuración. Solo lee; no instala ni cambia nada.

    python scripts/verificar_dependencias.py
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from selectores_fondos.main import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main(["--verificar"]))
