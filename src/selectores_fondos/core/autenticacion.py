"""Contraseña del modo oculto.

- Nunca se guarda la contraseña: solo un verificador {sal, hash, iteraciones}.
- Derivación: PBKDF2-HMAC-SHA256 (hashlib, biblioteca estándar) con sal
  aleatoria de 16 bytes. Se eligió PBKDF2 porque no requiere dependencias
  externas; Argon2id sería preferible pero obliga a instalar un paquete extra.
- La comparación es en tiempo constante (hmac.compare_digest).
- El repositorio NO trae ninguna contraseña: se crea la primera vez que se
  activa el modo oculto (o desde la ventana de configuración, tecla F2).

Resistencia a borrados: junto a config.json hay un «sello» (.sello) con la
huella del verificador. Si el verificador desaparece o cambia pero el sello
sigue ahí, el modo oculto se BLOQUEA y no deja crear otra contraseña (falla
cerrado). Borrar unas líneas de config.json no abre nada.

Límite honesto: quien pueda borrar los DOS archivos (config.json y .sello)
vuelve al estado «sin contraseña». Un programa local no puede impedirlo: para
eso hace falta cifrar o mover los fondos privados (cifrado de disco, otra
cuenta de usuario). No existe comando para restablecer la contraseña.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import os
from pathlib import Path

ALGORITMO = "pbkdf2_sha256"
ITERACIONES = 600_000  # recomendación OWASP vigente para PBKDF2-HMAC-SHA256
LARGO_MINIMO = 4


def _derivar(contrasena: str, sal: bytes, iteraciones: int) -> bytes:
    return hashlib.pbkdf2_hmac(
        "sha256", contrasena.encode("utf-8"), sal, iteraciones
    )


def crear_verificador(contrasena: str, iteraciones: int = ITERACIONES) -> dict:
    if len(contrasena) < LARGO_MINIMO:
        raise ValueError(
            f"La contraseña debe tener al menos {LARGO_MINIMO} caracteres."
        )

    sal = os.urandom(16)

    return {
        "algoritmo": ALGORITMO,
        "iteraciones": iteraciones,
        "sal": base64.b64encode(sal).decode("ascii"),
        "hash": base64.b64encode(
            _derivar(contrasena, sal, iteraciones)
        ).decode("ascii"),
    }


def verificar(contrasena: str, datos: dict) -> bool:
    """True si la contraseña coincide. Datos ausentes o dañados = False."""
    try:
        if datos.get("algoritmo") != ALGORITMO:
            return False

        sal = base64.b64decode(datos["sal"])
        esperado = base64.b64decode(datos["hash"])
        iteraciones = int(datos["iteraciones"])

        if iteraciones < 1:
            return False

    except (KeyError, ValueError, TypeError, AttributeError):
        return False

    return hmac.compare_digest(
        _derivar(contrasena, sal, iteraciones), esperado
    )


def _bien_formado(datos) -> bool:
    try:
        return (datos.get("algoritmo") == ALGORITMO
                and bool(datos["sal"]) and bool(datos["hash"])
                and int(datos["iteraciones"]) >= 1)
    except (KeyError, ValueError, TypeError, AttributeError):
        return False


def _sello(config) -> Path:
    return Path(config.archivo).parent / ".sello"


def _huella(datos) -> str:
    return hashlib.sha256(
        (str(datos.get("sal")) + str(datos.get("hash"))).encode("utf-8")
    ).hexdigest()


def _escribir_sello(config):
    ruta = _sello(config)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(_huella(config.autenticacion), encoding="ascii")

    if os.name != "nt":
        os.chmod(ruta, 0o600)


def estado(config) -> str:
    """'nueva' (nunca hubo contraseña), 'ok' o 'bloqueada' (faltan o fueron
    alterados los datos de la contraseña: no se permite nada)."""
    try:
        sello = _sello(config).read_text(encoding="ascii").strip()
    except OSError:
        sello = ""

    if _bien_formado(config.autenticacion):
        if not sello:
            try:
                _escribir_sello(config)  # primera vez con sello
            except OSError:
                pass
            return "ok"

        return "ok" if sello == _huella(config.autenticacion) else "bloqueada"

    return "bloqueada" if sello else "nueva"


def hay_contrasena(config) -> bool:
    return bool(config.autenticacion.get("hash"))


def establecer(config, nueva: str):
    """Guarda un verificador nuevo y su sello (llamar a config.guardar()).
    Quien llama debe haber comprobado antes la contraseña actual."""
    config.autenticacion = crear_verificador(nueva)
    _escribir_sello(config)
