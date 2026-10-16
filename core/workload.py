"""Fachada de carga académica; las reglas residen en Data."""

import logging
from typing import Any

from data.workload import (
    UMBRAL_SOBRECARGA_POR_DEFECTO,
    evaluar_riesgo_sobrecarga as _evaluar_riesgo_sobrecarga,
)


def evaluar_riesgo_sobrecarga(
    umbral: int = UMBRAL_SOBRECARGA_POR_DEFECTO,
) -> dict[str, Any]:
    """Solicita a Data el análisis de riesgo y reenvía errores a la UI."""
    try:
        return _evaluar_riesgo_sobrecarga(umbral)
    except (OSError, UnicodeDecodeError, ValueError) as error:
        logging.exception("No se pudo evaluar la carga académica.")
        return {"error": str(error)}


__all__ = ["evaluar_riesgo_sobrecarga"]
