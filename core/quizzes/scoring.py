"""Fachada pública de cálculos de quizzes."""

from data.quizzes_domain.scoring import (
    construir_resultado_evaluacion,
    preparar_respuestas_desarrollo,
    resumir_quiz,
)

__all__ = [
    "construir_resultado_evaluacion",
    "preparar_respuestas_desarrollo",
    "resumir_quiz",
]
