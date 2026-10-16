"""Punto de composición de Aethera.

Es el único lugar que conoce todas las capas: crea el motor de lenguaje, el
administrador de chats y el registro de herramientas, y los inyecta en la
interfaz de escritorio.
"""

from agent.llm import LLMEngine
from agent.prompts import SYSTEM_PROMPT
from agent.tools import REGISTRO_HERRAMIENTAS
from core.chat_manager import ChatManager
from core.configuration import configuracion_motor


def iniciar_aplicacion() -> None:
    """Ensambla dependencias compartidas y abre la interfaz de escritorio."""
    modelo, opciones = configuracion_motor()
    motor = LLMEngine(modelo, opciones)
    chats = ChatManager(
        motor,
        REGISTRO_HERRAMIENTAS,
        SYSTEM_PROMPT,
    )

    from ui.desktop_app import iniciar_app_escritorio

    iniciar_app_escritorio(
        motor,
        [],
        REGISTRO_HERRAMIENTAS,
        None,
        chat_manager=chats,
    )
