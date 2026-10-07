from config_de_carpetas import carpeta_historial, carpeta_resumen


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


def inicializar_memoria():
    archivo, contador = obtener_ultimo_archivo()
    if archivo is None:
        return 1, 0

    numero_seccion = int(archivo.stem.split("_")[1])
    if contador >= 20:
        return numero_seccion + 1, 0
    return numero_seccion, contador


def leer_interacciones(archivo):
    if not archivo.exists():
        return []

    interacciones = []
    usuario = None
    respuesta = None

    def guardar_interaccion():
        if usuario is not None and respuesta is not None:
            interacciones.append({
                "usuario": "\n".join(usuario).strip(),
                "aethera": "\n".join(respuesta).strip(),
            })

    with open(archivo, "r", encoding="utf-8") as historial:
        for linea in historial:
            linea = linea.rstrip("\n")
            if linea.startswith("=" * 10):
                guardar_interaccion()
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

    guardar_interaccion()
    return interacciones


def obtener_ultimas_interacciones(numero_seccion, cantidad=4):
    interacciones = []
    for numero in range(numero_seccion, 0, -1):
        archivo = carpeta_historial / f"HISTORIAL_{numero:04d}.txt"
        interacciones = leer_interacciones(archivo) + interacciones
        if len(interacciones) >= cantidad:
            break
    return interacciones[-cantidad:]


def obtener_ultimo_resumen(numero_seccion):
    numero_anterior = numero_seccion - 1
    if numero_anterior < 1:
        return None

    archivo = carpeta_resumen / f"RESUMEN_{numero_anterior:04d}.txt"
    if not archivo.exists():
        return None

    with open(archivo, "r", encoding="utf-8") as resumen:
        return resumen.read()