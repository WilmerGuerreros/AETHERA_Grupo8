"""Fachada de calendario: delega reglas y persistencia a Data."""

import logging
from datetime import date
from typing import Any

from data.calendar import (
    ORIGEN_EDITABLE,
    CalendarioInvalido,
    CalendarStore,
    CategoriaDesconocida,
    EventoAmbiguo,
    EventoNoEncontrado,
    OrigenDesconocido,
)
from data.calendar_operations import (
    FECHA_FIN_POR_DEFECTO,
    FECHA_INICIO_POR_DEFECTO,
    TIPO_TODAS_LAS_CATEGORIAS,
    borrar_evento_personal as _borrar_evento_personal,
    buscar_eventos as _buscar_eventos,
    categorias_disponibles as _categorias_disponibles,
    crear_evento as _crear_evento,
    eliminar_evento as _eliminar_evento,
    guardar_evento_personal as _guardar_evento_personal,
    obtener_eventos_semana as _obtener_eventos_semana,
    origenes_disponibles as _origenes_disponibles,
)


def origenes_disponibles() -> tuple[str, ...]:
    return _origenes_disponibles()


def categorias_disponibles(store: CalendarStore | None = None) -> set[str]:
    return _categorias_disponibles(store)


def buscar_eventos(
    tipo: str = TIPO_TODAS_LAS_CATEGORIAS,
    fecha_inicio: str = FECHA_INICIO_POR_DEFECTO,
    fecha_fin: str = FECHA_FIN_POR_DEFECTO,
    origen: str | None = None,
    store: CalendarStore | None = None,
) -> list[dict[str, Any]]:
    try:
        return _buscar_eventos(tipo, fecha_inicio, fecha_fin, origen, store)
    except (OSError, UnicodeDecodeError, ValueError, TypeError) as error:
        logging.exception("No se pudieron cargar los calendarios.")
        return [{"error": str(error)}]


def obtener_eventos_semana(
    fecha_inicio: date,
    fecha_fin: date,
    origen: str | None = None,
    categoria: str | None = None,
    store: CalendarStore | None = None,
) -> list[dict[str, Any]]:
    try:
        return _obtener_eventos_semana(
            fecha_inicio, fecha_fin, origen, categoria, store
        )
    except ValueError as error:
        raise ValueError(str(error)) from error


def eliminar_evento(
    uid: str, store: CalendarStore | None = None
) -> dict[str, str]:
    try:
        return _eliminar_evento(uid, store)
    except (
        CalendarioInvalido,
        EventoNoEncontrado,
        EventoAmbiguo,
        OSError,
        UnicodeDecodeError,
    ) as error:
        logging.exception("No se pudo eliminar el evento personal.")
        return {"error": str(error)}


def crear_evento(
    titulo: str,
    fecha_inicio: str,
    fecha_fin: str = "",
    descripcion: str = "",
    hora_inicio: str = "",
    hora_fin: str = "",
    store: CalendarStore | None = None,
) -> dict[str, Any]:
    try:
        return _crear_evento(
            titulo, fecha_inicio, fecha_fin, descripcion, hora_inicio, hora_fin, store
        )
    except (
        CalendarioInvalido,
        OSError,
        UnicodeDecodeError,
        ValueError,
        TypeError,
    ) as error:
        logging.exception("No se pudo guardar el evento personal.")
        return {"error": str(error)}


def guardar_evento_personal(
    titulo: str,
    fecha_inicio: str,
    fecha_fin: str = "",
    descripcion: str = "",
    hora_inicio: str = "",
    hora_fin: str = "",
    store: CalendarStore | None = None,
) -> dict[str, Any]:
    try:
        return _guardar_evento_personal(
            titulo, fecha_inicio, fecha_fin, descripcion, hora_inicio, hora_fin, store
        )
    except (
        CalendarioInvalido,
        OSError,
        UnicodeDecodeError,
        ValueError,
        TypeError,
    ) as error:
        logging.exception("No se pudo guardar el evento personal.")
        return {"error": str(error)}


def borrar_evento_personal(
    evento: dict[str, Any], store: CalendarStore | None = None
) -> dict[str, str]:
    try:
        return _borrar_evento_personal(evento, store)
    except (
        CalendarioInvalido,
        EventoNoEncontrado,
        EventoAmbiguo,
        OSError,
        UnicodeDecodeError,
        ValueError,
        TypeError,
    ) as error:
        logging.exception("No se pudo eliminar el evento personal.")
        return {"error": str(error)}


__all__ = [
    "ORIGEN_EDITABLE",
    "CalendarioInvalido",
    "CalendarStore",
    "CategoriaDesconocida",
    "EventoAmbiguo",
    "EventoNoEncontrado",
    "OrigenDesconocido",
    "borrar_evento_personal",
    "buscar_eventos",
    "categorias_disponibles",
    "crear_evento",
    "eliminar_evento",
    "guardar_evento_personal",
    "obtener_eventos_semana",
    "origenes_disponibles",
]
