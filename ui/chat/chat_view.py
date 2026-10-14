"""Orquestación de los componentes de la sección de chat."""

from .components import ChatHeader, ChatHistory, ChatInput, ChatQuizView
from .logica import ChatLogic


class ChatSection(ChatHeader, ChatHistory, ChatQuizView, ChatInput, ChatLogic):
    def _show_chat(self):
        self._render_chat_header()
        self._render_chat_history()
        self._render_chat_input()
        if self.chat_store.ocupado:
            # El turno siguió corriendo fuera de la página: retomamos el aviso.
            self._typing_phase = 0
            self._pulse_typing_indicator()
