from datetime import datetime

from config_de_carpetas import carpeta_historial

from .actualizar_indice import actualizar_indice
from .generar_resumen import generar_resumen
from .inicializar_memoria import inicializar_memoria


numero_seccion, contador_mensajes = inicializar_memoria()


def guardar_historial(usuario, respuesta, modelo="qwen2.5:7b"):
    global numero_seccion
    global contador_mensajes

    archivo = carpeta_historial / f"HISTORIAL_{numero_seccion:04d}.txt"
    archivo.parent.mkdir(parents=True, exist_ok=True)

    fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(archivo, "a", encoding="utf-8") as historial:
        historial.write("\n" + "=" * 60 + "\n")
        historial.write(f"Fecha: {fecha}\n")
        historial.write("=" * 60 + "\n")
        historial.write(f"Usuario: {usuario}\n")
        historial.write(f"Aethera: {respuesta}\n")

    contador_mensajes += 1
    print(f"[Memoria] HISTORIAL_{numero_seccion:04d} -> {contador_mensajes}/20")

    if contador_mensajes >= 20:
        archivo_resumen = generar_resumen(archivo, numero_seccion, modelo)
        actualizar_indice(numero_seccion, archivo, archivo_resumen)
        numero_seccion += 1
        contador_mensajes = 0 



                



