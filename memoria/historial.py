"""Lectura, escritura y consulta de historiales de conversación."""

from datetime import datetime

from config_de_carpetas import carpeta_historial

from .indice import actualizar_indice
from .resumen import generar_resumen


def guardar_interaccion(interacciones, usuario, respuesta):
    if usuario is not None and respuesta is not None:
        interacciones.append({
            "usuario": "\n".join(usuario).strip(),
            "aethera": "\n".join(respuesta).strip(),
        })


def leer_interacciones(archivo):
    if not archivo.exists():
        return []

    interacciones = []
    usuario = None
    respuesta = None

    with open(archivo, "r", encoding="utf-8") as historial:
        for linea in historial:
            linea = linea.rstrip("\n")
            if linea.startswith("=" * 10):
                guardar_interaccion(interacciones, usuario, respuesta)
                usuario = None
                respuesta = None
            elif linea.startswith("Usuario:"):
                usuario = [linea[len("Usuario:"):].strip()]
            elif linea.startswith("Aethera:"):
                respuesta = [linea[len("Aethera:"):].strip()]
            elif respuesta is not None:
                respuesta.append(linea)
            elif usuario is not None:
                usuario.append(linea)

    guardar_interaccion(interacciones, usuario, respuesta)
    return interacciones


def contar_conversaciones(archivo):
    if not archivo.exists():
        return 0

    with open(archivo, "r", encoding="utf-8") as historial:
        return sum(linea.startswith("Usuario:") for linea in historial)


def obtener_ultimo_archivo():
    numero = 1
    while (carpeta_historial / f"HISTORIAL_{numero:04d}.txt").exists():
        numero += 1

    if numero == 1:
        return None, 0

    archivo = carpeta_historial / f"HISTORIAL_{numero - 1:04d}.txt"
    return archivo, contar_conversaciones(archivo)


def obtener_ultimas_interacciones(numero_seccion, cantidad=4):
    interacciones = []
    for numero in range(numero_seccion, 0, -1):
        archivo = carpeta_historial / f"HISTORIAL_{numero:04d}.txt"
        interacciones = leer_interacciones(archivo) + interacciones
        if len(interacciones) >= cantidad:
            break
    return interacciones[-cantidad:]


def inicializar_memoria():
    archivo, contador = obtener_ultimo_archivo()
    if archivo is None:
        return 1, 0

    numero_seccion = int(archivo.stem.split("_")[1])
    if contador >= 20:
        return numero_seccion + 1, 0
    return numero_seccion, contador


numero_seccion, contador_mensajes = inicializar_memoria()


def guardar_historial(usuario, respuesta, modelo="nemotron-3-super:cloud"):
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
