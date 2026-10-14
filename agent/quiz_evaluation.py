"""Evaluación generativa de respuestas abiertas de quizzes."""

import json
import re
from typing import Any

from agent.prompts import (
    QUIZ_EVALUATION_SYSTEM_PROMPT,
    QUIZ_EVALUATION_USER_PROMPT,
    QUIZ_RESULTS_FEEDBACK_SYSTEM_PROMPT,
    QUIZ_RESULTS_FEEDBACK_USER_PROMPT,
)


def evaluar_respuestas_desarrollo(
    motor: Any,
    titulo: str,
    respuestas: list[dict[str, str]],
    historial_chat: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Evalúa respuestas abiertas mediante el LLM y valida su respuesta."""
    payload = json.dumps(
        {"titulo": titulo, "respuestas": respuestas},
        ensure_ascii=False,
    )
    prompt = QUIZ_EVALUATION_USER_PROMPT.replace("{quiz_payload}", payload)
    response = motor.generar_respuesta(
        historial=_crear_historial_evaluacion(
            historial_chat,
            QUIZ_EVALUATION_SYSTEM_PROMPT,
            prompt,
        )
    )
    content = _contenido_respuesta(response)
    parsed = _parse_json_object(content)
    evaluaciones = parsed.get("evaluaciones")
    expected_ids = {item["pregunta_id"] for item in respuestas}
    if not isinstance(evaluaciones, list):
        raise ValueError("El modelo no devolvió la lista de evaluaciones esperada.")
    evaluaciones_por_id = {}
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
            or pregunta_id in evaluaciones_por_id
        ):
            raise ValueError("El modelo devolvió una evaluación inválida.")
        evaluaciones_por_id[pregunta_id] = {
            "pregunta_id": pregunta_id,
            "puntaje_normalizado": float(puntaje_normalizado),
            "feedback_especifico": feedback_especifico.strip(),
        }
    if set(evaluaciones_por_id) != expected_ids:
        raise ValueError("El modelo no evaluó todas las respuestas de desarrollo.")
    return [evaluaciones_por_id[item["pregunta_id"]] for item in respuestas]


def generar_feedback_resultados(
    motor: Any,
    historial_chat: list[dict[str, Any]] | None,
    quiz: dict[str, Any],
    resultado: dict[str, Any],
) -> str:
    """Pide al agente un mensaje contextualizado con los resultados finales."""
    payload = json.dumps(
        {"quiz": quiz, "resultados": resultado},
        ensure_ascii=False,
    )
    prompt = QUIZ_RESULTS_FEEDBACK_USER_PROMPT.replace(
        "{results_payload}", payload
    )
    response = motor.generar_respuesta(
        historial=_crear_historial_evaluacion(
            historial_chat,
            QUIZ_RESULTS_FEEDBACK_SYSTEM_PROMPT,
            prompt,
        )
    )
    feedback = _contenido_respuesta(response).strip()
    if not feedback:
        raise ValueError("El modelo no devolvió retroalimentación para el quiz.")
    return feedback


def _crear_historial_evaluacion(
    historial_chat: list[dict[str, Any]] | None,
    instruccion: str,
    prompt: str,
) -> list[dict[str, Any]]:
    contexto = [
        dict(mensaje)
        for mensaje in historial_chat or []
        if mensaje.get("role") != "system"
    ]
    return [
        {"role": "system", "content": instruccion},
        *contexto,
        {"role": "user", "content": prompt},
    ]


def _contenido_respuesta(response: Any) -> str:
    message = getattr(response, "message", None)
    if message is not None:
        content = getattr(message, "content", "")
    elif isinstance(response, dict):
        content = response.get("message", {}).get("content", "")
    else:
        content = ""
    if not isinstance(content, str):
        raise ValueError("El modelo devolvió contenido con formato inválido.")
    return content


def _parse_json_object(texto: str) -> dict[str, Any]:
    resultado = _parse_json_value(texto)
    if not isinstance(resultado, dict):
        raise ValueError("El modelo no devolvió un objeto JSON.")
    return resultado


def _parse_json_value(texto: str) -> Any:
    decoder = json.JSONDecoder()
    for match in re.finditer(r"[\[{]", texto):
        try:
            return decoder.raw_decode(texto[match.start():])[0]
        except json.JSONDecodeError:
            continue
    raise ValueError("El modelo no devolvió JSON válido para evaluar.")
