"""Tools de solo lectura para consultar tareas académicas guardadas."""
from __future__ import annotations

from typing import Any

from datos.repositorio_academico import consultar_tareas_db


def consultar_tareas(
    materia_id: str = "",
    estado: str = "pendiente",
    fecha_inicio: str = "",
    fecha_fin: str = "",
) -> dict[str, Any]:
    """Lista tareas existentes por materia, estado y rango de fechas.

    Args:
        materia_id: Identificador de materia, por ejemplo 'matematica_discreta'.
            Cadena vacía consulta todas las materias.
        estado: 'pendiente', 'completada' o 'todas'.
        fecha_inicio: Filtro opcional YYYY-MM-DD.
        fecha_fin: Filtro opcional YYYY-MM-DD.
    """
    try:
        tareas = consultar_tareas_db(
            materia_id=materia_id,
            estado=estado,
            fecha_inicio=fecha_inicio or None,
            fecha_fin=fecha_fin or None,
        )
    except ValueError as exc:
        return {"error": str(exc)}

    return {
        "cantidad": len(tareas),
        "tareas": tareas,
        "nota": "La consulta solo lee tareas guardadas; no crea, modifica ni elimina tareas.",
    }

