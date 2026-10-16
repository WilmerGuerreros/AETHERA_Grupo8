"""Compatibilidad para lectores antiguos; la configuración vive en Data."""

from data.settings import (
    MAX_MENSAJES_POR_SECCION,
    MODELO,
    MODELO_RESUMEN,
    OPCIONES_LLM,
)

__all__ = [
    "MAX_MENSAJES_POR_SECCION",
    "MODELO",
    "MODELO_RESUMEN",
    "OPCIONES_LLM",
]
