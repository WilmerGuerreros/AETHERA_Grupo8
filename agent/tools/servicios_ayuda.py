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
        categoria: Uno de 'academic_pressure', 'social_support',
            'career_concern', 'sleep_and_routine' o 'service_navigation'.
        distrito: Identificador opcional: 'DIST_GAIA', 'DIST_HORIZON',
            'DIST_NEBULA', 'DIST_QUANTUM' o 'DIST_VECTOR'. Si se omite,
            se devuelven los servicios de todos los distritos.

    Returns:
        Un diccionario con la categoría y los servicios relacionados.
        Cada servicio incluye ubicación, horario, canales,
        elegibilidad e información requerida para derivar.
    """
    return _buscar_servicios_ayuda(categoria, distrito)
