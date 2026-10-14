"""Herramienta del agente para validar y guardar quizzes educativos."""

from typing import Any

from core.quizzes import crear_y_guardar_quiz


def crear_quiz(title: str, pages: list[list[Any]]) -> str:
    """Crea un quiz; incluye una explicación para la respuesta correcta.

    Args:
        title: Título del quiz.
        pages: Lista ordenada de preguntas. Cada pregunta usa uno de estos formatos:
            - Alternativas: ['alternative', pregunta, [opciones...],
              texto_respuesta_correcta, explicación_de_por_qué_es_correcta].
              La explicación debe ser clara y específica; se mostrará como
              retroalimentación cuando el estudiante responda.
            - Desarrollo: ['develope', pregunta, guia_orientativa, palabras_clave_rubrica]
    """
    try:
        crear_y_guardar_quiz(title, pages)
        return "Quiz creado y guardado correctamente."
    except (ValueError, OSError) as error:
        return f"No se pudo crear el quiz: {error}"
