"""Reglas, validaciones y consultas de calendario.

``core`` es ciego al almacenamiento: valida la petición, delega la lectura y la
escritura en el repositorio de Data y devuelve el resultado. No conoce rutas,
archivos ni el formato ICS.
"""

import logging
from datetime import date, datetime, time
from typing import Any

from data.calendar import (
    CalendarioInvalido,
    CalendarStore,
    EventoAmbiguo,
    EventoNoEncontrado,
)


ORIGENES_CALENDARIO = {
    "Ambos": "ambos",
    "Académico": "academico",
    "Personal": "personal",
}
CATEGORIAS_CALENDARIO = {
    "Evaluaciones": {"evaluation_week"},
    "Bienestar": {"wellbeing_activity"},
    "Períodos académicos": {"period_start", "period_end"},
    "Actividades": {"university_activity"},
}


def _resolver_store(store: CalendarStore | None) -> CalendarStore:
    """Devuelve el repositorio indicado o el de producción."""
    return store if store is not None else CalendarStore()


def buscar_eventos(
    tipo: str,
    fecha_inicio: str = "1900-01-01",
    fecha_fin: str = "2100-01-01",
    origen: str = "ambos",
    store: CalendarStore | None = None,
) -> list[dict[str, Any]]:
    """Devuelve eventos filtrados por rango, categoría y origen."""
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
    categorias_validas = {
        "any",
        "period_start",
        "evaluation_week",
        "wellbeing_activity",
        "period_end",
        "university_activity",
    }
    if tipo_normalizado not in categorias_validas:
        return [
            {
                "error": (
                    f"Categoría inválida: {tipo}. Usa una de estas opciones: "
                    f"{', '.join(sorted(categorias_validas))}."
                )
            }
        ]

    origen_normalizado = origen.strip().lower() if isinstance(origen, str) else ""
    origenes = {
        "academico": ("academico",),
        "personal": ("personal",),
        "ambos": ("academico", "personal"),
    }
    if origen_normalizado not in origenes:
        return [{"error": "El origen debe ser 'academico', 'personal' o 'ambos'."}]

    categorias = None if tipo_normalizado == "any" else {tipo_normalizado}
    try:
        almacen = _resolver_store(store)
        eventos = []
        for nombre_origen in origenes[origen_normalizado]:
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
    except (OSError, UnicodeDecodeError) as error:
        logging.exception("No se pudieron cargar los calendarios.")
        return [{"error": f"No se pudieron cargar los calendarios: {error}"}]


def obtener_eventos_semana(
    fecha_inicio: date,
    fecha_fin: date,
    origen: str,
    categoria: str,
    store: CalendarStore | None = None,
) -> list[dict[str, Any]]:
    """Carga eventos de un rango y aplica el origen y categoría seleccionados."""
    origen_consulta = ORIGENES_CALENDARIO.get(origen)
    if origen_consulta is None:
        raise ValueError(f"Origen de calendario inválido: {origen}")

    eventos = buscar_eventos(
        "any",
        fecha_inicio=fecha_inicio.isoformat(),
        fecha_fin=fecha_fin.isoformat(),
        origen=origen_consulta,
        store=store,
    )
    if eventos and "error" in eventos[0]:
        raise ValueError(eventos[0]["error"])

    categorias = CATEGORIAS_CALENDARIO.get(categoria)
    if categorias is None:
        return eventos
    return [evento for evento in eventos if evento.get("categoria") in categorias]


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
            "origen": "personal",
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
    """Elimina un evento solo cuando su origen es el calendario personal."""
    if evento.get("origen") != "personal":
        return {"error": "Solo se pueden eliminar eventos del calendario Personal."}
    uid = evento.get("uid")
    if not isinstance(uid, str) or not uid.strip():
        return {"error": "El evento personal no contiene un identificador válido."}
    return eliminar_evento(uid, store=store)
