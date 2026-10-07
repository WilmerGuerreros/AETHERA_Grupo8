from config_de_carpetas import carpeta_historial

from .contar_conversaciones import contar_conversaciones


def obtener_ultimo_archivo():
    numero = 1
    while (carpeta_historial / f"HISTORIAL_{numero:04d}.txt").exists():
        numero += 1

    if numero == 1:
        return None, 0

    archivo = carpeta_historial / f"HISTORIAL_{numero - 1:04d}.txt"
    return archivo, contar_conversaciones(archivo)