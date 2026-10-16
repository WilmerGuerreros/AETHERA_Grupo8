"""Valores de configuración compartidos por el dominio de la aplicación."""

MODELO = "nemotron-3-ultra:cloud"
MODELO_RESUMEN = "nemotron-3-super:cloud"
OPCIONES_LLM = {
    "temperature": 0.3,
    "num_ctx": 200000,
    "think": "low",
}
MAX_MENSAJES_POR_SECCION = 20
