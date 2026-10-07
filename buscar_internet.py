import os

import requests


def buscar_internet(consulta: str) -> str:
    """Busca información actualizada usando la API de Brave Search."""
    api_key = os.getenv("BRAVE_SEARCH_API_KEY")
    if not api_key:
        return "ERROR: No se encontró la API key de Brave Search."

    url = "https://api.search.brave.com/res/v1/web/search"
    headers = {
        "Accept": "application/json",
        "X-Subscription-Token": api_key,
    }
    params = {
        "q": consulta,
        "count": 5,
        "country": "PE",
        "search_lang": "es",
    }

    try:
        respuesta = requests.get(url, headers=headers, params=params, timeout=10)
        respuesta.raise_for_status()
        resultados = respuesta.json().get("web", {}).get("results", [])
        if not resultados:
            return "No encontré resultados relevantes."

        salida = []
        for numero, resultado in enumerate(resultados, start=1):
            salida.append(
                f"{numero}. {resultado.get('title', 'Sin título')}\n"
                f"URL: {resultado.get('url', '')}\n"
                f"Descripción: {resultado.get('description', '')}"
            )
        return "\n\n".join(salida)
    except requests.RequestException as error:
        return f"ERROR al buscar en Internet: {error}"