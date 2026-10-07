from LLMEngine import LLMEngine
from ChatSession import ChatSession
from guardar_historial_con_fecha import guardar_historial
from tools import LISTA_HERRAMIENTAS
from memoria_inicial import mensajes


def iniciar_app():
    configuracion = {
        'temperature': 0.2,
        'num_ctx': 8196 #2^n
    }
    
    motor = LLMEngine("nemotron-3-super:cloud", configuracion)
    chat = ChatSession(
        motor,
        mensajes,
        LISTA_HERRAMIENTAS,
        al_completar_turno=lambda usuario, respuesta: guardar_historial(
            usuario,
            respuesta,
            motor.modelo,
        ),
    )
    chat.iniciar_chat()


if __name__ == "__main__":
    iniciar_app()