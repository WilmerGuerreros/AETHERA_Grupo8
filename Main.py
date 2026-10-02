from LLMEngine import LLMEngine
from ChatSession import ChatSession
from tools import LISTA_HERRAMIENTAS


def iniciar_app():
    motor = LLMEngine("llama3.2:3b", 0.6)
    system = """
Eres GuIA, un asistente que ayuda a los estudiantes de 
AETHERA.
"""
    historial = [
        {
            'role': 'system',
            'content': system,
        }
    ]
    chat = ChatSession(motor, historial, LISTA_HERRAMIENTAS)
    chat.iniciar_chat()


if __name__ == "__main__":
    iniciar_app()