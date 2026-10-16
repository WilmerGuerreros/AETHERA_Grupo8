"""Orquestación de la evaluación y cierre de un quiz con el LLM."""

import logging
from typing import Any

from data.quizzes import QuizStore
from data.quizzes_domain.constants import (
    ORIGEN_FINALIZACION_CHAT,
    ORIGEN_FINALIZACION_PANEL,
)

from .schema import validar_quiz
from .scoring import construir_resultado_evaluacion, preparar_respuestas_desarrollo
from .store import (
    QuizManager,
    _resolver_store,
    eliminar_intento,
    guardar_progreso_quiz,
)


def evaluar_quiz(
    motor: Any,
    quiz: dict[str, Any],
    respuestas: dict[str, str],
    historial_chat: list[dict[str, Any]] | None = None,
    store: QuizStore | None = None,
) -> dict[str, Any]:
    """Orquesta evaluación, puntuación y feedback final del LLM."""
    from agent.quiz_evaluation import (
        evaluar_respuestas_desarrollo,
        generar_feedback_resultados,
    )

    quiz = validar_quiz(quiz)
    respuestas = guardar_progreso_quiz(quiz, 0, respuestas, store)
    desarrollo = preparar_respuestas_desarrollo(quiz, respuestas)
    evaluaciones_desarrollo = (
        evaluar_respuestas_desarrollo(
            motor,
            quiz["quiz_titulo"],
            desarrollo,
            historial_chat,
        )
        if any(pagina["tipo"] == "desarrollo" for pagina in quiz["paginas"])
        else []
    )
    resultado = construir_resultado_evaluacion(
        quiz,
        respuestas,
        evaluaciones_desarrollo,
    )
    resultado["feedback_final"] = generar_feedback_resultados(
        motor,
        historial_chat,
        quiz,
        resultado,
    )
    eliminar_intento(quiz["quiz_id"], store)
    return resultado


def finalizar_quiz(
    quiz: dict[str, Any] | str,
    respuestas: dict[str, str] | None = None,
    motor: Any | None = None,
    historial_chat: list[dict[str, Any]] | None = None,
    origen: str = ORIGEN_FINALIZACION_PANEL,
    store: QuizStore | None = None,
    agent_session: Any | None = None,
) -> dict[str, Any]:
    """Finaliza un quiz y devuelve el resultado listo para la UI.

    ``quiz`` puede ser el objeto del quiz o su identificador guardado. Corrige
    las alternativas, envía en segundo plano las respuestas de desarrollo al
    modelo para que sean evaluadas, persiste el resultado final en Data e
    inyecta el resultado como contexto silencioso del agente cuando el quiz
    proviene del chat.
    """
    quiz_obj = (
        QuizManager(store).cargar(quiz)
        if isinstance(quiz, str)
        else validar_quiz(quiz)
    )

    if motor is None:
        raise ValueError("Se requiere un motor para evaluar el quiz.")

    resultado = evaluar_quiz(
        motor,
        quiz_obj,
        dict(respuestas or {}),
        historial_chat,
        store,
    )

    # La persistencia forma parte del resultado: si falla, el error se reporta
    # a la UI en lugar de presentar un cierre que no quedó guardado.
    try:
        _resolver_store(store).guardar_resultado(
            quiz_obj["quiz_id"],
            resultado["porcentaje_total"],
            resultado["retroalimentacion"],
        )
    except (OSError, ValueError) as error:
        logging.exception("No se pudo guardar el resultado final del quiz.")
        raise RuntimeError(
            f"No se pudo guardar el resultado final del quiz: {error}"
        ) from error

    # Solo el chat inyecta el resultado como contexto silencioso del agente.
    if origen == ORIGEN_FINALIZACION_CHAT and agent_session is not None:
        try:
            mensaje = (
                f"[QUIZ] {quiz_obj['quiz_titulo']} - Resultado: "
                f"{resultado.get('porcentaje_total', 0)}%"
            )
            if hasattr(agent_session, "agregar_contexto"):
                agent_session.agregar_contexto(mensaje)
        except (AttributeError, OSError, RuntimeError, TypeError, ValueError) as error:
            logging.exception("No se pudo inyectar el resultado del quiz al agente.")
            raise RuntimeError(
                f"No se pudo actualizar el contexto del chat: {error}"
            ) from error

    return resultado
