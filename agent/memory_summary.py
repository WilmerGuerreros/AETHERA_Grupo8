"""Generación de resúmenes mediante el LLM."""

import ollama

from agent.prompts import MEMORY_SUMMARY_SYSTEM_PROMPT
from config import MODELO_RESUMEN


def generar_resumen(contenido_historial: str, modelo: str | None = None) -> str:
    """Resume texto de historial sin realizar operaciones de archivos."""
    respuesta = ollama.chat(
        model=modelo or MODELO_RESUMEN,
        messages=[
            {"role": "system", "content": MEMORY_SUMMARY_SYSTEM_PROMPT},
            {"role": "user", "content": contenido_historial},
        ],
    )
    contenido = respuesta.message.content
    if contenido is None:
        raise RuntimeError("El modelo devolvió una respuesta sin contenido.")
    return contenido
