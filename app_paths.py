"""Rutas de recursos de solo lectura y datos de usuario de Aethera."""

import os
import sys
from pathlib import Path


APPLICATION_ROOT = Path(
    getattr(sys, "_MEIPASS", Path(__file__).resolve().parent)
)


def resource_path(*parts: str) -> Path:
    """Devuelve la ruta de un recurso incluido junto a la aplicación."""
    return APPLICATION_ROOT.joinpath(*parts)


def user_data_directory() -> Path:
    """Devuelve una carpeta escribible para los datos persistentes del usuario."""
    if sys.platform == "win32":
        base = Path(
            os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local")
        )
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    return base / "Aethera"
