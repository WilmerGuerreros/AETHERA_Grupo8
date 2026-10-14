"""Herramienta del agente para buscar servicios de apoyo."""

from typing import Any

from core.services import (
    buscar_servicios_ayuda as _buscar_servicios_ayuda,
)


def buscar_servicios_ayuda(
    categoria: str, distrito: str | None = None
) -> dict[str, Any]:
    """
    Busca los servicios asociados a un motivo de orientación y sus datos de derivación.

    Args:
        categoria: Código del motivo de orientación. El catálogo de categorías
            válidas lo administra Data; si el código no existe, la herramienta
            devuelve un error que enumera las categorías disponibles.
        distrito: Identificador opcional del distrito. Si se omite, se
            devuelven los servicios de todos los distritos. Un distrito
            inexistente también devuelve un error con las opciones válidas.

    Returns:
        Un diccionario con la categoría y los servicios relacionados.
        Cada servicio incluye ubicación, horario, canales,
        elegibilidad e información requerida para derivar.
    """
    return _buscar_servicios_ayuda(categoria, distrito)
