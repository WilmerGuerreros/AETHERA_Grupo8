import ollama
from typing import Any, Dict, Iterator, List, Optional


def generar_stream(
    self,
    historial: List[Dict[str, Any]],
    herramientas: Optional[List[Any]] = None,
) -> Iterator[Any]:
    """Envía el historial a Ollama y devuelve fragmentos de respuesta."""
    return ollama.chat(
        model=self.modelo,
        messages=historial,
        tools=herramientas,
        stream=True,
        options=self.configuracion,
    )