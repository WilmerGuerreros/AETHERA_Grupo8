"""Operaciones y filtros de los calendarios académico y personal."""

from datetime import date
from typing import Any

from agente.tools.buscar_eventos import buscar_eventos
from agente.tools.crear_evento import crear_evento, eliminar_evento


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


def obtener_eventos_semana(
    fecha_inicio: date,
    fecha_fin: date,
    origen: str,
    categoria: str,
) -> list[dict[str, Any]]:
    """Carga eventos de un rango y aplica los filtros seleccionados."""
    origen_consulta = ORIGENES_CALENDARIO.get(origen)
    if origen_consulta is None:
        raise ValueError(f"Origen de calendario inválido: {origen}")

    eventos = buscar_eventos(
        "any",
        fecha_inicio=fecha_inicio.isoformat(),
        fecha_fin=fecha_fin.isoformat(),
        origen=origen_consulta,
    )
    if eventos and "error" in eventos[0]:
        raise ValueError(eventos[0]["error"])

    categorias = CATEGORIAS_CALENDARIO.get(categoria)
    if categorias is None:
        return eventos
    return [
        evento
        for evento in eventos
        if evento.get("categoria") in categorias
    ]


def guardar_evento_personal(
    titulo: str,
    fecha_inicio: str,
    fecha_fin: str = "",
    descripcion: str = "",
    hora_inicio: str = "",
    hora_fin: str = "",
) -> dict[str, Any]:
    """Guarda un evento personal mediante la herramienta del calendario."""
    return crear_evento(
        titulo,
        fecha_inicio,
        fecha_fin,
        descripcion,
        hora_inicio,
        hora_fin,
    )


def borrar_evento_personal(evento: dict[str, Any]) -> dict[str, Any]:
    """Elimina un evento solo si pertenece al calendario personal."""
    if evento.get("origen") != "personal":
        return {"error": "Solo se pueden eliminar eventos del calendario Personal."}
    uid = evento.get("uid")
    if not isinstance(uid, str) or not uid.strip():
        return {"error": "El evento personal no contiene un identificador válido."}
    return eliminar_evento(uid)
