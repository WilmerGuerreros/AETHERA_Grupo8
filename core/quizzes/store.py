"""Fachada pública de las operaciones de quizzes en Data."""

from data.quizzes_domain.store import (
    QuizManager,
    _resolver_store,
    cargar_intento,
    eliminar_intento,
    guardar_intento,
    guardar_progreso_quiz,
    guardar_quiz,
    listar_quices,
    seleccionar_respuesta_alternativa,
)

__all__ = [
    "QuizManager",
    "_resolver_store",
    "cargar_intento",
    "eliminar_intento",
    "guardar_intento",
    "guardar_progreso_quiz",
    "guardar_quiz",
    "listar_quices",
    "seleccionar_respuesta_alternativa",
]
