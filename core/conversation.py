"""Coordinación entre el agente y la persistencia de conversaciones."""

from collections.abc import Callable, Iterator
from typing import Any

from agent.session import AgentSession
from agent.tools.registro import Herramienta
from agent.llm import LLMEngine


class Conversacion:
    """Orquesta turnos del agente y publica eventos sin conocer la UI."""

    def __init__(
        self,
        motor: LLMEngine,
        historial: list,
        registro_herramientas: dict[str, Herramienta],
        guardar_interaccion: Callable[[str, str, str], None],
    ):
        self.motor = motor
        self.historial = historial
        self._guardar_interaccion = guardar_interaccion
        self._sesion = AgentSession(motor, historial, registro_herramientas)

    def evaluar_quiz(
        self,
        quiz: dict[str, Any],
        respuestas: dict[str, str],
    ) -> dict[str, Any]:
        """Evalúa un quiz usando el historial actual como contexto del agente."""
        from core.quizzes import evaluar_quiz

        return evaluar_quiz(
            self.motor,
            quiz,
            respuestas,
            list(self.historial),
        )

    def procesar_turno(
        self, usuario: str
    ) -> Iterator[tuple[str, Any]]:
        """Devuelve texto/estado del agente y persiste el turno completo."""
        for tipo_evento, contenido in self._sesion.procesar_turno(usuario):
            if tipo_evento == "complete":
                usuario_completado, respuesta = contenido
                self._guardar_interaccion(
                    usuario_completado,
                    respuesta,
                    self.motor.modelo,
                )
            yield tipo_evento, contenido
