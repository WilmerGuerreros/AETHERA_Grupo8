"""Rutas de recursos de solo lectura y datos de usuario de Aethera."""

import os
import shutil
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


def application_data_directory() -> Path:
    """Raíz única de los datos escribibles (memoria, calendario y quices).

    Durante el desarrollo vive en la carpeta ``datos/`` del proyecto; en el
    ejecutable empaquetado usa la carpeta de datos del sistema operativo.
    """
    if getattr(sys, "frozen", False):
        return user_data_directory()
    return APPLICATION_ROOT / "datos"


def user_calendar_path() -> Path:
    """Devuelve el calendario personal editable de la aplicación."""
    return application_data_directory() / "calendario.ics"


def quizzes_directory() -> Path:
    """Devuelve la carpeta donde se guardan los quices del usuario."""
    return application_data_directory() / "quices"


def _mover_contenido(origen: Path, destino: Path) -> None:
    """Mueve ``origen`` a ``destino`` sin sobrescribir lo que ya exista."""
    if not origen.exists():
        return
    if origen.is_file():
        if not destino.exists():
            destino.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(origen), str(destino))
        return
    destino.mkdir(parents=True, exist_ok=True)
    for elemento in origen.iterdir():
        objetivo = destino / elemento.name
        if not objetivo.exists():
            shutil.move(str(elemento), str(objetivo))
    if not any(origen.iterdir()):
        origen.rmdir()


def migrar_datos_heredados() -> None:
    """Reúne en la raíz única los datos guardados por versiones anteriores."""
    destino = application_data_directory()
    if getattr(sys, "frozen", False):
        raiz = user_data_directory()
        origenes = (
            (raiz / "CHATS DE AETHERA AI" / "MEMORIA", destino / "memoria"),
            (
                raiz / "memoria" / "usuario" / "calendario.ics",
                destino / "calendario.ics",
            ),
        )
    else:
        origenes = (
            (
                APPLICATION_ROOT / "CHATS DE AETHERA AI" / "MEMORIA",
                destino / "memoria",
            ),
            (
                APPLICATION_ROOT / "memoria" / "usuario" / "calendario.ics",
                destino / "calendario.ics",
            ),
            (
                APPLICATION_ROOT / "memoria" / "usuario" / "quices",
                destino / "quices",
            ),
            (user_data_directory() / "quices", destino / "quices"),
        )
    for origen, destino_item in origenes:
        _mover_contenido(origen, destino_item)


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
