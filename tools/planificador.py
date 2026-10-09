"""Análisis determinista de fechas de entrega concentradas."""
from __future__ import annotations

from collections import defaultdict
from typing import Any

from datos.repositorio_academico import consultar_tareas_db, validar_fecha


def evaluar_conflictos_academicos(
    fecha_inicio: str,
    fecha_fin: str,
    minutos_disponibles_por_dia: int = 120,
) -> dict[str, Any]:
    """Detecta días donde la suma del esfuerzo estimado vence el tiempo disponible.

    Esto es una alerta de concentración de entregas, no una predicción clínica ni
    un horario óptimo: no reparte automáticamente tareas en días anteriores.
    """
    try:
        inicio = validar_fecha(fecha_inicio)
        fin = validar_fecha(fecha_fin)
    except ValueError as exc:
        return {"error": str(exc)}
    if inicio > fin:
        return {"error": "La fecha inicial no puede ser posterior a la fecha final."}
    if not isinstance(minutos_disponibles_por_dia, int) or isinstance(minutos_disponibles_por_dia, bool):
        return {"error": "Los minutos disponibles deben ser un entero."}
    if not 15 <= minutos_disponibles_por_dia <= 1440:
        return {"error": "Los minutos disponibles deben estar entre 15 y 1440 por día."}

    try:
        tareas = consultar_tareas_db(
            estado="pendiente", fecha_inicio=inicio, fecha_fin=fin,
        )
    except ValueError as exc:
        return {"error": str(exc)}

    por_fecha: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for tarea in tareas:
        por_fecha[tarea["fecha_limite"]].append(tarea)

    resumen = []
    conflictos = []
    for fecha, tareas_dia in sorted(por_fecha.items()):
        minutos = sum(t["minutos_estimados"] for t in tareas_dia)
        dia = {
            "fecha": fecha,
            "cantidad_tareas": len(tareas_dia),
            "minutos_estimados_si_se_dejan_para_el_vencimiento": minutos,
            "minutos_disponibles_por_dia": minutos_disponibles_por_dia,
            "tareas": [
                {"materia": t["nombre_materia"], "titulo": t["titulo"],
                 "minutos_estimados": t["minutos_estimados"]}
                for t in tareas_dia
            ],
        }
        if minutos > minutos_disponibles_por_dia:
            dia["alerta"] = "La carga estimada supera el tiempo diario disponible."
            conflictos.append(dia)
        resumen.append(dia)

    return {
        "rango": {"desde": inicio, "hasta": fin},
        "dias_con_tareas": len(resumen),
        "cantidad_tareas": len(tareas),
        "dias_con_posible_conflicto": len(conflictos),
        "detalle_por_dia": resumen,
        "conflictos": conflictos,
        "limitacion": (
            "Se compara la estimación de esfuerzo de las tareas con el tiempo disponible "
            "el día de vencimiento. No calcula todavía bloques de estudio previos ni considera "
            "la dificultad real; usa estos avisos para conversar y proponer un plan al estudiante."
        ),
    }

