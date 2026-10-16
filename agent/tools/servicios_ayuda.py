"""Herramienta del agente para buscar servicios de apoyo."""

from typing import Any

from core.services import (
    buscar_servicios_ayuda as _buscar_servicios_ayuda,
    categorias_disponibles,
    distritos_disponibles,
)

_categorias = ", ".join(sorted(categorias_disponibles()))
_distritos = ", ".join(sorted(distritos_disponibles()))


_DESCRIPCION = """
Busca los servicios asociados a un motivo de orientación y sus datos de derivación.

Args:
    categoria: Código del motivo de orientación. Categorías válidas: {categorias}.
        Si no coincide con una opción, la herramienta devuelve un error.
    distrito: Identificador opcional del distrito. Distritos válidos: {distritos}.
        Si se omite, busca en todos los distritos. Un distrito inexistente devuelve
        un error con las opciones válidas.

Returns:
    Un diccionario con la categoría y los servicios relacionados.
    Cada servicio incluye ubicación, horario, canales,
    elegibilidad e información requerida para derivar.
"""


def buscar_servicios_ayuda(
    categoria: str, distrito: str | None = None
) -> dict[str, Any]:
    return _buscar_servicios_ayuda(categoria, distrito)


buscar_servicios_ayuda.__doc__ = _DESCRIPCION.format(
    categorias=_categorias,
    distritos=_distritos,
)
