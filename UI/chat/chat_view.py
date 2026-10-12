"""Orquestación de los componentes de la sección de chat."""

from .components import ChatHeader, ChatHistory, ChatInput
from .logica import ChatLogic


class ChatSection(ChatHeader, ChatHistory, ChatInput, ChatLogic):
    def _show_chat(self):
        self._render_chat_header()
        self._render_chat_history()
        self._render_chat_input()
