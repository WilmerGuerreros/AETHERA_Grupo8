"""Herramienta del agente para buscar información pública en la web."""

from core.web_search import buscar_en_web as _buscar_en_web


def buscar_en_web(consulta: str) -> str:
    """Busca información pública en la web para responder consultas actuales."""
    return _buscar_en_web(consulta)
