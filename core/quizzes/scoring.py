"""Cálculo de puntajes, resúmenes y presentación de resultados de un quiz."""

from typing import Any

from .schema import validar_quiz
from .session import QuizSession


def resumir_quiz(quiz: dict[str, Any]) -> dict[str, int]:
    """Devuelve el conteo de preguntas por tipo para presentar un quiz."""
    quiz = validar_quiz(quiz)
    alternativas = sum(
        pagina["tipo"] == "alternativa" for pagina in quiz["paginas"]
    )
    return {
        "alternativas": alternativas,
        "desarrollo": len(quiz["paginas"]) - alternativas,
    }


def preparar_respuestas_desarrollo(
    quiz: dict[str, Any],
    respuestas: dict[str, str],
) -> list[dict[str, str]]:
    """Devuelve todas las preguntas abiertas junto con su respuesta, si existe."""
    quiz_validado = validar_quiz(quiz)
    desarrollo = []
    for pagina in quiz_validado["paginas"]:
        if pagina["tipo"] != "desarrollo":
            continue
        respuesta = respuestas.get(pagina["id"], "")
        desarrollo.append(
            {
                "pregunta_id": pagina["id"],
                "pregunta": pagina["pregunta"],
                "respuesta_alumno": respuesta,
                "guia_evaluacion": pagina["guia_evaluacion"],
                "respuesta_sugerida": pagina["respuesta_sugerida"],
            }
        )
    return desarrollo


def construir_resultado_evaluacion(
    quiz: dict[str, Any],
    respuestas: dict[str, str],
    evaluaciones_desarrollo: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Aplica reglas de corrección y calcula puntajes del quiz.

    Devuelve el contrato canónico de resultados: ``porcentaje_total``,
    ``porcentaje_alternativas``, ``porcentaje_desarrollo`` y una lista
    ``retroalimentacion`` con un elemento por pregunta en el orden del quiz.
    Cada elemento usa la forma ``{pregunta_id, tipo, correcta, porcentaje,
    retroalimentacion}`` (``correcta`` es ``None`` en desarrollo).
    """
    quiz = validar_quiz(quiz)
    session = QuizSession(quiz)
    total_alternativas = sum(
        pagina["tipo"] == "alternativa" for pagina in quiz["paginas"]
    )
    total_desarrollo = len(quiz["paginas"]) - total_alternativas

    evaluaciones_desarrollo = evaluaciones_desarrollo or []
    if total_desarrollo and len(evaluaciones_desarrollo) != total_desarrollo:
        raise ValueError("Faltan evaluaciones para las preguntas de desarrollo.")
    desarrollo_por_id = {
        evaluacion["pregunta_id"]: evaluacion
        for evaluacion in evaluaciones_desarrollo
    }

    retroalimentacion = []
    correctas_alternativas = 0
    puntos_totales = 0
    desarrollo_porcentajes = []
    for pagina in quiz["paginas"]:
        pregunta_id = pagina["id"]
        respuesta = respuestas.get(pregunta_id, "")
        if pagina["tipo"] == "alternativa":
            if respuesta:
                evaluacion = session.responder_alternativa(pregunta_id, respuesta)
                correcta = evaluacion["correcta"]
                feedback = evaluacion["retroalimentacion"]
            else:
                correcta = False
                feedback = "Pregunta sin responder."
            if correcta:
                correctas_alternativas += 1
            puntos_totales += 100 if correcta else 0
            retroalimentacion.append(
                {
                    "pregunta_id": pregunta_id,
                    "tipo": "alternativa",
                    "correcta": correcta,
                    "porcentaje": 100 if correcta else 0,
                    "retroalimentacion": feedback,
                }
            )
        else:
            evaluacion = desarrollo_por_id[pregunta_id]
            porcentaje = round(evaluacion["puntaje_normalizado"] * 100)
            desarrollo_porcentajes.append(porcentaje)
            puntos_totales += porcentaje
            retroalimentacion.append(
                {
                    "pregunta_id": pregunta_id,
                    "tipo": "desarrollo",
                    "correcta": None,
                    "porcentaje": porcentaje,
                    "retroalimentacion": evaluacion["feedback_especifico"],
                }
            )

    return {
        "porcentaje_total": round(puntos_totales / len(quiz["paginas"])),
        "porcentaje_alternativas": (
            round(correctas_alternativas / total_alternativas * 100)
            if total_alternativas
            else None
        ),
        "porcentaje_desarrollo": (
            round(sum(desarrollo_porcentajes) / total_desarrollo)
            if total_desarrollo
            else None
        ),
        "correctas_alternativas": correctas_alternativas,
        "total_alternativas": total_alternativas,
        "retroalimentacion": retroalimentacion,
    }
