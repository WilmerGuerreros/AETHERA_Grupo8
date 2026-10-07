import os
from datetime import datetime, timedelta
from pathlib import Path

# Obtiene la carpeta 'tools' (donde está la herramienta)
TOOLS_DIR = Path(__file__).resolve().parent

# .parent sube a la raíz ('mi_proyecto') e ingresa a 'Resources/D7_calendar.ics'
RUTA_RECURSOS = TOOLS_DIR.parent / "Resources" / "D7_calendar.ics"

def calendario_academico(fecha_inicio: str, fecha_fin: str, tipo: str) -> list[dict]:
    """
Consulta eventos del calendario académico en un rango de fechas inclusivo.

Args:
    fecha_inicio (str): Fecha inicial en formato 'YYYY-MM-DD'.
    fecha_fin (str): Fecha final en formato 'YYYY-MM-DD'.
    tipo (str): Categoría exacta: 'period_start' (inicios), 'evaluation_week' (exámenes), 'wellbeing_activity' (pausas), 'period_end' (cierres), 'university_activity' (encuentros) o 'any' (todos).

Returns:
    list[dict]: Lista de eventos con claves: 'resumen', 'categoria', 'fecha_inicio', 'fecha_fin', 'periodo_id', 'distrito_id'. Si falla, retorna [{'error': 'motivo'}].
"""
    try:
        dt_inicio_busqueda = datetime.strptime(fecha_inicio, "%Y-%m-%d")
        dt_fin_busqueda = datetime.strptime(fecha_fin, "%Y-%m-%d")
    except ValueError:
        return [{"error": "Las fechas deben tener el formato YYYY-MM-DD."}]

    if dt_inicio_busqueda > dt_fin_busqueda:
        return [{"error": "La fecha de inicio no puede ser posterior a la fecha de fin."}]

    tipo_normalizado = tipo.strip().lower()
    categorias_validas = {
        "any",
        "period_start",
        "evaluation_week",
        "wellbeing_activity",
        "period_end",
        "university_activity",
    }
    if tipo_normalizado not in categorias_validas:
        return [{"error": f"Categoría inválida: {tipo}. Usa una de estas opciones: {', '.join(sorted(categorias_validas))}."}]

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
                tipo_normalizado == "any" or
                tipo_normalizado == categoria_evento.lower()
            )

            dt_start_evento = evento_actual.get("_DTSTART_OBJ")
            dt_end_evento = evento_actual.get("_DTEND_OBJ")

            if coincide_etiqueta and dt_start_evento and dt_end_evento:
                # En eventos de día completo, DTEND es exclusivo según el formato ICS.
                fecha_fin_evento = dt_end_evento - timedelta(days=1)
                if dt_start_evento <= dt_fin_busqueda and fecha_fin_evento >= dt_inicio_busqueda:
                    eventos_encontrados.append({
                        "resumen": evento_actual.get("SUMMARY"),
                        "categoria": evento_actual.get("CATEGORIES"),
                        "fecha_inicio": dt_start_evento.strftime("%Y-%m-%d"),
                        "fecha_fin": fecha_fin_evento.strftime("%Y-%m-%d"),
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


# Mantiene disponible el nombre usado antes de registrar la herramienta en el agente.
consultar_calendario_academico = calendario_academico