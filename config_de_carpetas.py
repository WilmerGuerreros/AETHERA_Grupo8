import sys
from pathlib import Path

from app_paths import user_data_directory


carpeta_chats = (
    user_data_directory() / "CHATS DE AETHERA AI"
    if getattr(sys, "frozen", False)
    else Path("CHATS DE AETHERA AI")
)

carpeta_memoria = carpeta_chats / "MEMORIA" 
carpeta_historial = carpeta_memoria / "HISTORIAL"
carpeta_resumen = carpeta_memoria / "RESUMEN"
carpeta_indice = carpeta_memoria / "INDICE" 
carpeta_adjuntos = carpeta_memoria / "ARCHIVOS ADJUNTOS"


# Crear carpetas si no existen  
carpeta_chats.mkdir(parents=True, exist_ok=True) 
carpeta_historial.mkdir(parents=True, exist_ok=True)
carpeta_resumen.mkdir(parents=True, exist_ok=True)
carpeta_indice.mkdir(parents=True, exist_ok=True)
carpeta_adjuntos.mkdir(parents=True, exist_ok=True) 