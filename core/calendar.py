"""Reglas, validaciones y consultas de calendario."""

import logging
import uuid
from datetime import date, datetime, time, timedelta, timezone
from typing import Any

from data.calendar import (
    guardar_calendario_personal,
    leer_calendario_academico,
    leer_calendario_personal,
)


ORIGENES_CALENDARIO = {
    "Ambos": "ambos",
    "Académico": "academico",
    "Personal": "personal",
}
CATEGORIAS_CALENDARIO = {
    "Evaluaciones": {"evaluation_week"},
    "Bienestar": {"wellbeing_activity"},
    "Períodos académicos": {"period_start", "period_end"},
    "Actividades": {"university_activity"},
}


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
    origen: str,
    dt_inicio_busqueda: date,
    dt_fin_busqueda: date,
    tipo_normalizado: str,
) -> list[dict[str, Any]]:
    try:
        if origen == "personal":
            contenido = leer_calendario_personal()
        else:
            contenido = leer_calendario_academico()
    except FileNotFoundError:
        if origen == "personal":
            return []
        raise OSError("No se encontró el calendario académico.")
    lineas = contenido.splitlines()

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
            categoria = evento_actual.get(
                "CATEGORIES", "personal" if origen == "personal" else ""
            )
            coincide_categoria = (
                tipo_normalizado == "any"
                or tipo_normalizado == categoria.lower()
            )
            inicio_evento = evento_actual.get("_DTSTART_OBJ")
            fin_evento_exclusivo = evento_actual.get("_DTEND_OBJ")

            if not coincide_categoria or not inicio_evento or not fin_evento_exclusivo:
                continue

            es_evento_con_hora = isinstance(inicio_evento, datetime)
            if es_evento_con_hora:
                inicio_fecha = inicio_evento.date()
                fin_fecha = (fin_evento_exclusivo - timedelta(microseconds=1)).date()
                hora_inicio = inicio_evento.strftime("%H:%M")
                hora_fin = fin_evento_exclusivo.strftime("%H:%M")
            else:
                inicio_fecha = inicio_evento
                fin_fecha = fin_evento_exclusivo - timedelta(days=1)
                hora_inicio = None
                hora_fin = None

            if inicio_fecha <= dt_fin_busqueda and fin_fecha >= dt_inicio_busqueda:
                eventos_encontrados.append(
                    {
                        "resumen": _desescapar_ics(evento_actual.get("SUMMARY", "")),
                        "uid": evento_actual.get("UID"),
                        "categoria": categoria,
                        "fecha_inicio": inicio_fecha.isoformat(),
                        "fecha_fin": fin_fecha.isoformat(),
                        "hora_inicio": hora_inicio,
                        "hora_fin": hora_fin,
                        "periodo_id": evento_actual.get("X-AETHERA-PERIOD-ID"),
                        "distrito_id": evento_actual.get("X-AETHERA-DISTRICT-ID"),
                        "descripcion": _desescapar_ics(
                            evento_actual.get("DESCRIPTION", "")
                        ),
                        "origen": origen,
                    }
                )
        elif en_evento and ":" in linea:
            clave_completa, valor = linea.split(":", 1)
            clave = clave_completa.split(";")[0]
            evento_actual[clave] = valor

            if clave in ("DTSTART", "DTEND"):
                try:
                    if "VALUE=DATE" in clave_completa or len(valor) == 8:
                        objeto = datetime.strptime(valor, "%Y%m%d").date()
                    else:
                        formato = (
                            "%Y%m%dT%H%M%SZ"
                            if valor.endswith("Z")
                            else "%Y%m%dT%H%M%S"
                        )
                        objeto = datetime.strptime(valor, formato)
                    evento_actual[f"_{clave}_OBJ"] = objeto
                except ValueError:
                    continue

    return eventos_encontrados


