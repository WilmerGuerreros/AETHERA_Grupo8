from ddgs import DDGS


def buscar_en_web(consulta: str) -> str:
    """Busca información pública en la web para responder consultas actuales."""
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