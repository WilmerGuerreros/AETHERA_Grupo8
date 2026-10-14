"""Evaluador de preguntas de desarrollo para quizzes."""
from __future__ import annotations

import json
import re
from typing import Any

from agent.prompts import (
    QUIZ_DEVELOPMENT_EVALUATION_SYSTEM_PROMPT,
    QUIZ_DEVELOPMENT_EVALUATION_USER_PROMPT,
)
from agent.quiz_evaluation import (
    _contenido_respuesta,
    _crear_historial_evaluacion,
    _parse_json_object,
)


def evaluar_desarrollo(
    motor: Any,
    quiz: dict[str, Any] | str | None = None,
    preguntas_desarrollo: list[dict[str, Any]] | None = None,
    **kwargs,
) -> dict[str, Any]:
    """Evalúa preguntas de desarrollo y devuelve JSON con estructura exacta.

    Soporta llamadas con diferentes firmas para flexibilidad.
    """
    # Permitir firma alternativa: (motor, titulo, respuestas, historial_chat)
    titulo = None
    respuestas = preguntas_desarrollo
    historial_chat = None
    if len(kwargs) == 0 and respuestas is None:
        pass
    # Intentar extraer desde kwargs
    if "titulo" in kwargs:
        titulo = kwargs["titulo"]
    if "respuestas" in kwargs:
        respuestas = kwargs["respuestas"]
    if "preguntas" in kwargs:
        respuestas = kwargs["preguntas"]
    if "historial_chat" in kwargs:
        historial_chat = kwargs["historial_chat"]
    if "historial" in kwargs:
        historial_chat = kwargs["historial"]

    # Si se pasó quiz como dict, extraer info
    if isinstance(quiz, dict):
        titulo = quiz.get("quiz_titulo") or titulo
        if respuestas is None and "paginas" in quiz:
            # intentar extraer desde respuestas_usuario si se pasó así? no directamente
            pass

    if respuestas is None:
        respuestas = []

    payload = json.dumps(
        {"titulo": titulo or "Quiz", "respuestas": respuestas},
        ensure_ascii=False,
    )
    prompt = QUIZ_DEVELOPMENT_EVALUATION_USER_PROMPT.replace("{quiz_payload}", payload)
    response = motor.generar_respuesta(
        historial=_crear_historial_evaluacion(
            historial_chat,
            QUIZ_DEVELOPMENT_EVALUATION_SYSTEM_PROMPT,
            prompt,
        )
    )
    content = _contenido_respuesta(response)
    parsed = _parse_json_object(content)
    evaluaciones = parsed.get("evaluaciones")
    if not isinstance(evaluaciones, list):
        raise ValueError("El modelo no devolvió la lista de evaluaciones esperada.")
    expected_ids = {item["pregunta_id"] for item in respuestas}
    for evaluacion in evaluaciones:
        if not isinstance(evaluacion, dict):
            raise ValueError("El modelo devolvió una evaluación con formato inválido.")
        pregunta_id = evaluacion.get("pregunta_id")
        puntaje_normalizado = evaluacion.get("puntaje_normalizado")
        feedback_especifico = evaluacion.get("feedback_especifico")
        if (
            pregunta_id not in expected_ids
            or not isinstance(puntaje_normalizado, (int, float))
            or isinstance(puntaje_normalizado, bool)
            or not 0.0 <= float(puntaje_normalizado) <= 1.0
            or not isinstance(feedback_especifico, str)
            or not feedback_especifico.strip()
        ):
            raise ValueError("El modelo devolvió una evaluación inválida.")
    return parsed
