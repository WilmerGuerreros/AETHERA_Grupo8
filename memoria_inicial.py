from retomar_memoria_escritura import (
    inicializar_memoria,
    obtener_ultimas_interacciones,
    obtener_ultimo_resumen,
)


numero_seccion, contador_mensajes = inicializar_memoria()
mensajes = [
    {
        "role": "system",
        "content": """
Eres Aethera, un agente de acompañamiento académico.
Ayuda al estudiante a organizarse, comprender su carga académica y prepararse para sus evaluaciones.
No eres un profesional de salud: no diagnostiques, no inventes información ni especules sin bases sólidas.
Utiliza la memoria recuperada como contexto cuando sea pertinente.
""",
    }
]

resumen_anterior = obtener_ultimo_resumen(numero_seccion)
if resumen_anterior:
    mensajes.append({
        "role": "system",
        "content": f"Memoria de largo plazo recuperada:\n{resumen_anterior}",
    })

ultimas_interacciones = obtener_ultimas_interacciones(numero_seccion, cantidad=4)
if ultimas_interacciones:
    contexto_reciente = "MEMORIA RECIENTE RECUPERADA:\n\n"
    for interaccion in ultimas_interacciones:
        contexto_reciente += (
            f"Usuario: {interaccion['usuario']}\n"
            f"Aethera: {interaccion['aethera']}\n\n"
        )
    mensajes.append({"role": "system", "content": contexto_reciente})