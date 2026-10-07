import json

from config_de_carpetas import carpeta_indice


def cargar_indice():
    archivo_indice = carpeta_indice / "INDICE_MEMORIA.json"
    if archivo_indice.exists():
        with open(archivo_indice, "r", encoding="utf-8") as archivo:
            return json.load(archivo)

    return {"secciones": [], "temas": {}}