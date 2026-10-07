import ollama
from typing import List, Dict, Any, Optional, Iterator

from generar_stream import generar_stream as _generar_stream


class LLMEngine:
    def __init__(self, modelo: str, configuracion: dict):
        self.modelo = modelo
        self.configuracion = configuracion

    generar_stream = _generar_stream