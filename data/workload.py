"""Lectura y reglas de negocio para la carga académica."""

import csv
from datetime import date, datetime, timedelta
from typing import Any

from data.resources import leer_recurso_csv

RECURSO_CALENDARIO = "D7_calendar.csv"
CATEGORIA_EVALUACION = "evaluation_week"
UMBRAL_SOBRECARGA_POR_DEFECTO = 3

_COLUMNAS_REQUERIDAS = (
    "calendar_event_id",
    "period_id",
    "event_type",
    "title",
    "start_date",
    "end_date",
    "evaluation_intensity",
)


class CalendarioAcademicoInvalido(ValueError):
    """El recurso académico falta, está incompleto o contiene datos inválidos."""


def listar_evaluaciones() -> list[dict[str, Any]]:
    """Carga y normaliza las evaluaciones del recurso académico."""
    try:
        filas = leer_recurso_csv(RECURSO_CALENDARIO)
    except (OSError, UnicodeDecodeError, csv.Error) as error:
        raise CalendarioAcademicoInvalido(
            f"No se pudieron cargar los datos del calendario académico: {error}"
        ) from error

    if not filas:
        raise CalendarioAcademicoInvalido(
            "No se pudieron cargar los datos del calendario académico."
        )

    columnas_faltantes = set(_COLUMNAS_REQUERIDAS) - set(filas[0])
    if columnas_faltantes:
        raise CalendarioAcademicoInvalido(
            "El CSV no contiene las columnas requeridas: "
            + ", ".join(sorted(columnas_faltantes))
        )

    evaluaciones = []
    for fila in filas:
        tipo_evento = (fila.get("event_type") or "").strip().lower()
        if tipo_evento != CATEGORIA_EVALUACION:
            continue

        event_id = fila.get("calendar_event_id", "desconocido")
        try:
            fecha_inicio = datetime.strptime(fila["start_date"], "%Y-%m-%d").date()
            fecha_fin = datetime.strptime(fila["end_date"], "%Y-%m-%d").date()
            intensidad = int(fila["evaluation_intensity"])
        except (TypeError, ValueError, KeyError) as error:
            raise CalendarioAcademicoInvalido(
                f"Datos inválidos para el evento {event_id}: fechas YYYY-MM-DD e "
                f"intensidad entera requeridas ({error})."
            ) from error
        if fecha_inicio > fecha_fin:
            raise CalendarioAcademicoInvalido(
                f"El evento {event_id} termina antes de su fecha de inicio."
            )
        if intensidad < 0:
            raise CalendarioAcademicoInvalido(
                f"La intensidad del evento {event_id} no puede ser negativa."
            )
        if intensidad:
            evaluaciones.append(
                {
                    "evento": fila["title"],
                    "fecha_inicio": fecha_inicio,
                    "fecha_fin": fecha_fin,
                    "intensidad": intensidad,
                    "periodo_id": fila["period_id"],
                }
            )
    return evaluaciones


def evaluar_riesgo_sobrecarga(
    umbral: int = UMBRAL_SOBRECARGA_POR_DEFECTO,
) -> dict[str, Any]:
    """Agrupa evaluaciones por semana y detecta semanas de sobrecarga."""
    if not isinstance(umbral, int) or isinstance(umbral, bool) or umbral < 1:
        raise ValueError("El umbral debe ser un entero mayor que cero.")
    evaluaciones = listar_evaluaciones()

    evaluaciones_por_semana: dict[str, list[dict[str, Any]]] = {}
    for evaluacion in evaluaciones:
        detalle_evento = {
            "evento": evaluacion["evento"],
            "fecha_inicio": evaluacion["fecha_inicio"].isoformat(),
            "fecha_fin": evaluacion["fecha_fin"].isoformat(),
            "intensidad": evaluacion["intensidad"],
            "periodo_id": evaluacion["periodo_id"],
        }
        for semana in _semanas_cubiertas(
            evaluacion["fecha_inicio"], evaluacion["fecha_fin"]
        ):
            evaluaciones_por_semana.setdefault(semana, []).append(detalle_evento)

    semanas_criticas = []
    for semana, eventos in sorted(evaluaciones_por_semana.items()):
        intensidad_total = sum(evento["intensidad"] for evento in eventos)
        if intensidad_total >= umbral:
            semanas_criticas.append({
                "semana": semana,
                "cantidad_eventos": len(eventos),
                "intensidad_total": intensidad_total,
                "nivel_riesgo": "ALTO" if intensidad_total >= 4 else "MEDIO",
                "eventos": eventos,
            })

    return {
        "total_semanas_analizadas": len(evaluaciones_por_semana),
        "semanas_con_sobrecarga": semanas_criticas,
        "recomendacion": (
            "Activar protocolo de fragmentación y derivación a bienestar"
            if semanas_criticas
            else "Carga académica dentro de parámetros normales."
        ),
    }


def _semanas_cubiertas(fecha_inicio: date, fecha_fin: date) -> set[str]:
    """Devuelve las semanas ISO (``2026-W07``) que abarca el evento."""
    semanas: set[str] = set()
    fecha_actual = fecha_inicio
    while fecha_actual <= fecha_fin:
        semana_iso = fecha_actual.isocalendar()
        semanas.add(f"{semana_iso.year}-W{semana_iso.week:02d}")
        fecha_actual += timedelta(days=1)
    return semanas
