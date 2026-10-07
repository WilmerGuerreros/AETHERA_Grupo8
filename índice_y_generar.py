import json
from config_de_carpetas import carpeta_indice, carpeta_resumen
from resumen_por_memoria import generar_resumen_memoria

def cargar_indice():

    archivo_indice = carpeta_indice / "INDICE_MEMORIA.json"

    if archivo_indice.exists():

        with open(archivo_indice, "r", encoding="utf-8") as f:

            return json.load(f)

    else:

        return {
            "secciones": [],
            "temas": {}
        }


def actualizar_indice(numero_seccion, archivo_historial, archivo_resumen):

    archivo_indice = carpeta_indice / "INDICE_MEMORIA.json"

    indice = cargar_indice()

    # Evitar duplicar una sección si por alguna razón
    # la función se ejecuta nuevamente
    for seccion in indice["secciones"]:

        if seccion["id"] == numero_seccion:
            return

    nueva_seccion = {

        "id": numero_seccion,

        "historial": archivo_historial.name,

        "resumen": archivo_resumen.name,

        "estado": "sellado"

    }

    indice["secciones"].append(nueva_seccion)

    with open(archivo_indice, "w", encoding="utf-8") as f:

        json.dump(
            indice,
            f,
            indent=4,
            ensure_ascii=False
        )

