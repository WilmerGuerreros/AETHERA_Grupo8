"""Rutas de recursos y datos persistentes de Aethera."""

import os
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path


APPLICATION_ROOT = Path(
    getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent)
)


def resource_path(*parts: str) -> Path:
    """Devuelve la ruta de un recurso de solo lectura incluido con la aplicación."""
    return APPLICATION_ROOT.joinpath("data", "resources", *parts)


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
    """Devuelve la raíz de datos durante desarrollo o ejecución empaquetada."""
    if getattr(sys, "frozen", False):
        return user_data_directory()
    return APPLICATION_ROOT / "data"


def user_calendar_path() -> Path:
    """Devuelve la ruta del calendario personal editable."""
    return application_data_directory() / "calendario.ics"


def quizzes_directory() -> Path:
    """Devuelve la carpeta de quizzes del usuario."""
    return application_data_directory() / "quices"


@dataclass(frozen=True)
class MemoryPaths:
    """Agrupa las carpetas donde se guarda la memoria del usuario."""

    historial: Path
    resumen: Path
    indice: Path
    adjuntos: Path

    def ensure(self) -> "MemoryPaths":
        """Crea las carpetas persistentes que usa el servicio de memoria."""
        for carpeta in (
            self.historial,
            self.resumen,
            self.indice,
            self.adjuntos,
        ):
            carpeta.mkdir(parents=True, exist_ok=True)
        return self


def memory_paths() -> MemoryPaths:
    """Calcula las rutas de memoria sin crear carpetas."""
    raiz = application_data_directory() / "memoria"
    return MemoryPaths(
        historial=raiz / "HISTORIAL",
        resumen=raiz / "RESUMEN",
        indice=raiz / "INDICE",
        adjuntos=raiz / "ARCHIVOS ADJUNTOS",
    )


def _mover_contenido(origen: Path, destino: Path) -> None:
    """Mueve datos heredados sin sobrescribir los archivos existentes."""
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
        if elemento.is_dir() and objetivo.is_dir():
            _mover_contenido(elemento, objetivo)
        elif not objetivo.exists():
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
            (APPLICATION_ROOT / "datos", destino),
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
