import ollama

modelo: str = "llama3.2:3b"
temperatura: float = 0.6


def generar(historial: list, herramientas: list | None = None) -> dict:
    return ollama.chat(
        model=modelo,
        messages=historial,
        tools=herramientas,
        stream=False,
        options={"temperature": temperatura},
    )