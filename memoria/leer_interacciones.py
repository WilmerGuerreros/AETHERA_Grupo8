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
                if usuario is not None and respuesta is not None:
                    interacciones.append({
                        "usuario": "\n".join(usuario).strip(),
                        "aethera": "\n".join(respuesta).strip(),
                    })
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

    if usuario is not None and respuesta is not None:
        interacciones.append({
            "usuario": "\n".join(usuario).strip(),
            "aethera": "\n".join(respuesta).strip(),
        })

    return interacciones