"""Herramienta del agente para consultar los calendarios."""

from core.calendar import buscar_eventos as _buscar_eventos


def buscar_eventos(
    tipo: str = "any",
    fecha_inicio: str = "1900-01-01",
    fecha_fin: str = "2100-01-01",
    origen: str = "",
) -> list[dict]:
    """
Consulta eventos académicos, personales o de ambos calendarios en un rango inclusivo.

Args:
    tipo: Categoría exacta o 'any' para todas. El catálogo de categorías
        válidas lo administra Data; si la categoría no existe, la herramienta
        devuelve un error que enumera las disponibles.
    fecha_inicio: Fecha inicial en formato 'YYYY-MM-DD'.
    fecha_fin: Fecha final en formato 'YYYY-MM-DD'.
    origen: Código del calendario a consultar, o vacío para consultarlos todos.
        Un origen inexistente devuelve un error con las opciones válidas.

Returns:
    Lista de eventos etiquetados con su origen, o [{'error': 'motivo'}].
    """
    return _buscar_eventos(
        tipo,
        fecha_inicio=fecha_inicio,
        fecha_fin=fecha_fin,
        origen=origen or None,
    )
