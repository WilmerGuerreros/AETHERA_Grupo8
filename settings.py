"""Valores de configuración del modelo y de la memoria.

Reúne los modelos de Ollama, sus opciones de generación y el tamaño de las
secciones de memoria. No administra archivos: eso corresponde a ``data``.
"""

MODELO = "nemotron-3-ultra:cloud"
MODELO_RESUMEN = "nemotron-3-super:cloud"
OPCIONES_LLM = {
    "temperature": 0.3,
    "num_ctx": 200000,
    "think": "low",
}
MAX_MENSAJES_POR_SECCION = 20
