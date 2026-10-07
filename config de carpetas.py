from pathlib import Path
from datetime import datetime
import json
import ollama


carpeta_memoria = Path("MEMORIA DE AETHERA AI")

carpeta_historial = carpeta_memoria / "HISTORIAL"
carpeta_resumen = carpeta_memoria / "RESUMEN"
carpeta_indice = carpeta_memoria / "INDICE"


# Crear carpetas si no existen
carpeta_historial.mkdir(parents=True, exist_ok=True)
carpeta_resumen.mkdir(parents=True, exist_ok=True)
carpeta_indice.mkdir(parents=True, exist_ok=True)
