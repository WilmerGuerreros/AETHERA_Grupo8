def guardar_interaccion(interacciones, usuario, respuesta):
    if usuario is not None and respuesta is not None:
        interacciones.append({
            "usuario": "\n".join(usuario).strip(),
            "aethera": "\n".join(respuesta).strip(),
        })