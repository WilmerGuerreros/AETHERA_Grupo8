import sys
from pathlib import Path

from app_paths import user_data_directory


carpeta_memoria = (
    user_data_directory() / "MEMORIA DE AETHERA AI"
    if getattr(sys, "frozen", False)
    else Path("MEMORIA DE AETHERA AI")
)

carpeta_historial = carpeta_memoria / "HISTORIAL"
carpeta_resumen = carpeta_memoria / "RESUMEN"
carpeta_indice = carpeta_memoria / "INDICE" 
carpeta_adjuntos = carpeta_memoria / "ARCHIVOS ADJUNTOS"


# Crear carpetas si no existen 
carpeta_historial.mkdir(parents=True, exist_ok=True)
carpeta_resumen.mkdir(parents=True, exist_ok=True)
carpeta_indice.mkdir(parents=True, exist_ok=True)
carpeta_adjuntos.mkdir(parents=True, exist_ok=True) 