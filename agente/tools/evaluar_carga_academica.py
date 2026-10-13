"""Herramienta del agente para evaluar la carga académica."""

from typing import Any

from dominio.carga_academica import (
    evaluar_riesgo_sobrecarga as _evaluar_riesgo_sobrecarga,
)


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
    return _evaluar_riesgo_sobrecarga(umbral)
