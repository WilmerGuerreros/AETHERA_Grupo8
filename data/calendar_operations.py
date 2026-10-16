"""Reglas, validaciones y consultas de calendario."""

import logging
from datetime import date, datetime, time
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
from data.calendar import (
    categorias_disponibles as _categorias_disponibles,
)
from data.calendar import (
    origenes_disponibles as _origenes_disponibles,
)

TIPO_TODAS_LAS_CATEGORIAS = "any"
FECHA_INICIO_POR_DEFECTO = "1900-01-01"
FECHA_FIN_POR_DEFECTO = "2100-01-01"


def origenes_disponibles() -> tuple[str, ...]:
    """Devuelve los orígenes (calendarios) disponibles, según Data."""
    return _origenes_disponibles()


def categorias_disponibles(store: CalendarStore | None = None) -> set[str]:
    """Devuelve las categorías del calendario académico, según Data."""
    return _categorias_disponibles(store)


def _resolver_store(store: CalendarStore | None) -> CalendarStore:
    """Devuelve el repositorio indicado o el de producción."""
    return store if store is not None else CalendarStore()


def buscar_eventos(
    tipo: str = TIPO_TODAS_LAS_CATEGORIAS,
    fecha_inicio: str = FECHA_INICIO_POR_DEFECTO,
    fecha_fin: str = FECHA_FIN_POR_DEFECTO,
    origen: str | None = None,
    store: CalendarStore | None = None,
) -> list[dict[str, Any]]:
    """Devuelve eventos filtrados por rango, categoría y origen.

    ``tipo`` es una categoría exacta o ``"any"`` para todas; ``origen`` es uno
    de los calendarios disponibles o ``None`` para consultarlos todos. Data es
    quien valida que la categoría y el origen existan.
    """
    try:
        dt_inicio_busqueda = date.fromisoformat(fecha_inicio)
        dt_fin_busqueda = date.fromisoformat(fecha_fin)
    except (TypeError, ValueError):
        return [{"error": "Las fechas deben tener el formato YYYY-MM-DD."}]

    if dt_inicio_busqueda > dt_fin_busqueda:
        return [{"error": "La fecha de inicio no puede ser posterior a la fecha de fin."}]

    if not isinstance(tipo, str):
        return [{"error": "La categoría debe ser una cadena de texto."}]
    tipo_normalizado = tipo.strip().lower()
    categorias = (
        None
        if tipo_normalizado in ("", TIPO_TODAS_LAS_CATEGORIAS)
        else {tipo_normalizado}
    )

    origen_normalizado = origen.strip().lower() if isinstance(origen, str) else ""
    if origen_normalizado:
        origenes = (origen_normalizado,)
    else:
        origenes = _origenes_disponibles()

    try:
        almacen = _resolver_store(store)
        eventos = []
        for nombre_origen in origenes:
            eventos.extend(
                almacen.listar(
                    nombre_origen,
                    dt_inicio_busqueda,
                    dt_fin_busqueda,
                    categorias,
                )
            )
        return sorted(
            eventos,
            key=lambda evento: (evento["fecha_inicio"], evento["resumen"]),
        )
    except (OrigenDesconocido, CategoriaDesconocida) as error:
        return [{"error": str(error)}]
    except (OSError, UnicodeDecodeError) as error:
        logging.exception("No se pudieron cargar los calendarios.")
        return [{"error": f"No se pudieron cargar los calendarios: {error}"}]


def obtener_eventos_semana(
    fecha_inicio: date,
    fecha_fin: date,
    origen: str | None = None,
    categoria: str | None = None,
    store: CalendarStore | None = None,
) -> list[dict[str, Any]]:
    """Carga eventos de un rango aplicando el origen y la categoría elegidos.

    ``origen`` y ``categoria`` son códigos provistos por Data, o ``None`` para
    no filtrar. Data valida su existencia y Core solo relega el error.
    """
    if isinstance(categoria, str) and categoria.strip():
        tipo = categoria.strip()
    else:
        tipo = TIPO_TODAS_LAS_CATEGORIAS

    eventos = buscar_eventos(
        tipo,
        fecha_inicio=fecha_inicio.isoformat(),
        fecha_fin=fecha_fin.isoformat(),
        origen=origen,
        store=store,
    )
    if eventos and "error" in eventos[0]:
        raise ValueError(eventos[0]["error"])
    return eventos


def eliminar_evento(
    uid: str, store: CalendarStore | None = None
) -> dict[str, str]:
    """Elimina un evento personal identificado por su UID."""
    if not isinstance(uid, str) or not uid.strip():
        return {"error": "Se requiere un identificador de evento válido."}

    try:
        _resolver_store(store).eliminar(uid)
    except (CalendarioInvalido, EventoNoEncontrado, EventoAmbiguo) as error:
        return {"error": str(error)}
    except (OSError, UnicodeDecodeError) as error:
        logging.exception("No se pudo eliminar el evento personal.")
        return {"error": f"No se pudo eliminar el evento personal: {error}"}

    return {"mensaje": "Evento eliminado del calendario Personal."}


