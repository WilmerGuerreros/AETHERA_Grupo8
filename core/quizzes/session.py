"""Sesión en memoria de un intento de quiz."""

import json
from typing import Any

from .schema import _validar_texto, validar_quiz


class QuizSession:
    """Mantiene en memoria las respuestas de un intento de quiz."""

    def __init__(self, quiz: dict[str, Any]):
        self.quiz = validar_quiz(quiz)
        self._respuestas_desarrollo: dict[str, str] = {}
        self._paginas = {pagina["id"]: pagina for pagina in self.quiz["paginas"]}

    @property
    def respuestas_desarrollo(self) -> dict[str, str]:
        """Devuelve una copia de las respuestas abiertas recibidas hasta ahora."""
        return self._respuestas_desarrollo.copy()

    def responder_alternativa(
        self, pregunta_id: str, respuesta: str
    ) -> dict[str, bool | str]:
        """Evalúa una alternativa y devuelve su corrección y retroalimentación."""
        pagina = self._obtener_pregunta(pregunta_id, "alternativa")
        if not isinstance(respuesta, str):
            raise ValueError("La respuesta debe ser una clave de alternativa.")
        respuesta = respuesta.strip()
        retroalimentacion = pagina["retroalimentacion"]
        if respuesta not in pagina["alternativas"]:
            raise ValueError(
                f"La opción '{respuesta}' no existe para la pregunta '{pregunta_id}'."
            )
        return {
            "correcta": respuesta == pagina["respuesta_correcta"],
            "retroalimentacion": retroalimentacion[respuesta],
        }

    def guardar_respuesta_desarrollo(
        self, pregunta_id: str, respuesta: str
    ) -> None:
        """Guarda o reemplaza la respuesta del alumno a una pregunta abierta."""
        self._obtener_pregunta(pregunta_id, "desarrollo")
        respuesta_validada = _validar_texto(
            respuesta, f"respuesta de la pregunta '{pregunta_id}'"
        )
        self._respuestas_desarrollo[pregunta_id] = respuesta_validada

    def preparar_evaluacion(self) -> str:
        """Consolida el quiz y respuestas abiertas en un JSON para el LLM."""
        respuestas = [
            {
                "pregunta_id": pagina["id"],
                "pregunta": pagina["pregunta"],
                "respuesta_alumno": self._respuestas_desarrollo[pagina["id"]],
                "guia_evaluacion": pagina["guia_evaluacion"],
                "respuesta_sugerida": pagina["respuesta_sugerida"],
            }
            for pagina in self.quiz["paginas"]
            if pagina["tipo"] == "desarrollo"
            and pagina["id"] in self._respuestas_desarrollo
        ]
        return json.dumps(
            {
                "quiz": self.quiz,
                "respuestas_desarrollo": respuestas,
            },
            ensure_ascii=False,
            indent=2,
        )

    def _obtener_pregunta(self, pregunta_id: str, tipo: str) -> dict[str, Any]:
        if not isinstance(pregunta_id, str) or pregunta_id not in self._paginas:
            raise ValueError(f"No existe una pregunta con id '{pregunta_id}'.")
        pagina = self._paginas[pregunta_id]
        if pagina["tipo"] != tipo:
            raise ValueError(
                f"La pregunta '{pregunta_id}' no es de tipo '{tipo}'."
            )
        return pagina


def evaluar_respuesta_alternativa(
    quiz: dict[str, Any],
    pregunta_id: str,
    respuesta: str,
) -> dict[str, bool | str]:
    """Devuelve la corrección de una alternativa para una pregunta."""
    return QuizSession(quiz).responder_alternativa(pregunta_id, respuesta)
