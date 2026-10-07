import json

from config_de_carpetas import carpeta_indice

from .cargar_indice import cargar_indice


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