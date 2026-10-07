from LLMEngine import LLMEngine
from ChatSession import ChatSession
from tools import LISTA_HERRAMIENTAS


def iniciar_app():
    configuracion = {
        'temperature': 0.2,
        'num_ctx': 8196 #2^n
    }
    
    motor = LLMEngine("nemotron-3-super:cloud", configuracion)
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


