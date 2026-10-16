"""Rutas de recursos y datos persistentes de Aethera."""

import os
import sys
from dataclasses import dataclass
from pathlib import Path


APPLICATION_ROOT = Path(
    getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent)
)


def emoji_font_candidates() -> list[Path]:
    """Lista las rutas posibles de una fuente de emoji a color por plataforma."""
    if sys.platform == "win32":
        windows_directory = Path(os.environ.get("WINDIR", r"C:\Windows"))
        return [windows_directory / "Fonts" / "seguiemj.ttf"]
    if sys.platform == "darwin":
        return [
            Path("/System/Library/Fonts/Apple Color Emoji.ttc"),
            Path("/Library/Fonts/Apple Color Emoji.ttc"),
        ]
    candidates = [
        Path("/usr/share/fonts/noto/NotoColorEmoji.ttf"),
        Path("/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf"),
        Path("/usr/share/fonts/google-noto-emoji/NotoColorEmoji.ttf"),
        Path("/usr/local/share/fonts/NotoColorEmoji.ttf"),
        Path.home() / ".local" / "share" / "fonts" / "NotoColorEmoji.ttf",
        Path.home() / ".fonts" / "NotoColorEmoji.ttf",
    ]
    search_roots = (
        Path("/usr/share/fonts"),
        Path("/usr/local/share/fonts"),
        Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
        / "fonts",
    )
    for root in search_roots:
        if root.is_dir():
            candidates.extend(sorted(root.glob("**/NotoColorEmoji.ttf")))
    return candidates


def emoji_font_path() -> Path | None:
    """Devuelve la ruta de la fuente de emoji a color instalada, o ``None``."""
    for candidate in emoji_font_candidates():
        if candidate.is_file():
            return candidate
    return None


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


def chat_archives_directory() -> Path:
    """Devuelve la raíz de los archivos independientes de cada chat."""
    return application_data_directory() / "CHATS DE AETHERA AI"


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


def memory_paths(raiz: Path | None = None) -> MemoryPaths:
    """Calcula las rutas de memoria sin crear carpetas.

    La raíz solo se indica para inyectar una ubicación alternativa en pruebas.
    """
    raiz = Path(raiz) if raiz is not None else application_data_directory() / "memoria"
    return MemoryPaths(
        historial=raiz / "MEMORIA BRUTA",
        resumen=raiz / "RESUMEN",
        indice=raiz / "INDICE",
        adjuntos=raiz / "ARCHIVOS ADJUNTOS",
    )
