"""Herramienta del agente para validar y guardar quizzes educativos."""

from typing import Any

from core.quizzes import crear_y_guardar_quiz


def crear_quiz(title: str, pages: list[list[Any]]) -> str:
    """
    Crea y guarda un quiz.

    Args:
        title: Título del quiz.
        pages: Lista ordenada de preguntas. Cada pregunta usa uno de estos formatos:
            - Alternativas: ['alternative', pregunta, [opciones...], texto_respuesta_correcta]
            - Desarrollo: ['develope', pregunta, guia_orientativa, palabras_clave_rubrica]
    """
    try:
        crear_y_guardar_quiz(title, pages)
        return "Quiz creado y guardado correctamente."
    except (ValueError, OSError) as error:
        return f"No se pudo crear el quiz: {error}"
