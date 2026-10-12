from .historial import inicializar_memoria, obtener_ultimas_interacciones
from .resumen import obtener_ultimo_resumen


numero_seccion, contador_mensajes = inicializar_memoria()
mensajes = [{'':''}]

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