"""Búsqueda de información pública en la web."""

from ddgs import DDGS


def buscar_en_web(consulta: str) -> str:
    """Devuelve resultados públicos de la web para una consulta."""
    consulta = consulta.strip()
    if not consulta:
        return "Escribe qué información quieres buscar en la web."

    resultados = DDGS().text(consulta, max_results=5)
    if not resultados:
        return f"No se encontraron resultados para: {consulta}"

    return "\n\n".join(
        f"{resultado.get('title', 'Sin título')}\n"
        f"{resultado.get('href', '')}\n"
        f"{resultado.get('body', '')}"
        for resultado in resultados
    )
