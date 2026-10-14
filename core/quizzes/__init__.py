"""Reglas, sesiones, persistencia y orquestación de quizzes educativos.

La fachada expone el contrato estable de ``core.quizzes``; la estructura
internamente se agrupa en módulos por responsabilidad:

- ``schema``: construcción, validación y extracción del esquema del quiz.
- ``session``: sesión en memoria de un intento.
- ``scoring``: cálculo de puntajes y resúmenes.
- ``store``: persistencia del avance y de los quizzes en Data.
- ``evaluation``: evaluación y cierre del quiz con el LLM.
"""

from .evaluation import evaluar_quiz, finalizar_quiz
from .schema import (
    crear_quiz,
    quiz_desde_mensaje,
    quiz_desde_resultado_herramienta,
    validar_quiz,
)
from .scoring import (
    construir_resultado_evaluacion,
    preparar_respuestas_desarrollo,
    resumir_quiz,
)
from .session import QuizSession, evaluar_respuesta_alternativa
from .store import (
    QuizManager,
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
    "QuizSession",
    "cargar_intento",
    "construir_resultado_evaluacion",
    "crear_quiz",
    "eliminar_intento",
    "evaluar_quiz",
    "evaluar_respuesta_alternativa",
    "finalizar_quiz",
    "guardar_intento",
    "guardar_progreso_quiz",
    "guardar_quiz",
    "listar_quices",
    "preparar_respuestas_desarrollo",
    "quiz_desde_mensaje",
    "quiz_desde_resultado_herramienta",
    "resumir_quiz",
    "seleccionar_respuesta_alternativa",
    "validar_quiz",
]
