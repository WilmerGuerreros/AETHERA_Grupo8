from config_de_carpetas import carpeta_resumen


def obtener_ultimo_resumen(numero_seccion):
    numero_anterior = numero_seccion - 1
    if numero_anterior < 1:
        return None

    archivo = carpeta_resumen / f"RESUMEN_{numero_anterior:04d}.txt"
    if not archivo.exists():
        return None

    with open(archivo, "r", encoding="utf-8") as resumen:
        return resumen.read()