"""Selección de servicios de apoyo.

``core`` es ciego al catálogo y al recurso: recibe la petición, la transmite a
Data y reenvía el resultado. Si Data lanza una excepción (categoría inexistente,
distrito inválido o servicios faltantes), aquí solo se captura y se reenvía como
error para que el agente lo comunique. No valida ni conoce las categorías; los
catálogos se piden a Data a través de ``categorias_disponibles`` y
``distritos_disponibles``.
"""

import logging
from typing import Any

from data.services import (
    CategoriaDesconocida,
    DistritoDesconocido,
    ServiciosFaltantes,
    buscar_servicios,
)
from data.services import (
    categorias_disponibles as _categorias_disponibles,
)
from data.services import (
    distritos_disponibles as _distritos_disponibles,
)


def categorias_disponibles() -> set[str]:
    """Devuelve las categorías de servicios disponibles, según Data."""
    return _categorias_disponibles()


def distritos_disponibles() -> set[str]:
    """Devuelve los distritos disponibles, según Data."""
    return _distritos_disponibles()


def buscar_servicios_ayuda(
    categoria: object, distrito: object = None
) -> dict[str, Any]:
    """Devuelve los servicios de una categoría y distrito opcional.

    No valida la categoría: delega en Data la resolución y, si no existe, Data
    lanza ``CategoriaDesconocida`` y aquí se reenvía como error.
    """
    try:
        return buscar_servicios(categoria, distrito)
    except (CategoriaDesconocida, DistritoDesconocido, ServiciosFaltantes) as error:
        return {"error": str(error)}
    except (OSError, ValueError) as error:
        logging.exception("No se pudieron cargar los datos de derivación.")
        return {"error": f"No se pudieron cargar los datos de derivación: {error}"}
