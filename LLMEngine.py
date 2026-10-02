import ollama
from typing import List, Dict, Any, Optional, Iterator


class LLMEngine:
    def __init__(self, modelo: str, temperatura: float):
        self.modelo = modelo
        self.temperatura = temperatura

    def generar_stream(
            self, 
            historial: List[Dict[str, Any]], 
            herramientas: Optional[List[Any]] = None
            ) -> Iterator[Any]:
        """Envía los datos a Ollama y devuelve un flujo (stream) de fragmentos en tiempo real."""
        
        flujo = ollama.chat(
            model=self.modelo,
            messages=historial,
            tools=herramientas,
            stream=True, # ¡La magia ocurre aquí!
            options={
                "temperature": self.temperatura
            }
        )
        
        return flujo