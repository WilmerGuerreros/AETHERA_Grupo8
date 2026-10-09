from config_de_carpetas import carpeta_historial

from .leer_interacciones import leer_interacciones


def obtener_ultimas_interacciones(numero_seccion, cantidad=4):
    interacciones = []
    for numero in range(numero_seccion, 0, -1):
        archivo = carpeta_historial / f"HISTORIAL_{numero:04d}.txt"
        interacciones = leer_interacciones(archivo) + interacciones
        if len(interacciones) >= cantidad:
            break
    return interacciones[-cantidad:] 

#HISTORIAL 00_69 