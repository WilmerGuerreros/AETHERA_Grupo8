from LLMEngine import LLMEngine


class ChatSession:
    def __init__(
        self,
        motor: LLMEngine,
        historial: list,
        lista_herramientas: dict,
    ):
        self.motor = motor
        self.historial = historial
        self.lista_herramientas = lista_herramientas

    def iniciar_chat(self):
        print(
            """
-------------------------------------
#         CHAT INICIADO             #
-------------------------------------
"""
        )
        while True:
            usuario = input("> ")
            if usuario.strip().lower() in {"salir", "exit", "quit"}:
                print("Chat finalizado.")
                break

            self.historial.append({"role": "user", "content": usuario})
            
            print("GuIA> ", end="", flush=True) # Preparamos el inicio de la línea
            
            texto_completo: str = ""
            flujo_respuesta = self.motor.generar_stream(self.historial)
            
            for fragmento in flujo_respuesta:
                contenido: str = fragmento['message']['content']
                print(contenido, end="", flush=True)
                texto_completo += contenido
                
            print()

            self.historial.append({'role': 'assistant', 'content': texto_completo})