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


def configure_tk_environment() -> None:
    """Ayuda a Tcl/Tk a localizar sus bibliotecas en instalaciones de Python."""
    if sys.platform != "win32" or getattr(sys, "frozen", False):
        return

    tcl_root = Path(sys.base_prefix) / "tcl"
    libraries = (
        ("TCL_LIBRARY", tcl_root / "tcl8.6", "init.tcl"),
        ("TK_LIBRARY", tcl_root / "tk8.6", "tk.tcl"),
    )
    for variable, fallback, required_file in libraries:
        configured = Path(os.environ.get(variable, ""))
        if (configured / required_file).is_file():
            continue
        if (fallback / required_file).is_file():
            os.environ[variable] = str(fallback)
