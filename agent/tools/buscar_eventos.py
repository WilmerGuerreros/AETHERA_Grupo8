"""Herramienta del agente para consultar los calendarios."""

from core.calendar import (
    buscar_eventos as _buscar_eventos,
    categorias_disponibles,
    origenes_disponibles,
)

_categorias = ", ".join(sorted(categorias_disponibles()))
_origenes = ", ".join(sorted(origenes_disponibles()))


_DESCRIPCION = """
Consulta eventos académicos, personales o de ambos calendarios en un rango inclusivo.

Args:
    tipo: Categoría exacta o 'any' para todas. Categorías válidas: {categorias}.
        Si la categoría no existe, la herramienta devuelve un error con las opciones válidas.
    fecha_inicio: Fecha inicial en formato 'YYYY-MM-DD'.
    fecha_fin: Fecha final en formato 'YYYY-MM-DD'.
    origen: Código del calendario a consultar. Orígenes válidos: {origenes}.
        Déjalo vacío para consultar todos; un origen inexistente devuelve un error.

Returns:
    Lista de eventos etiquetados con su origen, o [{{'error': 'motivo'}}].
"""


def buscar_eventos(
    tipo: str = "any",
    fecha_inicio: str = "1900-01-01",
    fecha_fin: str = "2100-01-01",
    origen: str = "",
) -> list[dict]:
    return _buscar_eventos(
        tipo,
        fecha_inicio=fecha_inicio,
        fecha_fin=fecha_fin,
        origen=origen or None,
    )


buscar_eventos.__doc__ = _DESCRIPCION.format(
    categorias=_categorias,
    origenes=_origenes,
)
