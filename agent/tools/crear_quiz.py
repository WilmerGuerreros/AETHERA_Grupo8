"""Herramienta del agente para validar y guardar quizzes educativos."""

from typing import Any

from core.quizzes import crear_quiz as construir_quiz
from core.quizzes import guardar_quiz


def crear_quiz(title: str, pages: list[list[Any]]) -> str:
    """Create a quiz and return its data to enable restoring it from the history.

Args:
    title: Quiz title.
    pages: Ordered list of questions. Each question uses one of these formats:
        - Multiple Choice: ['alternative', question, [options...],
          correct_answer_text, explanation_of_why_it_is_correct].
          The explanation must be clear and specific; it will be shown as
          feedback when the student answers.
        - Open-ended / Development: ['develope', question, guiding_guidelines, rubric_keywords]
"""
    try:
        quiz = construir_quiz(title, pages)
        guardar_quiz(quiz)
        return repr({"quiz_data": quiz})
    except (ValueError, OSError) as error:
        return f"No se pudo crear el quiz: {error}"
