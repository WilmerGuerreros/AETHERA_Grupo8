"""Fachada de configuración usada por el punto de composición."""

import logging

from data.paths import emoji_font_path
from settings import MODELO, OPCIONES_LLM


def configuracion_motor() -> tuple[str, dict[str, object]]:
    """Solicita a Data los parámetros del motor sin exponer su diccionario."""
    return MODELO, dict(OPCIONES_LLM)


def fuente_emoji_color() -> str | None:
    """Pide a Data la ruta de la fuente de emoji a color del sistema.

    Devuelve la ruta como texto o ``None`` cuando no hay fuente disponible;
    cualquier excepción de Data se captura aquí para que la interfaz degrade
    sin emojis en lugar de interrumpir el arranque.
    """
    try:
        ruta = emoji_font_path()
    except OSError:
        logging.exception("No se pudo resolver la fuente de emoji a color.")
        return None
    return str(ruta) if ruta else None
