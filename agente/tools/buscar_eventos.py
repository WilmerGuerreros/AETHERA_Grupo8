import logging
from datetime import date, datetime, timedelta

from app_paths import resource_path, user_calendar_path

RUTA_RECURSOS = resource_path("Resources", "D7_calendar.ics")
RUTA_CALENDARIO_PERSONAL = user_calendar_path()


def _desescapar_ics(valor: str) -> str:
    caracteres = []
    indice = 0
    while indice < len(valor):
        if valor[indice] == "\\" and indice + 1 < len(valor):
            siguiente = valor[indice + 1]
            if siguiente in "nN":
                caracteres.append("\n")
                indice += 2
                continue
            if siguiente in "\\,;":
                caracteres.append(siguiente)
                indice += 2
                continue
        caracteres.append(valor[indice])
        indice += 1
    return "".join(caracteres)


def _leer_eventos(
    ruta,
    origen: str,
    dt_inicio_busqueda: date,
    dt_fin_busqueda: date,
    tipo_normalizado: str,
) -> list[dict]:
    if not ruta.exists():
        if origen == "personal":
            return []
        raise OSError(f"No se encontró el archivo en la ruta: {ruta}")

    with ruta.open(encoding="utf-8") as archivo:
        lineas = archivo.read().splitlines()

    lineas_plegadas = []
    for linea in lineas:
        if linea.startswith((" ", "\t")) and lineas_plegadas:
            lineas_plegadas[-1] += linea[1:]
        else:
            lineas_plegadas.append(linea)

    eventos_encontrados = []
    evento_actual = {}
    en_evento = False

    for linea in lineas_plegadas:
        if linea == "BEGIN:VEVENT":
            en_evento = True
            evento_actual = {}
        elif linea == "END:VEVENT" and en_evento:
            en_evento = False
            categoria = evento_actual.get("CATEGORIES", "personal" if origen == "personal" else "")
            coincide_categoria = (
                tipo_normalizado == "any"
                or tipo_normalizado == categoria.lower()
            )
            inicio_evento = evento_actual.get("_DTSTART_OBJ")
            fin_evento_exclusivo = evento_actual.get("_DTEND_OBJ")

            if not coincide_categoria or not inicio_evento or not fin_evento_exclusivo:
                continue

            fin_evento = fin_evento_exclusivo - timedelta(days=1)
            if inicio_evento <= dt_fin_busqueda and fin_evento >= dt_inicio_busqueda:
                eventos_encontrados.append(
                    {
                        "resumen": _desescapar_ics(evento_actual.get("SUMMARY", "")),
                        "categoria": categoria,
                        "fecha_inicio": inicio_evento.isoformat(),
                        "fecha_fin": fin_evento.isoformat(),
                        "periodo_id": evento_actual.get("X-AETHERA-PERIOD-ID"),
                        "distrito_id": evento_actual.get("X-AETHERA-DISTRICT-ID"),
                        "descripcion": _desescapar_ics(evento_actual.get("DESCRIPTION", "")),
                        "origen": origen,
                    }
                )
        elif en_evento and ":" in linea:
            clave_completa, valor = linea.split(":", 1)
            clave = clave_completa.split(";")[0]
            evento_actual[clave] = valor

            if clave in ("DTSTART", "DTEND"):
                try:
                    evento_actual[f"_{clave}_OBJ"] = datetime.strptime(
                        valor, "%Y%m%d"
                    ).date()
                except ValueError:
                    continue

    return eventos_encontrados


def buscar_eventos(
    tipo: str,
    fecha_inicio: str = "1900-01-01",
    fecha_fin: str = "2100-01-01",
    origen: str = "ambos",
) -> list[dict]:
    """
Consulta eventos académicos, personales o de ambos calendarios en un rango inclusivo.

Args:
    tipo: Categoría exacta o 'any' para todas.
    fecha_inicio: Fecha inicial en formato 'YYYY-MM-DD'.
    fecha_fin: Fecha final en formato 'YYYY-MM-DD'.
    origen: 'academico', 'personal' o 'ambos'. Por defecto busca en ambos.

Returns:
    Lista de eventos etiquetados con su origen, o [{'error': 'motivo'}].
    """
    try:
        dt_inicio_busqueda = date.fromisoformat(fecha_inicio)
        dt_fin_busqueda = date.fromisoformat(fecha_fin)
    except (TypeError, ValueError):
        return [{"error": "Las fechas deben tener el formato YYYY-MM-DD."}]

    if dt_inicio_busqueda > dt_fin_busqueda:
        return [{"error": "La fecha de inicio no puede ser posterior a la fecha de fin."}]

    if not isinstance(tipo, str):
        return [{"error": "La categoría debe ser una cadena de texto."}]
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
        return [
            {
                "error": (
                    f"Categoría inválida: {tipo}. Usa una de estas opciones: "
                    f"{', '.join(sorted(categorias_validas))}."
                )
            }
        ]

    origen_normalizado = origen.strip().lower() if isinstance(origen, str) else ""
    rutas = {
        "academico": ((RUTA_RECURSOS, "academico"),),
        "personal": ((RUTA_CALENDARIO_PERSONAL, "personal"),),
        "ambos": (
            (RUTA_RECURSOS, "academico"),
            (RUTA_CALENDARIO_PERSONAL, "personal"),
        ),
    }
    if origen_normalizado not in rutas:
        return [{"error": "El origen debe ser 'academico', 'personal' o 'ambos'."}]

    try:
        eventos = []
        for ruta, nombre_origen in rutas[origen_normalizado]:
            eventos.extend(
                _leer_eventos(
                    ruta,
                    nombre_origen,
                    dt_inicio_busqueda,
                    dt_fin_busqueda,
                    tipo_normalizado,
                )
            )
        return sorted(
            eventos,
            key=lambda evento: (evento["fecha_inicio"], evento["resumen"]),
        )
    except (OSError, UnicodeDecodeError) as error:
        logging.exception("No se pudieron cargar los calendarios.")
        return [{"error": f"No se pudieron cargar los calendarios: {error}"}]