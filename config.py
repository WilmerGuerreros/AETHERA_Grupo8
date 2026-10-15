"""Configuración central de Aethera.

Reúne en un solo lugar los valores que suelen ajustarse: los modelos de Ollama,
las opciones de generación y el tamaño de las secciones de memoria.
"""

# Modelo compartido por todas las conversaciones de Aethera.
MODELO = "nemotron-3-super:cloud"

# Modelo más económico usado para resumir la memoria de largo plazo.
MODELO_RESUMEN = "nemotron-3-super:cloud"

# Opciones que se envían a Ollama en cada generación de la conversación.
OPCIONES_LLM = {
    "temperature": 0.3,
    "num_ctx": 200000,#solo para cloud.
    "think": "low",
}

# Cantidad de interacciones que se acumulan antes de resumir y sellar una sección.
MAX_MENSAJES_POR_SECCION = 20
