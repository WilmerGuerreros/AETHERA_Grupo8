"""Fachada pública de sesiones de intento de quiz."""

from data.quizzes_domain.session import QuizSession, evaluar_respuesta_alternativa

__all__ = ["QuizSession", "evaluar_respuesta_alternativa"]
