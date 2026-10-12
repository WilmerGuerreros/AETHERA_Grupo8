"""Carga y actualización del índice de resúmenes de memoria."""

import json

from config_de_carpetas import carpeta_indice


def cargar_indice():
    archivo_indice = carpeta_indice / "INDICE_MEMORIA.json"
    if archivo_indice.exists():
        with open(archivo_indice, "r", encoding="utf-8") as archivo:
            return json.load(archivo)

    return {"secciones": [], "temas": {}}


def actualizar_indice(numero_seccion, archivo_historial, archivo_resumen):
    indice = cargar_indice()
    if any(seccion["id"] == numero_seccion for seccion in indice["secciones"]):
        return

    indice["secciones"].append({
        "id": numero_seccion,
        "historial": archivo_historial.name,
        "resumen": archivo_resumen.name,
        "estado": "sellado",
    })

    archivo_indice = carpeta_indice / "INDICE_MEMORIA.json"
    with open(archivo_indice, "w", encoding="utf-8") as archivo:
        json.dump(indice, archivo, indent=4, ensure_ascii=False)