def crear_evento(
    titulo: str,
    fecha_inicio: str,
    fecha_fin: str = "",
    descripcion: str = "",
    hora_inicio: str = "",
    hora_fin: str = "",
    store: CalendarStore | None = None,
) -> dict[str, Any]:
    """Valida y crea un evento de día completo o con horario."""
    if not isinstance(titulo, str) or not titulo.strip():
        return {"error": "El título del evento no puede estar vacío."}
    titulo = titulo.strip()
    if len(titulo) > 200:
        return {"error": "El título del evento no puede superar 200 caracteres."}
    if not isinstance(descripcion, str):
        return {"error": "La descripción debe ser texto."}
    descripcion = descripcion.strip()
    if len(descripcion) > 2000:
        return {"error": "La descripción no puede superar 2000 caracteres."}

    try:
        inicio = date.fromisoformat(fecha_inicio)
        fin = date.fromisoformat(fecha_fin) if fecha_fin else inicio
    except (TypeError, ValueError):
        return {"error": "Las fechas deben tener el formato YYYY-MM-DD."}
    if inicio.isoformat() != fecha_inicio or (fecha_fin and fin.isoformat() != fecha_fin):
        return {"error": "Las fechas deben tener el formato YYYY-MM-DD."}
    if fin < inicio:
        return {"error": "La fecha de fin no puede ser anterior a la fecha de inicio."}
    if fin == date.max:
        return {"error": "La fecha de fin debe ser anterior al 31/12/9999."}

    if not isinstance(hora_inicio, str) or not isinstance(hora_fin, str):
        return {"error": "Las horas deben ser texto en formato HH:MM."}
    hora_inicio = hora_inicio.strip()
    hora_fin = hora_fin.strip()
    if bool(hora_inicio) != bool(hora_fin):
        return {"error": "Debes indicar tanto la hora de inicio como la de fin."}

    inicio_horario = None
    fin_horario = None
    if hora_inicio:
        try:
            inicio_horario = time.fromisoformat(hora_inicio)
            fin_horario = time.fromisoformat(hora_fin)
        except ValueError:
            return {"error": "Las horas deben tener el formato HH:MM."}
        if (
            inicio_horario.strftime("%H:%M") != hora_inicio
            or fin_horario.strftime("%H:%M") != hora_fin
        ):
            return {"error": "Las horas deben tener el formato HH:MM."}
        fecha_hora_inicio = datetime.combine(inicio, inicio_horario)
        fecha_hora_fin = datetime.combine(fin, fin_horario)
        if fecha_hora_fin <= fecha_hora_inicio:
            return {
                "error": "La fecha y hora de fin deben ser posteriores a las de inicio."
            }

    try:
        _resolver_store(store).agregar(
            titulo,
            inicio,
            fin,
            descripcion,
            inicio_horario,
            fin_horario,
        )
    except CalendarioInvalido as error:
        return {"error": str(error)}
    except (OSError, UnicodeDecodeError) as error:
        logging.exception("No se pudo guardar el evento personal.")
        return {"error": f"No se pudo guardar el evento personal: {error}"}

    return {
        "mensaje": "Evento creado en el calendario Personal.",
        "evento": {
            "resumen": titulo,
            "fecha_inicio": inicio.isoformat(),
            "fecha_fin": fin.isoformat(),
            "hora_inicio": hora_inicio or None,
            "hora_fin": hora_fin or None,
            "descripcion": descripcion,
            "origen": ORIGEN_EDITABLE,
            "editable": True,
        },
    }


def guardar_evento_personal(
    titulo: str,
    fecha_inicio: str,
    fecha_fin: str = "",
    descripcion: str = "",
    hora_inicio: str = "",
    hora_fin: str = "",
    store: CalendarStore | None = None,
) -> dict[str, Any]:
    """Crea un evento personal usando las mismas reglas del calendario."""
    return crear_evento(
        titulo,
        fecha_inicio,
        fecha_fin,
        descripcion,
        hora_inicio,
        hora_fin,
        store=store,
    )


def borrar_evento_personal(
    evento: dict[str, Any], store: CalendarStore | None = None
) -> dict[str, str]:
    """Elimina un evento solo cuando pertenece al calendario personal (editable)."""
    if evento.get("origen") != ORIGEN_EDITABLE:
        return {"error": "Solo se pueden eliminar eventos del calendario Personal."}
    uid = evento.get("uid")
    if not isinstance(uid, str) or not uid.strip():
        return {"error": "El evento personal no contiene un identificador válido."}
    return eliminar_evento(uid, store=store)
