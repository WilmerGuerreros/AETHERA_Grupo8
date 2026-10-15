"""Punto de composición de Aethera.

Es el único lugar que conoce todas las capas: crea el motor de lenguaje, el
administrador de chats y el registro de herramientas, y los inyecta en la
interfaz de escritorio.
"""

from agent.llm import LLMEngine
from agent.prompts import SYSTEM_PROMPT
from agent.tools import REGISTRO_HERRAMIENTAS
from config import MODELO, OPCIONES_LLM
from core.chat_manager import ChatManager


def iniciar_aplicacion() -> None:
    """Ensambla dependencias compartidas y abre la interfaz de escritorio."""
    motor = LLMEngine(MODELO, dict(OPCIONES_LLM))
    chats = ChatManager(
        motor,
        REGISTRO_HERRAMIENTAS,
        SYSTEM_PROMPT,
    )

    from UI.desktop_app import iniciar_app_escritorio

    iniciar_app_escritorio(
        motor,
        [],
        REGISTRO_HERRAMIENTAS,
        None,
        chat_manager=chats,
    )
