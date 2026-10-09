from .obtener_ultimo_archivo import obtener_ultimo_archivo


def inicializar_memoria():
    archivo, contador = obtener_ultimo_archivo()
    if archivo is None:
        return 1, 0

    numero_seccion = int(archivo.stem.split("_")[1])
    if contador >= 20:
        return numero_seccion + 1, 0
    return numero_seccion, contador 



# CIERRAS --> VUELVES A ABRIR LA APP  
# Historial_0016 #17 --> Historial_0016 #18 

