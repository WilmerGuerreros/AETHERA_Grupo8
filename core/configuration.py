"""Fachada de configuración usada por el punto de composición."""

from data.settings import MODELO, OPCIONES_LLM


def configuracion_motor() -> tuple[str, dict[str, object]]:
    """Solicita a Data los parámetros del motor sin exponer su diccionario."""
    return MODELO, dict(OPCIONES_LLM)
