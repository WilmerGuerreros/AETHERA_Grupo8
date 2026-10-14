"""Lectura y filtrado del mapa de servicios de apoyo (D6).

Este módulo es el único que conoce el nombre del recurso, la estructura del
mapa y el catálogo de categorías de apoyo. ``core`` solo pide servicios por
categoría y distrito; aquí se resuelve la categoría, se normaliza la petición,
se filtran los servicios y se lanzan excepciones explícitas cuando algo no
existe (categoría, distrito o servicio referido).
"""

import logging
from typing import Any, Iterable

from data.resources import leer_recurso_json


RECURSO_SERVICIOS = "D6_services_map.geojson"

# Catálogo de categorías de apoyo: qué servicios referidos (``service_id``)
# atienden cada motivo de orientación. Es estructura de los datos, no del core.
SERVICIOS_POR_CATEGORIA: dict[str, frozenset[str]] = {
    "academic_pressure": frozenset(
        {
            "SRV_AE_002",
            "SRV_AE_004",
            "SRV_AE_007",
            "SRV_AE_009",
            "SRV_AE_012",
            "SRV_AE_014",
        }
    ),
    "social_support": frozenset(
        {
            "SRV_AE_001",
            "SRV_AE_004",
            "SRV_AE_006",
            "SRV_AE_009",
            "SRV_AE_011",
            "SRV_AE_014",
        }
    ),
    "career_concern": frozenset(
        {
            "SRV_AE_001",
            "SRV_AE_003",
            "SRV_AE_006",
            "SRV_AE_008",
            "SRV_AE_011",
            "SRV_AE_013",
        }
    ),
    "sleep_and_routine": frozenset(
        {
            "SRV_AE_003",
            "SRV_AE_005",
            "SRV_AE_008",
            "SRV_AE_010",
            "SRV_AE_013",
            "SRV_AE_015",
        }
    ),
    "service_navigation": frozenset(
        {
            "SRV_AE_002",
            "SRV_AE_005",
            "SRV_AE_007",
            "SRV_AE_010",
            "SRV_AE_012",
            "SRV_AE_015",
        }
    ),
}


class CategoriaDesconocida(ValueError):
    """La categoría pedida no existe en el catálogo de servicios."""


class DistritoDesconocido(ValueError):
    """El distrito pedido no existe en el mapa de servicios."""


class ServiciosFaltantes(ValueError):
    """El mapa no contiene alguno de los servicios referidos."""


def categorias_disponibles() -> set[str]:
    """Devuelve las categorías de apoyo presentes en el catálogo."""
    return set(SERVICIOS_POR_CATEGORIA)


def distritos_disponibles() -> set[str]:
    """Devuelve los identificadores de distrito presentes en el mapa."""
    return {
        feature["properties"]["district_id"]
        for feature in _cargar_mapa()["features"]
    }


def buscar_servicios(
    categoria: object, distrito: object = None
) -> dict[str, Any]:
    """Devuelve los servicios de una categoría y distrito opcional.

    Normaliza la categoría y el distrito y resuelve la categoría contra el
    catálogo. Lanza ``CategoriaDesconocida`` si la categoría no existe,
    ``DistritoDesconocido`` si el distrito no es válido y ``ServiciosFaltantes``
    si el mapa no contiene alguno de los servicios referidos.
    """
    categoria_normalizada = _normalizar_categoria(categoria)
    distrito_normalizado = _normalizar_distrito(distrito)
    servicios = listar_servicios(
        SERVICIOS_POR_CATEGORIA[categoria_normalizada],
        distrito_normalizado,
    )
    return {
        "categoria": categoria_normalizada,
        "distrito": distrito_normalizado,
        "servicios": servicios,
    }


def listar_servicios(
    ids_servicio: Iterable[str],
    distrito: str | None = None,
) -> list[dict[str, Any]]:
    """Devuelve los servicios del mapa que coinciden con los ids y el distrito.

    Lanza ``DistritoDesconocido`` si el distrito no existe en el mapa y
    ``ServiciosFaltantes`` si el mapa no contiene alguno de los ids pedidos. Si
    no hay coincidencias devuelve una lista vacía (no es un error).
    """
    features = _cargar_mapa()["features"]
    servicios_por_id = {
        feature["properties"]["service_id"]: feature for feature in features
    }

    ids_solicitados = set(ids_servicio)
    faltantes = ids_solicitados - servicios_por_id.keys()
    if faltantes:
        logging.error("Faltan servicios en el mapa: %s", sorted(faltantes))
        raise ServiciosFaltantes(
            "El mapa no contiene los servicios referidos: "
            + ", ".join(sorted(faltantes))
        )

    if distrito is not None:
        disponibles = {
            feature["properties"]["district_id"] for feature in features
        }
        if distrito not in disponibles:
            raise DistritoDesconocido(
                f"Distrito inválido: {distrito!r}. Usa uno de estos "
                f"identificadores: {', '.join(sorted(disponibles))}."
            )

    servicios = []
    for service_id in sorted(ids_solicitados):
        feature = servicios_por_id[service_id]
        if distrito is not None and feature["properties"]["district_id"] != distrito:
            continue
        servicios.append(_a_servicio(service_id, feature))
    return servicios


def _normalizar_categoria(categoria: object) -> str:
    if isinstance(categoria, str):
        normalizada = categoria.strip().lower()
        if normalizada in SERVICIOS_POR_CATEGORIA:
            return normalizada
    raise CategoriaDesconocida(
        f"Categoría inválida: {categoria!r}. Usa una de estas opciones: "
        f"{', '.join(sorted(SERVICIOS_POR_CATEGORIA))}."
    )


def _normalizar_distrito(distrito: object) -> str | None:
    if distrito is None:
        return None
    if not isinstance(distrito, str):
        raise DistritoDesconocido(
            "El distrito debe ser una cadena con un identificador de D6."
        )
    normalizado = distrito.strip().upper()
    if not normalizado:
        raise DistritoDesconocido(
            "El distrito debe ser un identificador no vacío de D6."
        )
    return normalizado


def _cargar_mapa() -> dict[str, Any]:
    return leer_recurso_json(RECURSO_SERVICIOS)


def _a_servicio(service_id: str, feature: dict[str, Any]) -> dict[str, Any]:
    properties = feature["properties"]
    longitud, latitud = feature["geometry"]["coordinates"]
    return {
        "service_id": service_id,
        "nombre": properties["name"],
        "tipo_servicio": properties["service_type"],
        "ubicacion": {
            "distrito_id": properties["district_id"],
            "coordenadas": {"longitud": longitud, "latitud": latitud},
        },
        "horario_atencion": properties["schedule"],
        "canales_atencion": properties["channels"],
        "eligibilidad": "Aethera students",
        "informacion_requerida_derivacion": properties["referral_information"],
    }
