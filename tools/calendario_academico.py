import os
from datetime import datetime
from pathlib import Path

# Obtiene la carpeta 'tools' (donde está la herramienta)
TOOLS_DIR = Path(__file__).resolve().parent

# .parent sube a la raíz ('mi_proyecto') e ingresa a 'Resources/D7_calendar.ics'
RUTA_RECURSOS = TOOLS_DIR.parent / "Resources" / "D7_calendar.ics"

def consultar_eventos_calendario(fecha_inicio: str, fecha_fin: str, etiqueta: str) -> list[dict]:
    """
Consulta y filtra los eventos registrados en el calendario académico dentro de un rango temporal específico.

Args:
    fecha_inicio (str): Fecha de inicio del intervalo a consultar en formato 'YYYY-MM-DD' (ej: '2026-01-01').
    fecha_fin (str): Fecha de término del intervalo a consultar en formato 'YYYY-MM-DD' (ej: '2026-03-31').
    etiqueta (str): Categoría específica del evento a filtrar. Las opciones válidas registradas en el sistema son:
        - 'any': Recupera todos los eventos dentro del intervalo sin filtrar por categoría.
        - 'period_start': Inicios de períodos académicos[cite: 1].
        - 'evaluation_week': Semanas de evaluaciones intermedias y finales[cite: 1].
        - 'wellbeing_activity': Semanas de pausa y actividades de bienestar[cite: 1].
        - 'period_end': Cierres de períodos académicos[cite: 1].
        - 'university_activity': Encuentros estudiantiles y actividades universitarias específicas[cite: 1].

Returns:
    list[dict]: Lista de objetos donde cada elemento representa un evento que cumple con los criterios solicitados.
        Estructura de cada diccionario:
        - 'resumen' (str): Título o descripción breve del evento[cite: 1].
        - 'categoria' (str): Etiqueta asignada en el calendario[cite: 1].
        - 'fecha_inicio' (str): Fecha en que inicia el evento en formato 'YYYY-MM-DD'[cite: 1].
        - 'fecha_fin' (str): Fecha en que concluye el evento en formato 'YYYY-MM-DD'[cite: 1].
        - 'periodo_id' (str): Identificador del período académico asociado (ej: 'PER_2026_1')[cite: 1].
        - 'distrito_id' (str): Identificador del distrito al que pertenece el evento o 'ALL' si aplica a toda la institución[cite: 1].
        
        En caso de error en los parámetros o la ruta del recurso, retorna una lista con un diccionario indicando la clave 'error'.
"""
    try:
        dt_inicio_busqueda = datetime.strptime(fecha_inicio, "%Y-%m-%d")
        dt_fin_busqueda = datetime.strptime(fecha_fin, "%Y-%m-%d")
    except ValueError:
        return [{"error": "Las fechas deben tener el formato YYYY-MM-DD."}]

    if not os.path.exists(RUTA_RECURSOS):
        return [{"error": f"No se encontró el archivo en la ruta: {RUTA_RECURSOS}"}]

    eventos_encontrados = []

    with open(RUTA_RECURSOS, 'r', encoding='utf-8') as f:
        lineas = f.readlines()

    evento_actual = {}
    en_evento = False

    for linea in lineas:
        linea = linea.strip()

        if linea == "BEGIN:VEVENT":
            en_evento = True
            evento_actual = {}
        elif linea == "END:VEVENT":
            en_evento = False
            
            categoria_evento = evento_actual.get("CATEGORIES", "")
            
            # Sombra/Comprobación: si es 'any', ignora el filtro por categoría
            coincide_etiqueta = (
                etiqueta.lower() == "any" or 
                etiqueta.lower() in categoria_evento.lower()
            )

            dt_start_evento = evento_actual.get("_DTSTART_OBJ")
            dt_end_evento = evento_actual.get("_DTEND_OBJ")

            if coincide_etiqueta and dt_start_evento and dt_end_evento:
                # Comprobar si hay solapamiento con el intervalo
                if dt_start_evento <= dt_fin_busqueda and dt_end_evento >= dt_inicio_busqueda:
                    eventos_encontrados.append({
                        "resumen": evento_actual.get("SUMMARY"),
                        "categoria": evento_actual.get("CATEGORIES"),
                        "fecha_inicio": dt_start_evento.strftime("%Y-%m-%d"),
                        "fecha_fin": dt_end_evento.strftime("%Y-%m-%d"),
                        "periodo_id": evento_actual.get("X-AETHERA-PERIOD-ID"),
                        "distrito_id": evento_actual.get("X-AETHERA-DISTRICT-ID")
                    })

        elif en_evento and ":" in linea:
            clave_completa, valor = linea.split(":", 1)
            clave = clave_completa.split(";")[0]

            evento_actual[clave] = valor

            if clave in ("DTSTART", "DTEND"):
                try:
                    fecha_obj = datetime.strptime(valor, "%Y%m%d")
                    evento_actual[f"_{clave}_OBJ"] = fecha_obj
                except ValueError:
                    pass

    return eventos_encontrados