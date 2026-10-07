import ollama

from config_de_carpetas import carpeta_resumen


def generar_resumen(archivo_historial, numero_seccion, modelo="qwen2.5:7b"):
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