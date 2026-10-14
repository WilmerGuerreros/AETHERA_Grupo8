"""Lectura de las evaluaciones académicas usadas para estimar la sobrecarga.

Este módulo es el único que conoce el recurso ``D7_calendar.csv``: su nombre,
sus columnas y qué tipo de evento cuenta como evaluación. ``core`` solo recibe
la lista ya normalizada y calcula el riesgo; no sabe de dónde sale ni cómo se
llaman sus columnas.
"""

import csv
from datetime import datetime
from typing import Any

from data.resources import leer_recurso_csv


RECURSO_CALENDARIO = "D7_calendar.csv"

# Tipo de evento del CSV que representa una evaluación (semana de exámenes).
CATEGORIA_EVALUACION = "evaluation_week"

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
    """El recurso D7 falta, está incompleto o trae datos inconsistentes."""


def listar_evaluaciones() -> list[dict[str, Any]]:
    """Devuelve las evaluaciones con intensidad positiva ya normalizadas.

    Cada evaluación es un diccionario con ``evento``, ``fecha_inicio`` y
    ``fecha_fin`` (objetos ``date``), ``intensidad`` y ``periodo_id``. Lanza
    ``CalendarioAcademicoInvalido`` si el recurso no se puede leer, le faltan
    columnas o contiene fechas/intensidades inválidas.
    """
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

    evaluaciones: list[dict[str, Any]] = []
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
        if intensidad == 0:
            continue

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
