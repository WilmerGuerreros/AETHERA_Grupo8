import csv
import logging
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

from app_paths import resource_path


RUTA_CALENDARIO_CSV = resource_path("Resources", "D7_calendar.csv")


def _cargar_csv_data(file_path: Path) -> list[dict[str, str]]:
    """Carga datos desde el archivo CSV local."""
    try:
        with file_path.open(mode="r", encoding="utf-8", newline="") as file:
            reader = csv.DictReader(file)
            return list(reader)
    except FileNotFoundError:
        logging.error(f"No se encontró el archivo: {file_path}")
        return []
    except (OSError, UnicodeDecodeError, csv.Error) as e:
        logging.error(f"Error al leer el CSV: {e}")
        return []


def evaluar_riesgo_sobrecarga(umbral: int = 3) -> dict[str, Any]:
    """
    Analiza el calendario académico, fragmenta las evaluaciones por semanas 
    y detecta semanas críticas según la intensidad total de evaluaciones.

    Args:
        umbral (int): Intensidad mínima de evaluaciones en una misma semana para considerar
            sobrecarga (por defecto es 3).

    Returns:
        dict[str, Any]: Semanas analizadas, semanas con sobrecarga y recomendación para bienestar.
    """
    if not isinstance(umbral, int) or isinstance(umbral, bool) or umbral < 1:
        return {"error": "El umbral debe ser un entero mayor que cero."}

    calendar_data = _cargar_csv_data(RUTA_CALENDARIO_CSV)

    if not calendar_data:
        return {"error": f"No se pudieron cargar los datos desde {RUTA_CALENDARIO_CSV}"}

    columnas_requeridas = {
        "calendar_event_id",
        "period_id",
        "event_type",
        "title",
        "start_date",
        "end_date",
        "evaluation_intensity",
    }
    columnas_disponibles = set(calendar_data[0])
    columnas_faltantes = columnas_requeridas - columnas_disponibles
    if columnas_faltantes:
        return {
            "error": (
                "El CSV no contiene las columnas requeridas: "
                + ", ".join(sorted(columnas_faltantes))
            )
        }

    evaluaciones_por_semana: dict[str, list[dict[str, Any]]] = {}

    for evento in calendar_data:
        tipo_evento = (evento.get("event_type") or "").strip().lower()
        if tipo_evento != "evaluation_week":
            continue

        event_id = evento.get("calendar_event_id", "desconocido")
        try:
            fecha_inicio = datetime.strptime(evento["start_date"], "%Y-%m-%d").date()
            fecha_fin = datetime.strptime(evento["end_date"], "%Y-%m-%d").date()
            intensidad = int(evento["evaluation_intensity"])
        except (TypeError, ValueError) as error:
            return {
                "error": (
                    f"Datos inválidos para el evento {event_id}: "
                    f"fechas YYYY-MM-DD e intensidad entera requeridas ({error})."
                )
            }

        if fecha_inicio > fecha_fin:
            return {"error": f"El evento {event_id} termina antes de su fecha de inicio."}
        if intensidad < 0:
            return {"error": f"La intensidad del evento {event_id} no puede ser negativa."}
        if intensidad == 0:
            continue

        semanas_del_evento: set[str] = set()
        fecha_actual: date = fecha_inicio
        while fecha_actual <= fecha_fin:
            semana_iso = fecha_actual.isocalendar()
            semanas_del_evento.add(f"{semana_iso.year}-W{semana_iso.week:02d}")
            fecha_actual += timedelta(days=1)

        detalle_evento = {
            "evento": evento["title"],
            "fecha_inicio": fecha_inicio.isoformat(),
            "fecha_fin": fecha_fin.isoformat(),
            "intensidad": intensidad,
            "periodo_id": evento["period_id"],
        }
        for semana in semanas_del_evento:
            evaluaciones_por_semana.setdefault(semana, []).append(detalle_evento)

    # Detectar sobrecarga
    semanas_criticas = []
    for semana, eventos in sorted(evaluaciones_por_semana.items()):
        intensidad_total = sum(evento["intensidad"] for evento in eventos)
        if intensidad_total >= umbral:
            semanas_criticas.append({
                "semana": semana,
                "cantidad_eventos": len(eventos),
                "intensidad_total": intensidad_total,
                "nivel_riesgo": "ALTO" if intensidad_total >= 4 else "MEDIO",
                "eventos": eventos
            })

    return {
        "total_semanas_analizadas": len(evaluaciones_por_semana),
        "semanas_con_sobrecarga": semanas_criticas,
        "recomendacion": (
            "Activar protocolo de fragmentación y derivación a bienestar"
            if semanas_criticas else "Carga académica dentro de parámetros normales."
        )
    }