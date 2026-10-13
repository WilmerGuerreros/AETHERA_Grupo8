"""Evaluación generativa de respuestas abiertas de quizzes."""

import json
import re
from typing import Any

from agent.prompts import (
    QUIZ_EVALUATION_SYSTEM_PROMPT,
    QUIZ_EVALUATION_USER_PROMPT,
)


def evaluar_respuestas_desarrollo(
    motor: Any,
    titulo: str,
    respuestas: list[dict[str, str]],
) -> list[dict[str, Any]]:
    """Evalúa respuestas abiertas mediante el LLM y valida su respuesta."""
    payload = json.dumps(
        {"titulo": titulo, "respuestas": respuestas},
        ensure_ascii=False,
    )
    prompt = QUIZ_EVALUATION_USER_PROMPT.replace("{quiz_payload}", payload)
    response = motor.generar_respuesta(
        historial=[
            {"role": "system", "content": QUIZ_EVALUATION_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ]
    )
    message = getattr(response, "message", None)
    content = (
        getattr(message, "content", "")
        if message is not None
        else response.get("message", {}).get("content", "")
    )
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
        porcentaje = evaluacion.get("porcentaje")
        feedback = evaluacion.get("retroalimentacion")
        if (
            pregunta_id not in expected_ids
            or not isinstance(porcentaje, (int, float))
            or isinstance(porcentaje, bool)
            or not 0 <= porcentaje <= 100
            or not isinstance(feedback, str)
            or not feedback.strip()
            or pregunta_id in evaluaciones_por_id
        ):
            raise ValueError("El modelo devolvió una evaluación inválida.")
        evaluaciones_por_id[pregunta_id] = {
            "pregunta_id": pregunta_id,
            "porcentaje": round(porcentaje),
            "retroalimentacion": feedback.strip(),
        }
    if set(evaluaciones_por_id) != expected_ids:
        raise ValueError("El modelo no evaluó todas las respuestas de desarrollo.")
    return [evaluaciones_por_id[item["pregunta_id"]] for item in respuestas]


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
