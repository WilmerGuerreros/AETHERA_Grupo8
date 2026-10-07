import csv
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List

# Ruta a la carpeta Resources desde la carpeta tools
TOOLS_DIR = Path(__file__).resolve().parent
RUTA_CALENDARIO_CSV = TOOLS_DIR.parent / "Resources" / "D7_calendar.csv"


def _cargar_csv_data(file_path: Path) -> List[Dict[str, str]]:
    """Carga datos desde el archivo CSV local."""
    try:
        with open(file_path, mode='r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            return list(reader)
    except FileNotFoundError:
        logging.error(f"No se encontró el archivo: {file_path}")
        return []
    except Exception as e:
        logging.error(f"Error al leer el CSV: {e}")
        return []


def evaluar_riesgo_sobrecarga(umbral: int = 3) -> Dict[str, Any]:
    """
    Analiza el calendario académico D7_calendar.csv, fragmenta las evaluaciones por semanas 
    y detecta si existen semanas críticas que superen el umbral de sobrecarga.

    Args:
        umbral (int): Cantidad mínima de evaluaciones en una misma semana para considerar sobrecarga (por defecto es 3).

    Returns:
        Dict[str, Any]: Diccionario con las semanas analizadas, las semanas con sobrecarga y la recomendación para bienestar.
    """
    calendar_data = _cargar_csv_data(RUTA_CALENDARIO_CSV)

    if not calendar_data:
        return {"error": f"No se pudieron cargar los datos desde {RUTA_CALENDARIO_CSV}"}

    evaluaciones_por_semana = {}

    for evento in calendar_data:
        # Extraer campos asegurando tolerancia a mayúsculas/minúsculas en las columnas
        fecha_str = evento.get('fecha', '')
        tipo = evento.get('tipo', 'actividad').lower()
        curso = evento.get('curso', 'Desconocido')

        # Filtrar solo eventos de tipo evaluación/entrega/examen
        if any(palabra in tipo for palabra in ['examen', 'entrega', 'evaluacion', 'evaluación']):
            try:
                fecha = datetime.strptime(fecha_str, "%Y-%m-%d").date()
                semana_key = fecha.strftime("%Y-W%W")

                if semana_key not in evaluaciones_por_semana:
                    evaluaciones_por_semana[semana_key] = []

                evaluaciones_por_semana[semana_key].append({
                    "curso": curso,
                    "fecha": fecha_str,
                    "tipo": tipo
                })
            except ValueError:
                continue

    # Detectar sobrecarga
    semanas_criticas = []
    for semana, eventos in evaluaciones_por_semana.items():
        if len(eventos) >= umbral:
            semanas_criticas.append({
                "semana": semana,
                "cantidad_eventos": len(eventos),
                "nivel_riesgo": "ALTO" if len(eventos) >= 4 else "MEDIO",
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