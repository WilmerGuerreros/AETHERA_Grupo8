"""Generación y consulta de resúmenes de memoria."""

import ollama

from config_de_carpetas import carpeta_resumen


def generar_resumen(archivo_historial, numero_seccion, modelo="nemotron-3-super:cloud"):
    with open(archivo_historial, "r", encoding="utf-8") as historial:
        contenido_historial = historial.read()

    respuesta = ollama.chat(
        model=modelo,
        messages=[
            {
                "role": "system",
                "content": (
                    "Resume conversaciones sin inventar información. "
                    "Conserva solo datos útiles para futuras conversaciones, "
                    "en un máximo de ocho puntos."
                ),
            },
            {"role": "user", "content": contenido_historial},
        ],
    )

    archivo_resumen = carpeta_resumen / f"RESUMEN_{numero_seccion:04d}.txt"
    with open(archivo_resumen, "w", encoding="utf-8") as resumen:
        resumen.write(respuesta.message.content)
    return archivo_resumen


def generar_resumen_memoria(archivo_historial, numero_seccion, modelo="qwen2.5:7b"):
    return generar_resumen(archivo_historial, numero_seccion, modelo)


def obtener_ultimo_resumen(numero_seccion):
    numero_anterior = numero_seccion - 1
    if numero_anterior < 1:
        return None

    archivo = carpeta_resumen / f"RESUMEN_{numero_anterior:04d}.txt"
    if not archivo.exists():
        return None

    with open(archivo, "r", encoding="utf-8") as resumen:
        return resumen.read()
