"""Cálculo de carga académica y detección de semanas de sobrecarga.

Solo recibe de Data las evaluaciones ya normalizadas y aplica la regla de
negocio: agrupa por semana, suma intensidad y marca las semanas que alcanzan el
umbral. No conoce el nombre del recurso, sus columnas ni sus categorías.
"""

from datetime import date, timedelta
from typing import Any

from data.workload import CalendarioAcademicoInvalido, listar_evaluaciones


def evaluar_riesgo_sobrecarga(umbral: int = 3) -> dict[str, Any]:
    """Agrupa evaluaciones por semana y detecta semanas de sobrecarga."""
    if not isinstance(umbral, int) or isinstance(umbral, bool) or umbral < 1:
        return {"error": "El umbral debe ser un entero mayor que cero."}

    try:
        evaluaciones = listar_evaluaciones()
    except CalendarioAcademicoInvalido as error:
        return {"error": str(error)}

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
