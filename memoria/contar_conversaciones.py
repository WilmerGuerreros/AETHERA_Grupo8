def contar_conversaciones(archivo):
    if not archivo.exists():
        return 0

    with open(archivo, "r", encoding="utf-8") as historial:
        return sum(linea.startswith("Usuario:") for linea in historial)