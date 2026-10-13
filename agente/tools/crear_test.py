"""Herramienta del agente para validar y guardar quizzes educativos."""

from typing import Any

from dominio.quices import QuizManager
from dominio.quices.creacion import crear_quiz


def crear_test(title: str, pages: list[list[Any]]) -> str:
    """
    Crea y guarda un quiz.

    Args:
        title: Título del quiz.
        pages: Lista ordenada de preguntas. Cada pregunta usa uno de estos formatos:
            - Alternativas: ['alternative', pregunta, [opciones...], texto_respuesta_correcta]
            - Desarrollo: ['develope', pregunta, guia_orientativa, palabras_clave_rubrica]
    """
    try:
        datos_quiz = crear_quiz(title, pages)
        QuizManager().guardar(datos_quiz)
        return "Quiz creado y guardado correctamente."
    except (ValueError, OSError) as error:
        return f"No se pudo crear el quiz: {error}"
