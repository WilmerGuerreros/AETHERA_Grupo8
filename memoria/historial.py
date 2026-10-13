"""Lectura, escritura y consulta de historiales de conversación."""

from datetime import datetime
from pathlib import Path


def guardar_interaccion(interacciones, usuario, respuesta):
    if usuario is not None and respuesta is not None:
        interacciones.append({
            "usuario": "\n".join(usuario).strip(),
            "aethera": "\n".join(respuesta).strip(),
        })


def leer_interacciones(archivo: Path):
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


def contar_conversaciones(archivo: Path):
    if not archivo.exists():
        return 0

    with open(archivo, "r", encoding="utf-8") as historial:
        return sum(linea.startswith("Usuario:") for linea in historial)


def ruta_historial(carpeta_historial: Path, numero_seccion: int) -> Path:
    """Devuelve la ruta del archivo de historial de una sección."""
    return Path(carpeta_historial) / f"HISTORIAL_{numero_seccion:04d}.txt"


def obtener_ultimo_archivo(carpeta_historial: Path):
    numero = 1
    while ruta_historial(carpeta_historial, numero).exists():
        numero += 1

    if numero == 1:
        return None, 0

    archivo = ruta_historial(carpeta_historial, numero - 1)
    return archivo, contar_conversaciones(archivo)


def obtener_ultimas_interacciones(
    carpeta_historial: Path, numero_seccion, cantidad=4
):
    interacciones = []
    for numero in range(numero_seccion, 0, -1):
        archivo = ruta_historial(carpeta_historial, numero)
        interacciones = leer_interacciones(archivo) + interacciones
        if len(interacciones) >= cantidad:
            break
    return interacciones[-cantidad:]


def inicializar_memoria(carpeta_historial: Path, max_mensajes: int = 20):
    """Calcula la sección y el contador actuales a partir del disco."""
    archivo, contador = obtener_ultimo_archivo(carpeta_historial)
    if archivo is None:
        return 1, 0

    numero_seccion = int(archivo.stem.split("_")[1])
    if contador >= max_mensajes:
        return numero_seccion + 1, 0
    return numero_seccion, contador


def escribir_interaccion(
    carpeta_historial: Path, numero_seccion, usuario, respuesta
) -> Path:
    """Añade una interacción al historial de la sección y devuelve su ruta."""
    archivo = ruta_historial(carpeta_historial, numero_seccion)
    archivo.parent.mkdir(parents=True, exist_ok=True)

    fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(archivo, "a", encoding="utf-8") as historial:
        historial.write("\n" + "=" * 60 + "\n")
        historial.write(f"Fecha: {fecha}\n")
        historial.write("=" * 60 + "\n")
        historial.write(f"Usuario: {usuario}\n")
        historial.write(f"Aethera: {respuesta}\n")
    return archivo
