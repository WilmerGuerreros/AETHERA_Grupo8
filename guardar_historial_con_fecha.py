from datetime import datetime

from config_de_carpetas import carpeta_historial
from índice_y_generar import actualizar_indice
from resumen_por_memoria import generar_resumen
from retomar_memoria_escritura import inicializar_memoria


numero_seccion, contador_mensajes = inicializar_memoria()

def guardar_historial(usuario, respuesta, modelo="qwen2.5:7b"):

    global numero_seccion
    global contador_mensajes

    archivo = (
        carpeta_historial /
        f"HISTORIAL_{numero_seccion:04d}.txt"
    )
    archivo.parent.mkdir(parents=True, exist_ok=True)

    fecha = datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    with open(archivo, "a", encoding="utf-8") as f:

        f.write(
            "\n" + "=" * 60 + "\n"
        )

        f.write(
            f"Fecha: {fecha}\n"
        )

        f.write(
            "=" * 60 + "\n"
        )

        f.write(
            f"Usuario: {usuario}\n"
        )

        f.write(
            f"Aethera: {respuesta}\n"
        )

    contador_mensajes += 1

    print(
        f"[Memoria] "
        f"HISTORIAL_{numero_seccion:04d} "
        f"→ {contador_mensajes}/20"
    )

    # ========================================================
    # SELLAR SECCIÓN
    # ========================================================

    if contador_mensajes >= 20:

        print(
            "\n[Memoria] "
            "Sección completada."
        )

        # Generar resumen
        archivo_resumen = generar_resumen(
            archivo,
            numero_seccion,
            modelo,
        )

        # Actualizar índice
        actualizar_indice(
            numero_seccion,
            archivo,
            archivo_resumen
        )

        print(
            "[Memoria] Resumen guardado."
        )

        print(
            "[Memoria] Índice actualizado."
        )

        # Pasar a la siguiente sección
        numero_seccion += 1

        contador_mensajes = 0

        print(
            f"[Memoria] Nueva sección: "
            f"HISTORIAL_{numero_seccion:04d}"
        )



