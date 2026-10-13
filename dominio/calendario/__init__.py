"""Lógica de lectura y edición de los calendarios académico y personal."""

from .escritura import crear_evento, eliminar_evento
from .lectura import buscar_eventos

__all__ = ["buscar_eventos", "crear_evento", "eliminar_evento"]
