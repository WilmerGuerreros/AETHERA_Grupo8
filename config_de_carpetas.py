"""Rutas de las carpetas de memoria de Aethera."""

from dataclasses import dataclass
from pathlib import Path

from app_paths import application_data_directory


@dataclass(frozen=True)


class RutasMemoria:
    """Agrupa las carpetas donde se guarda la memoria del usuario."""

    historial: Path
    resumen: Path
    indice: Path
    adjuntos: Path

    def ensure(self) -> "RutasMemoria":
        """Crea las carpetas que falten y devuelve las mismas rutas."""
        for carpeta in (
            self.historial,
            self.resumen,
            self.indice,
            self.adjuntos,
        ):
            carpeta.mkdir(parents=True, exist_ok=True)
        return self


def rutas_memoria() -> RutasMemoria:
    """Calcula las rutas de memoria sin tocar el disco."""
    raiz = application_data_directory() / "memoria"
    return RutasMemoria(
        historial=raiz / "HISTORIAL",
        resumen=raiz / "RESUMEN",
        indice=raiz / "INDICE",
        adjuntos=raiz / "ARCHIVOS ADJUNTOS",
    )
