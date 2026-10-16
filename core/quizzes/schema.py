"""Fachada pública de validación de quizzes."""

from data.quizzes_domain.schema import (
    crear_quiz,
    quiz_desde_mensaje,
    quiz_desde_resultado_herramienta,
    validar_quiz,
)

__all__ = [
    "crear_quiz",
    "quiz_desde_mensaje",
    "quiz_desde_resultado_herramienta",
    "validar_quiz",
]