def buscar_eventos(
    tipo: str,
    fecha_inicio: str = "1900-01-01",
    fecha_fin: str = "2100-01-01",
    origen: str = "ambos",
) -> list[dict[str, Any]]:
    """Devuelve eventos filtrados por rango, categoría y origen."""
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
    origenes = {
        "academico": ("academico",),
        "personal": ("personal",),
        "ambos": ("academico", "personal"),
    }
    if origen_normalizado not in origenes:
        return [{"error": "El origen debe ser 'academico', 'personal' o 'ambos'."}]

    try:
        eventos = []
        for nombre_origen in origenes[origen_normalizado]:
            eventos.extend(
                _leer_eventos(
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


def obtener_eventos_semana(
    fecha_inicio: date,
    fecha_fin: date,
    origen: str,
    categoria: str,
) -> list[dict[str, Any]]:
    """Carga eventos de un rango y aplica el origen y categoría seleccionados."""
    origen_consulta = ORIGENES_CALENDARIO.get(origen)
    if origen_consulta is None:
        raise ValueError(f"Origen de calendario inválido: {origen}")

    eventos = buscar_eventos(
        "any",
        fecha_inicio=fecha_inicio.isoformat(),
        fecha_fin=fecha_fin.isoformat(),
        origen=origen_consulta,
    )
    if eventos and "error" in eventos[0]:
        raise ValueError(eventos[0]["error"])

    categorias = CATEGORIAS_CALENDARIO.get(categoria)
    if categorias is None:
        return eventos
    return [evento for evento in eventos if evento.get("categoria") in categorias]


def _escapar_ics(valor: str) -> str:
    return (
        valor.replace("\\", "\\\\")
        .replace("\r\n", "\n")
        .replace("\r", "\n")
        .replace("\n", r"\n")
        .replace(",", r"\,")
        .replace(";", r"\;")
    )


def _plegar_linea_ics(linea: str) -> str:
    segmentos = []
    segmento = ""
    longitud = 0
    for caracter in linea:
        bytes_caracter = len(caracter.encode("utf-8"))
        if longitud + bytes_caracter > 75:
            segmentos.append(segmento)
            segmento = " "
            longitud = 1
        segmento += caracter
        longitud += bytes_caracter
    segmentos.append(segmento)
    return "\r\n".join(segmentos)


def eliminar_evento(uid: str) -> dict[str, str]:
    """Elimina un evento personal identificado por su UID."""
    if not isinstance(uid, str) or not uid.strip():
        return {"error": "Se requiere un identificador de evento válido."}

    try:
        contenido = leer_calendario_personal()
        lineas = contenido.replace("\r\n", "\n").replace("\r", "\n").splitlines()
        if (
            not lineas
            or lineas[0] != "BEGIN:VCALENDAR"
            or lineas[-1] != "END:VCALENDAR"
        ):
            return {"error": "El archivo de calendario personal no es válido."}

        bloques_eventos = []
        indice = 0
        while indice < len(lineas):
            if lineas[indice] != "BEGIN:VEVENT":
                indice += 1
                continue
            fin_evento = indice + 1
            while fin_evento < len(lineas) and lineas[fin_evento] != "END:VEVENT":
                fin_evento += 1
            if fin_evento == len(lineas):
                return {"error": "El calendario contiene un evento ICS incompleto."}
            bloque = lineas[indice : fin_evento + 1]
            desplegado = []
            for linea in bloque:
                if linea.startswith((" ", "\t")) and desplegado:
                    desplegado[-1] += linea[1:]
                else:
                    desplegado.append(linea)
            uid_evento = next(
                (
                    linea.split(":", 1)[1]
                    for linea in desplegado
                    if linea.startswith("UID:")
                ),
                None,
            )
            if uid_evento == uid:
                bloques_eventos.append((indice, fin_evento + 1))
            indice = fin_evento + 1

        if not bloques_eventos:
            return {"error": "No se encontró ese evento en el calendario Personal."}
        if len(bloques_eventos) > 1:
            return {
                "error": (
                    "El identificador aparece en varios eventos; "
                    "no se eliminó ninguno."
                )
            }

        inicio_bloque, fin_bloque = bloques_eventos[0]
        del lineas[inicio_bloque:fin_bloque]
        guardar_calendario_personal("\r\n".join(lineas) + "\r\n")
    except (OSError, UnicodeDecodeError) as error:
        logging.exception("No se pudo eliminar el evento personal.")
        return {"error": f"No se pudo eliminar el evento personal: {error}"}

    return {"mensaje": "Evento eliminado del calendario Personal."}


def crear_evento(
    titulo: str,
    fecha_inicio: str,
    fecha_fin: str = "",
    descripcion: str = "",
    hora_inicio: str = "",
    hora_fin: str = "",
) -> dict[str, Any]:
    """Valida y crea un evento de día completo o con horario."""
    if not isinstance(titulo, str) or not titulo.strip():
        return {"error": "El título del evento no puede estar vacío."}
    titulo = titulo.strip()
    if len(titulo) > 200:
        return {"error": "El título del evento no puede superar 200 caracteres."}
    if not isinstance(descripcion, str):
        return {"error": "La descripción debe ser texto."}
    descripcion = descripcion.strip()
    if len(descripcion) > 2000:
        return {"error": "La descripción no puede superar 2000 caracteres."}

    try:
        inicio = date.fromisoformat(fecha_inicio)
        fin = date.fromisoformat(fecha_fin) if fecha_fin else inicio
    except (TypeError, ValueError):
        return {"error": "Las fechas deben tener el formato YYYY-MM-DD."}
    if inicio.isoformat() != fecha_inicio or (fecha_fin and fin.isoformat() != fecha_fin):
        return {"error": "Las fechas deben tener el formato YYYY-MM-DD."}
    if fin < inicio:
        return {"error": "La fecha de fin no puede ser anterior a la fecha de inicio."}
    if fin == date.max:
        return {"error": "La fecha de fin debe ser anterior al 31/12/9999."}

    if not isinstance(hora_inicio, str) or not isinstance(hora_fin, str):
        return {"error": "Las horas deben ser texto en formato HH:MM."}
    hora_inicio = hora_inicio.strip()
    hora_fin = hora_fin.strip()
    if bool(hora_inicio) != bool(hora_fin):
        return {"error": "Debes indicar tanto la hora de inicio como la de fin."}

    inicio_horario = None
    fin_horario = None
    if hora_inicio:
        try:
            inicio_horario = time.fromisoformat(hora_inicio)
            fin_horario = time.fromisoformat(hora_fin)
        except ValueError:
            return {"error": "Las horas deben tener el formato HH:MM."}
        if (
            inicio_horario.strftime("%H:%M") != hora_inicio
            or fin_horario.strftime("%H:%M") != hora_fin
        ):
            return {"error": "Las horas deben tener el formato HH:MM."}
        fecha_hora_inicio = datetime.combine(inicio, inicio_horario)
        fecha_hora_fin = datetime.combine(fin, fin_horario)
        if fecha_hora_fin <= fecha_hora_inicio:
            return {
                "error": "La fecha y hora de fin deben ser posteriores a las de inicio."
            }

    try:
        try:
            contenido = leer_calendario_personal()
        except FileNotFoundError:
            contenido = ""
        if contenido.strip():
            lineas_calendario = (
                contenido.replace("\r\n", "\n").replace("\r", "\n").splitlines()
            )
            if (
                not lineas_calendario
                or lineas_calendario[0] != "BEGIN:VCALENDAR"
                or lineas_calendario[-1] != "END:VCALENDAR"
            ):
                return {"error": "El archivo de calendario personal no es válido."}
            contenido = "\r\n".join(lineas_calendario[:-1])
        else:
            contenido = (
                "BEGIN:VCALENDAR\r\n"
                "VERSION:2.0\r\n"
                "PRODID:-//Aethera//Calendario Personal//ES\r\n"
                "CALSCALE:GREGORIAN\r\n"
                "X-WR-CALNAME:Personal"
            )

        identificador = f"{uuid.uuid4()}@aethera"
        if inicio_horario and fin_horario:
            fecha_inicio_ics = fecha_hora_inicio.strftime("%Y%m%dT%H%M%S")
            fecha_fin_ics = fecha_hora_fin.strftime("%Y%m%dT%H%M%S")
            propiedad_inicio = f"DTSTART:{fecha_inicio_ics}"
            propiedad_fin = f"DTEND:{fecha_fin_ics}"
        else:
            fecha_fin_ics = date.fromordinal(fin.toordinal() + 1).strftime("%Y%m%d")
            propiedad_inicio = f"DTSTART;VALUE=DATE:{inicio.strftime('%Y%m%d')}"
            propiedad_fin = f"DTEND;VALUE=DATE:{fecha_fin_ics}"
        evento = [
            "BEGIN:VEVENT",
            f"UID:{identificador}",
            f"DTSTAMP:{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
            propiedad_inicio,
            propiedad_fin,
            f"SUMMARY:{_escapar_ics(titulo)}",
            "CATEGORIES:personal",
            "X-AETHERA-SOURCE:PERSONAL",
        ]
        if descripcion:
            evento.append(f"DESCRIPTION:{_escapar_ics(descripcion)}")
        evento.append("END:VEVENT")

        nuevo_contenido = (
            contenido.rstrip("\r\n")
            + "\r\n"
            + "\r\n".join(_plegar_linea_ics(linea) for linea in evento)
            + "\r\nEND:VCALENDAR\r\n"
        )
        guardar_calendario_personal(nuevo_contenido)
    except (OSError, UnicodeDecodeError) as error:
        logging.exception("No se pudo guardar el evento personal.")
        return {"error": f"No se pudo guardar el evento personal: {error}"}

    return {
        "mensaje": "Evento creado en el calendario Personal.",
        "evento": {
            "resumen": titulo,
            "fecha_inicio": inicio.isoformat(),
            "fecha_fin": fin.isoformat(),
            "hora_inicio": hora_inicio or None,
            "hora_fin": hora_fin or None,
            "descripcion": descripcion,
            "origen": "personal",
        },
    }


def guardar_evento_personal(
    titulo: str,
    fecha_inicio: str,
    fecha_fin: str = "",
    descripcion: str = "",
    hora_inicio: str = "",
    hora_fin: str = "",
) -> dict[str, Any]:
    """Crea un evento personal usando las mismas reglas del calendario."""
    return crear_evento(
        titulo,
        fecha_inicio,
        fecha_fin,
        descripcion,
        hora_inicio,
        hora_fin,
    )


def borrar_evento_personal(evento: dict[str, Any]) -> dict[str, str]:
    """Elimina un evento solo cuando su origen es el calendario personal."""
    if evento.get("origen") != "personal":
        return {"error": "Solo se pueden eliminar eventos del calendario Personal."}
    uid = evento.get("uid")
    if not isinstance(uid, str) or not uid.strip():
        return {"error": "El evento personal no contiene un identificador válido."}
    return eliminar_evento(uid)
