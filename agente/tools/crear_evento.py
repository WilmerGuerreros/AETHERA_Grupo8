import logging
import os
import tempfile
import uuid
from datetime import date, datetime, timezone

from app_paths import user_calendar_path


RUTA_CALENDARIO_PERSONAL = user_calendar_path()


def _escapar_valor_ics(valor: str) -> str:
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


def eliminar_evento(uid: str) -> dict:
    """Elimina del calendario personal el evento identificado por su UID."""
    if not isinstance(uid, str) or not uid.strip():
        return {"error": "Se requiere un identificador de evento válido."}

    ruta = RUTA_CALENDARIO_PERSONAL
    temporal = None
    try:
        contenido = ruta.read_text(encoding="utf-8")
        lineas = contenido.replace("\r\n", "\n").replace("\r", "\n").splitlines()
        if (
            not lineas
            or lineas[0] != "BEGIN:VCALENDAR"
            or lineas[-1] != "END:VCALENDAR"
        ):
            return {"error": f"El archivo de calendario personal no es válido: {ruta}"}

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
            return {"error": "El identificador aparece en varios eventos; no se eliminó ninguno."}

        inicio_bloque, fin_bloque = bloques_eventos[0]
        del lineas[inicio_bloque:fin_bloque]
        nuevo_contenido = "\r\n".join(lineas) + "\r\n"
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="",
            dir=ruta.parent,
            prefix=f".{ruta.name}.",
            suffix=".tmp",
            delete=False,
        ) as archivo:
            temporal = archivo.name
            archivo.write(nuevo_contenido)
        os.replace(temporal, ruta)
    except (OSError, UnicodeDecodeError) as error:
        logging.exception("No se pudo eliminar el evento personal.")
        return {"error": f"No se pudo eliminar el evento personal: {error}"}
    finally:
        if temporal and os.path.exists(temporal):
            os.unlink(temporal)

    return {"mensaje": "Evento eliminado del calendario Personal."}


def crear_evento(
    titulo: str,
    fecha_inicio: str,
    fecha_fin: str = "",
    descripcion: str = "",
) -> dict:
    """Crea un evento de día completo en el calendario personal del usuario.

    Args:
        titulo: Nombre breve del evento.
        fecha_inicio: Primer día del evento en formato YYYY-MM-DD.
        fecha_fin: Último día inclusivo en formato YYYY-MM-DD; si se omite,
            el evento dura un día.
        descripcion: Detalles opcionales del evento.

    Returns:
        Confirmación con los datos guardados o un diccionario con 'error'.
    """
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

    ruta = RUTA_CALENDARIO_PERSONAL
    temporal = None
    try:
        ruta.parent.mkdir(parents=True, exist_ok=True)
        contenido = ruta.read_text(encoding="utf-8") if ruta.exists() else ""
        if contenido.strip():
            lineas_calendario = contenido.replace("\r\n", "\n").replace("\r", "\n").splitlines()
            if (
                not lineas_calendario
                or lineas_calendario[0] != "BEGIN:VCALENDAR"
                or lineas_calendario[-1] != "END:VCALENDAR"
            ):
                return {"error": f"El archivo de calendario personal no es válido: {ruta}"}
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
        fin_exclusivo = fin.toordinal() + 1
        fecha_fin_ics = date.fromordinal(fin_exclusivo).strftime("%Y%m%d")
        evento = [
            "BEGIN:VEVENT",
            f"UID:{identificador}",
            f"DTSTAMP:{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
            f"DTSTART;VALUE=DATE:{inicio.strftime('%Y%m%d')}",
            f"DTEND;VALUE=DATE:{fecha_fin_ics}",
            f"SUMMARY:{_escapar_valor_ics(titulo)}",
            "CATEGORIES:personal",
            "X-AETHERA-SOURCE:PERSONAL",
        ]
        if descripcion:
            evento.append(f"DESCRIPTION:{_escapar_valor_ics(descripcion)}")
        evento.append("END:VEVENT")

        nuevo_contenido = (
            contenido.rstrip("\r\n")
            + "\r\n"
            + "\r\n".join(_plegar_linea_ics(linea) for linea in evento)
            + "\r\nEND:VCALENDAR\r\n"
        )
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="",
            dir=ruta.parent,
            prefix=f".{ruta.name}.",
            suffix=".tmp",
            delete=False,
        ) as archivo:
            temporal = archivo.name
            archivo.write(nuevo_contenido)
        os.replace(temporal, ruta)
    except (OSError, UnicodeDecodeError) as error:
        logging.exception("No se pudo guardar el evento personal.")
        return {"error": f"No se pudo guardar el evento personal: {error}"}
    finally:
        if temporal and os.path.exists(temporal):
            os.unlink(temporal)

    return {
        "mensaje": "Evento creado en el calendario Personal.",
        "evento": {
            "resumen": titulo,
            "fecha_inicio": inicio.isoformat(),
            "fecha_fin": fin.isoformat(),
            "descripcion": descripcion,
            "origen": "personal",
        },
    }