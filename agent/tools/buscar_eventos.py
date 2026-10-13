"""Herramienta del agente para consultar los calendarios."""

from core.calendar import buscar_eventos as _buscar_eventos


def buscar_eventos(
    tipo: str,
    fecha_inicio: str = "1900-01-01",
    fecha_fin: str = "2100-01-01",
    origen: str = "ambos",
) -> list[dict]:
    """
Consulta eventos académicos, personales o de ambos calendarios en un rango inclusivo.

Args:
    tipo: Categoría exacta o 'any' para todas.
    fecha_inicio: Fecha inicial en formato 'YYYY-MM-DD'.
    fecha_fin: Fecha final en formato 'YYYY-MM-DD'.
    origen: 'academico', 'personal' o 'ambos'. Por defecto busca en ambos.

Returns:
    Lista de eventos etiquetados con su origen, o [{'error': 'motivo'}].
    """
    return _buscar_eventos(
        tipo,
        fecha_inicio=fecha_inicio,
        fecha_fin=fecha_fin,
        origen=origen,
    )
