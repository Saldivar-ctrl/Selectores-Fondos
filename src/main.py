#!/usr/bin/env python3
"""Lanzador cómodo: python src/main.py [circular|hexagonal] [opciones].

Añade esta carpeta al camino de importación y llama a selectores_fondos.main.
(También sirve como entrada para PyInstaller.)
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from selectores_fondos.main import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
