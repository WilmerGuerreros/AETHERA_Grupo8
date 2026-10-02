import ollama

modelo: str = "llama3.2:3b"
temperatura: float = 0
limiteTokens: int = 0
stream: bool = False

tools: list = []

systemPrompt: str = """
"""

historial: list = []

def iniciar_chat():
    while(True):
        usuario: str = input("> ")

        if usuario == "salir":
            break

        historial.append({'role': 'user', 'content': usuario})

        respuesta = ollama.chat(
            model = modelo,
            messages = historial,
            stream = stream
        )

        historial.append({'role':'assistant', 'content': respuesta['message']['content']})

        print(respuesta['message']['content'])

iniciar_chat()


