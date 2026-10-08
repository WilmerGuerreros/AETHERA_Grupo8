from typing import Callable, Optional

from LLMEngine import LLMEngine


class ChatSession:
    def __init__(
        self,
        motor: LLMEngine,
        historial: list,
        lista_herramientas: dict,
        al_completar_turno: Optional[Callable[[str, str], None]] = None,
    ):
        self.motor = motor
        self.historial = historial
        self.lista_herramientas = lista_herramientas
        self.al_completar_turno = al_completar_turno

#---------------- METODO DE BUCLE DEL CHAT --------------
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
            
            
            self._procesar_respuesta()

#---------------- METODO DE BUCLE DE HERRAMIENTAS ----------------
    def _procesar_respuesta(self):
        """Maneja el stream y la ejecución cíclica de herramientas si el modelo las solicita."""
        usuario = self.historial[-1]["content"]

        while True:
            print("\nAETHERA> ", end="", flush=True)
            
            texto_completo = ""
            herramientas_solicitadas = []

            herramientas_para_ollama = list(self.lista_herramientas.values())

            # Llamamos al generador pasando el historial y la LISTA de herramientas
            flujo_respuesta = self.motor.generar_stream(
                historial=self.historial,
                herramientas=herramientas_para_ollama
            )

            for fragmento in flujo_respuesta:
                msg = fragmento.get('message', {})
                
                # Imprimir texto parcial si viene en el fragmento
                contenido = msg.get('content', '')
                if contenido:
                    print(contenido, end="", flush=True)
                    texto_completo += contenido
                
                # Detectar si el fragmento contiene llamadas a herramientas
                if 'tool_calls' in msg and msg['tool_calls']:
                    herramientas_solicitadas.extend(msg['tool_calls'])
                
            print()  # Salto de línea al terminar el stream de este turno

            # 2. Registrar la respuesta del asistente en el historial
            mensaje_asistente = {'role': 'assistant', 'content': texto_completo}
            if herramientas_solicitadas:
                mensaje_asistente['tool_calls'] = herramientas_solicitadas
            
            self.historial.append(mensaje_asistente)

            # 3. Si el modelo no pidió ninguna herramienta, terminamos el turno
            if not herramientas_solicitadas:
                if self.al_completar_turno is not None:
                    self.al_completar_turno(usuario, texto_completo)
                break

            # 4. Si pidió herramientas, las ejecutamos en local
            for tool_call in herramientas_solicitadas:
                nombre_fn = tool_call['function']['name']
                argumentos = tool_call['function']['arguments']

                print(f"🛠️ [Ejecutando herramienta '{nombre_fn}' con argumentos: {argumentos}]")

                if nombre_fn in self.lista_herramientas:
                    try:
                        # Ejecutar la función pasando los argumentos desempaquetados
                        resultado = self.lista_herramientas[nombre_fn](**argumentos)
                    except Exception as e:
                        resultado = f"Error al ejecutar la herramienta: {str(e)}"
                else:
                    resultado = f"Error: La herramienta '{nombre_fn}' no está registrada."

                # 5. Agregar el resultado de la herramienta al historial
                self.historial.append({
                    'role': 'tool',
                    'content': str(resultado),
                    'name': nombre_fn
                })

            # El bucle `while True` vuelve a ejecutarse automáticamente para que el LLM
            # reciba el resultado en el historial y genere la respuesta explicativa final.