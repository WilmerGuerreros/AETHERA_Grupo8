from typing import Callable, Optional

from .LLMEngine import LLMEngine


class AgentSession:
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

    def procesar_turno(
        self,
        usuario: str,
        al_emitir_texto: Callable[[str], None],
        al_actualizar_estado: Callable[[str], None],
    ):
        self.historial.append({"role": "user", "content": usuario})
        self._procesar_respuesta(usuario, al_emitir_texto, al_actualizar_estado)

    def _procesar_respuesta(
        self,
        usuario: str,
        al_emitir_texto: Callable[[str], None],
        al_actualizar_estado: Callable[[str], None],
    ):
        """Maneja el stream y la ejecución cíclica de herramientas si el modelo las solicita."""

        while True:
            texto_completo = ""
            herramientas_solicitadas = []

            herramientas_para_ollama = list(self.lista_herramientas.values())

            flujo_respuesta = self.motor.generar_stream(
                historial=self.historial,
                herramientas=herramientas_para_ollama,
            )

            for fragmento in flujo_respuesta:
                msg = fragmento.get('message', {})
                
                contenido = msg.get('content', '')
                if contenido:
                    al_emitir_texto(contenido)
                    texto_completo += contenido
                
                if 'tool_calls' in msg and msg['tool_calls']:
                    herramientas_solicitadas.extend(msg['tool_calls'])
                
            mensaje_asistente = {'role': 'assistant', 'content': texto_completo}
            if herramientas_solicitadas:
                mensaje_asistente['tool_calls'] = herramientas_solicitadas
            
            self.historial.append(mensaje_asistente)

            if not herramientas_solicitadas:
                if self.al_completar_turno is not None:
                    self.al_completar_turno(usuario, texto_completo)
                break

            for tool_call in herramientas_solicitadas:
                nombre_fn = tool_call['function']['name']
                argumentos = tool_call['function']['arguments']

                estado = f"Consultando {nombre_fn.replace('_', ' ')}..."
                al_actualizar_estado(estado)

                if nombre_fn in self.lista_herramientas:
                    try:
                        # Ejecutar la función pasando los argumentos desempaquetados
                        resultado = self.lista_herramientas[nombre_fn](**argumentos)
                    except Exception as e:
                        resultado = f"Error al ejecutar la herramienta: {str(e)}"
                else:
                    resultado = f"Error: La herramienta '{nombre_fn}' no está registrada."

                self.historial.append({
                    'role': 'tool',
                    'content': str(resultado),
                    'name': nombre_fn
                })
