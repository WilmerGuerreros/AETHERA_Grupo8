"""Lectura y escritura del calendario personal."""

import os
import tempfile
from pathlib import Path

from data.paths import user_calendar_path


def leer_calendario(ruta: Path) -> str:
    """Lee contenido ICS desde la ruta indicada."""
    return ruta.read_text(encoding="utf-8")


def leer_calendario_personal() -> str:
    """Lee el contenido ICS del calendario personal."""
    return leer_calendario(user_calendar_path())


def guardar_calendario_personal(contenido: str) -> None:
    """Guarda el contenido ICS reemplazando el archivo de forma atómica."""
    ruta = user_calendar_path()
    ruta.parent.mkdir(parents=True, exist_ok=True)
    temporal = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="",
            dir=ruta.parent,
            prefix=f".{ruta.name}.",
            suffix=".tmp",
            delete=False,
        ) as archivo:
            temporal = archivo.name
            archivo.write(contenido)
        os.replace(temporal, ruta)
    finally:
        if temporal and os.path.exists(temporal):
            os.unlink(temporal)
