import json
import logging
from pathlib import Path
from typing import Any


TOOLS_DIR = Path(__file__).resolve().parent
RUTA_SERVICIOS = TOOLS_DIR.parent / "Resources" / "D6_services_map.geojson"

SERVICIOS_POR_CATEGORIA = {
    "academic_pressure": {
        "SRV_AE_002",
        "SRV_AE_004",
        "SRV_AE_007",
        "SRV_AE_009",
        "SRV_AE_012",
        "SRV_AE_014",
    },
    "social_support": {
        "SRV_AE_001",
        "SRV_AE_004",
        "SRV_AE_006",
        "SRV_AE_009",
        "SRV_AE_011",
        "SRV_AE_014",
    },
    "career_concern": {
        "SRV_AE_001",
        "SRV_AE_003",
        "SRV_AE_006",
        "SRV_AE_008",
        "SRV_AE_011",
        "SRV_AE_013",
    },
    "sleep_and_routine": {
        "SRV_AE_003",
        "SRV_AE_005",
        "SRV_AE_008",
        "SRV_AE_010",
        "SRV_AE_013",
        "SRV_AE_015",
    },
    "service_navigation": {
        "SRV_AE_002",
        "SRV_AE_005",
        "SRV_AE_007",
        "SRV_AE_010",
        "SRV_AE_012",
        "SRV_AE_015",
    },
}


def buscar_servicios_ayuda(
    categoria: str, distrito: str | None = None
) -> dict[str, Any]:
    """
    Busca los servicios asociados a un motivo de orientación y sus datos de derivación.

    Args:
        categoria: Uno de 'academic_pressure', 'social_support',
            'career_concern', 'sleep_and_routine' o 'service_navigation'.
        distrito: Identificador opcional del distrito, por ejemplo 'DIST_GAIA'.
            Si se omite, se devuelven los servicios de todos los distritos.

    Returns:
        Un diccionario con la categoría, los servicios relacionados y una nota
        de seguridad. Cada servicio incluye ubicación, horario, canales,
        elegibilidad e información requerida para derivar.
    """
    if (
        not isinstance(categoria, str)
        or categoria.strip().lower() not in SERVICIOS_POR_CATEGORIA
    ):
        return {
            "error": (
                f"Categoría inválida: {categoria!r}. Usa una de estas opciones: "
                f"{', '.join(sorted(SERVICIOS_POR_CATEGORIA))}."
            )
        }

    categoria_normalizada = categoria.strip().lower()
    if distrito is not None and not isinstance(distrito, str):
        return {"error": "El distrito debe ser una cadena con un identificador de D6."}
    distrito_normalizado = distrito.strip().upper() if distrito is not None else None
    if distrito is not None and not distrito_normalizado:
        return {"error": "El distrito debe ser un identificador no vacío de D6."}

    try:
        with RUTA_SERVICIOS.open(encoding="utf-8") as archivo:
            mapa_servicios = json.load(archivo)
    except (OSError, json.JSONDecodeError) as error:
        logging.exception("No se pudieron cargar los datos de derivación.")
        return {"error": f"No se pudieron cargar los datos de derivación: {error}"}

    ids_servicio = SERVICIOS_POR_CATEGORIA[categoria_normalizada]
    if not ids_servicio:
        return {
            "error": (
                f"No hay servicios asociados a la categoría "
                f"{categoria_normalizada!r}."
            )
        }

    servicios_por_id = {
        feature["properties"]["service_id"]: feature
        for feature in mapa_servicios["features"]
    }
    distritos_disponibles = {
        feature["properties"]["district_id"]
        for feature in mapa_servicios["features"]
    }
    if distrito_normalizado and distrito_normalizado not in distritos_disponibles:
        return {
            "error": (
                f"Distrito inválido: {distrito!r}. Usa uno de estos identificadores: "
                f"{', '.join(sorted(distritos_disponibles))}."
            )
        }

    ids_faltantes = ids_servicio - servicios_por_id.keys()
    if ids_faltantes:
        logging.error("Faltan servicios en el mapa: %s", sorted(ids_faltantes))
        return {
            "error": (
                "El mapa no contiene los servicios referidos: "
                + ", ".join(sorted(ids_faltantes))
            )
        }

    if distrito_normalizado:
        ids_servicio = {
            service_id
            for service_id in ids_servicio
            if servicios_por_id[service_id]["properties"]["district_id"]
            == distrito_normalizado
        }
        if not ids_servicio:
            return {
                "error": (
                    f"No hay servicios para la categoría {categoria_normalizada!r} "
                    f"en el distrito {distrito_normalizado!r}."
                )
            }

    servicios = []
    for service_id in sorted(ids_servicio):
        feature = servicios_por_id[service_id]
        properties = feature["properties"]
        longitud, latitud = feature["geometry"]["coordinates"]
        servicios.append(
            {
                "service_id": service_id,
                "nombre": properties["name"],
                "tipo_servicio": properties["service_type"],
                "ubicacion": {
                    "distrito_id": properties["district_id"],
                    "coordenadas": {"longitud": longitud, "latitud": latitud},
                    "nota": (
                        "Coordenadas sintéticas; no representan una ubicación "
                        "real ni sirven para navegación."
                    ),
                },
                "horario_atencion": properties["schedule"],
                "canales_atencion": properties["channels"],
                "elegibilidad": properties["eligibility"],
                "informacion_requerida_derivacion": properties[
                    "referral_information"
                ],
            }
        )

    return {
        "categoria": categoria_normalizada,
        "distrito": distrito_normalizado,
        "servicios": servicios,
        "nota_seguridad": (
            "Orientación sintética y no clínica; requiere revisión humana. "
            "No diagnostica ni reemplaza la atención profesional."
        ),
    }
