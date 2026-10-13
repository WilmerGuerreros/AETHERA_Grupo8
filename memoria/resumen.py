"""Generación y consulta de resúmenes de memoria."""

from pathlib import Path

from config import MODELO_RESUMEN


def generar_resumen(
    archivo_historial,
    numero_seccion,
    carpeta_resumen,
    modelo=None,
):
    """Resume un historial con el modelo configurado y guarda el resultado."""
    import ollama

    modelo = modelo or MODELO_RESUMEN
    contenido_historial = Path(archivo_historial).read_text(encoding="utf-8")

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

    archivo_resumen = Path(carpeta_resumen) / f"RESUMEN_{numero_seccion:04d}.txt"
    archivo_resumen.write_text(respuesta.message.content, encoding="utf-8")
    return archivo_resumen


def obtener_ultimo_resumen(numero_seccion, carpeta_resumen):
    """Devuelve el texto del resumen de la sección anterior, si existe."""
    numero_anterior = numero_seccion - 1
    if numero_anterior < 1:
        return None

    archivo = Path(carpeta_resumen) / f"RESUMEN_{numero_anterior:04d}.txt"
    if not archivo.exists():
        return None

    return archivo.read_text(encoding="utf-8")
