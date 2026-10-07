from .generar_resumen import generar_resumen


def generar_resumen_memoria(archivo_historial, numero_seccion, modelo="qwen2.5:7b"):
    return generar_resumen(archivo_historial, numero_seccion, modelo)