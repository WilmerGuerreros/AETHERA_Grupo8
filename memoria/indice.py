"""Carga y actualización del índice de resúmenes de memoria."""

import json
from pathlib import Path


def cargar_indice(carpeta_indice):
    archivo_indice = Path(carpeta_indice) / "INDICE_MEMORIA.json"
    if archivo_indice.exists():
        return json.loads(archivo_indice.read_text(encoding="utf-8"))

    return {"secciones": [], "temas": {}}


def actualizar_indice(
    numero_seccion, archivo_historial, archivo_resumen, carpeta_indice
):
    indice = cargar_indice(carpeta_indice)
    if any(seccion["id"] == numero_seccion for seccion in indice["secciones"]):
        return

    indice["secciones"].append({
        "id": numero_seccion,
        "historial": Path(archivo_historial).name,
        "resumen": Path(archivo_resumen).name,
        "estado": "sellado",
    })

    archivo_indice = Path(carpeta_indice) / "INDICE_MEMORIA.json"
    archivo_indice.parent.mkdir(parents=True, exist_ok=True)
    archivo_indice.write_text(
        json.dumps(indice, indent=4, ensure_ascii=False),
        encoding="utf-8",
    )
