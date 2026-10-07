import os
import requests 


def buscar_internet(consulta: str) -> str:
    """
    Busca información actualizada en Internet.
    
    Args:
        consulta: Texto de búsqueda que se enviará al buscador.

    Returns:
        Resultados resumidos de la búsqueda.
    """

    api_key = os.getenv("BRAVE_SEARCH_API_KEY")

    if not api_key:
        return "ERROR: No se encontró la API key de Brave Search."

    url = "https://api.search.brave.com/res/v1/web/search"

    headers = {
        "Accept": "application/json",
        "X-Subscription-Token": api_key
    }

    params = {
        "q": consulta,
        "count": 5,
        "country": "PE",
        "search_lang": "es"
    }

    try:

        respuesta = requests.get(
            url,
            headers=headers,
            params=params,
            timeout=10
        )

        respuesta.raise_for_status()

        datos = respuesta.json()

        resultados = datos.get("web", {}).get("results", [])

        if not resultados:
            return "No encontré resultados relevantes."

        salida = []

        for i, resultado in enumerate(resultados, start=1):

            titulo = resultado.get("title", "Sin título")
            url_resultado = resultado.get("url", "")
            descripcion = resultado.get("description", "")

            salida.append(
                f"{i}. {titulo}\n"
                f"URL: {url_resultado}\n"
                f"Descripción: {descripcion}"
            )

        return "\n\n".join(salida)

    except requests.RequestException as e:

        return f"ERROR al buscar en Internet: {e}"