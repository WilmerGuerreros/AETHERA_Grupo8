from collections.abc import Iterator
from typing import Any

from .tools.registro import Herramienta


class AgentSession:
    def __init__(
        self,
        motor: Any,
        historial: list,
        registro_herramientas: dict[str, Herramienta],
    ):
        self.motor = motor
        self.historial = historial
        self.registro_herramientas = registro_herramientas

    def procesar_turno(
        self,
        usuario: str,
    ) -> Iterator[tuple[str, str | tuple[str, str]]]:
        self.historial.append({"role": "user", "content": usuario})
        yield from self._procesar_respuesta(usuario)

    def agregar_contexto(self, mensaje: str) -> None:
        """Agrega un mensaje silencioso al historial del agente."""
        self.historial.append(
            {"role": "system", "content": mensaje, "silent": True}
        )

    def _procesar_respuesta(
        self,
        usuario: str,
    ) -> Iterator[tuple[str, str | tuple[str, str]]]:
        """Maneja el stream y la ejecución cíclica de herramientas si el modelo las solicita."""

        while True:
            texto_completo = ""
            herramientas_solicitadas = []

            herramientas_para_ollama = [
                herramienta.funcion
                for herramienta in self.registro_herramientas.values()
            ]

            flujo_respuesta = self.motor.generar_stream(
                historial=self.historial,
                herramientas=herramientas_para_ollama,
            )

            for fragmento in flujo_respuesta:
                msg = fragmento.get('message', {})
                
                contenido = msg.get('content', '')
                if contenido:
                    yield "token", contenido
                    texto_completo += contenido
                
                if 'tool_calls' in msg and msg['tool_calls']:
                    herramientas_solicitadas.extend(msg['tool_calls'])
                
            mensaje_asistente = {'role': 'assistant', 'content': texto_completo}
            if herramientas_solicitadas:
                mensaje_asistente['tool_calls'] = herramientas_solicitadas
            
            self.historial.append(mensaje_asistente)

            if not herramientas_solicitadas:
                yield "complete", (usuario, texto_completo)
                break

            for tool_call in herramientas_solicitadas:
                nombre_fn = tool_call['function']['name']
                argumentos = tool_call['function']['arguments']

                estado = f"Consultando {nombre_fn.replace('_', ' ')}..."
                yield "status", estado

                if nombre_fn in self.registro_herramientas:
                    try:
                        # Ejecutar la función pasando los argumentos desempaquetados
                        resultado = self.registro_herramientas[nombre_fn].funcion(
                            **argumentos
                        )
                    except Exception as e:
                        resultado = f"Error al ejecutar la herramienta: {str(e)}"
                else:
                    resultado = f"Error: La herramienta '{nombre_fn}' no está registrada."

                self.historial.append({
                    'role': 'tool',
                    'content': str(resultado),
                    'name': nombre_fn
                })
