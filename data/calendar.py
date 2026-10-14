"""Lectura, consulta y escritura de los calendarios académico y personal.

Este módulo es el único que conoce el formato ICS, las rutas de los archivos, la
forma de guardarlos y el catálogo de orígenes y categorías del calendario.
``core`` solo pide eventos con filtros y delega aquí las altas y bajas; no sabe
cómo se almacenan, cómo se buscan ni qué categorías existen.
"""

import os
import tempfile
import uuid
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from typing import Any

from data.paths import resource_path, user_calendar_path


RECURSO_CALENDARIO = "D7_calendar.ics"

# Orígenes (calendarios) disponibles. ``ORIGEN_EDITABLE`` es el único en el que
# el usuario puede crear y eliminar eventos; el resto es de solo lectura.
ORIGENES = ("academico", "personal")
ORIGEN_EDITABLE = "personal"

CABECERA_PERSONAL = (
    "BEGIN:VCALENDAR\r\n"
    "VERSION:2.0\r\n"
    "PRODID:-//Aethera//Calendario Personal//ES\r\n"
    "CALSCALE:GREGORIAN\r\n"
    "X-WR-CALNAME:Personal"
)


class CalendarioInvalido(ValueError):
    """El contenido del calendario no tiene la estructura ICS esperada."""


class EventoNoEncontrado(ValueError):
    """No existe un evento personal con el identificador pedido."""


class EventoAmbiguo(ValueError):
    """El identificador aparece en más de un evento personal."""


class OrigenDesconocido(ValueError):
    """El origen (calendario) pedido no existe."""


class CategoriaDesconocida(ValueError):
    """La categoría pedida no existe en el calendario académico."""


class CalendarStore:
    """Repositorio de los calendarios académico (recurso) y personal (usuario).

    Las rutas solo se indican para inyectar archivos alternativos en pruebas;
    en producción se resuelven con ``resource_path`` y ``user_calendar_path``.
    """

    def __init__(
        self,
        ruta_personal: Path | str | None = None,
        ruta_academico: Path | str | None = None,
    ) -> None:
        self.ruta_personal = (
            Path(ruta_personal)
            if ruta_personal is not None
            else user_calendar_path()
        )
        self.ruta_academico = (
            Path(ruta_academico)
            if ruta_academico is not None
            else resource_path(RECURSO_CALENDARIO)
        )

    # --- consulta ---

    def listar(
        self,
        origen: str,
        fecha_inicio: date | None = None,
        fecha_fin: date | None = None,
        categorias: set[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Devuelve los eventos del calendario ``origen`` que caen en el rango.

        ``categorias`` restringe el resultado a esas categorías; ``None`` las
        incluye todas. El calendario personal inexistente equivale a vacío.

        Lanza ``OrigenDesconocido`` si el origen no existe y
        ``CategoriaDesconocida`` si alguna categoría pedida no existe.
        """
        if origen not in ORIGENES:
            raise OrigenDesconocido(
                f"Origen inválido: {origen!r}. Usa uno de estos: "
                f"{', '.join(ORIGENES)}."
            )
        if categorias is not None:
            self._validar_categorias(categorias)

        contenido = self._leer(origen)
        return _parsear_eventos(
            contenido, origen, fecha_inicio, fecha_fin, categorias
        )

    def categorias_disponibles(self) -> set[str]:
        """Devuelve las categorías presentes en el calendario académico."""
        return _extraer_categorias(self._leer("academico"))

    # --- escritura ---

    def agregar(
        self,
        titulo: str,
        inicio: date,
        fin: date | None = None,
        descripcion: str = "",
        hora_inicio: time | None = None,
        hora_fin: time | None = None,
    ) -> str:
        """Añade un evento al calendario personal y devuelve su UID.

        ``titulo``, ``descripcion`` y las fechas ya vienen validados por
        ``core``; aquí solo se serializa y se persiste. Si se omite ``fin``,
        el evento dura un solo día.
        """
        if fin is None:
            fin = inicio
        contenido = self._leer_para_agregar()
        identificador = f"{uuid.uuid4()}@aethera"
        evento = _construir_vevent(
            identificador, inicio, fin, titulo, descripcion, hora_inicio, hora_fin
        )
        nuevo_contenido = (
            contenido.rstrip("\r\n")
            + "\r\n"
            + "\r\n".join(_plegar_linea_ics(linea) for linea in evento)
            + "\r\nEND:VCALENDAR\r\n"
        )
        self._guardar(nuevo_contenido)
        return identificador

    def eliminar(self, uid: str) -> None:
        """Elimina un evento personal por su UID.

        Lanza ``CalendarioInvalido`` si el archivo no es válido y
        ``EventoNoEncontrado``/``EventoAmbiguo`` según corresponda.
        """
        contenido = self.ruta_personal.read_text(encoding="utf-8")
        lineas = contenido.replace("\r\n", "\n").replace("\r", "\n").splitlines()
        if (
            not lineas
            or lineas[0] != "BEGIN:VCALENDAR"
            or lineas[-1] != "END:VCALENDAR"
        ):
            raise CalendarioInvalido(
                "El archivo de calendario personal no es válido."
            )

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
                raise CalendarioInvalido(
                    "El calendario contiene un evento ICS incompleto."
                )
            bloque = lineas[indice : fin_evento + 1]
            desplegado = _desplegar_lineas(bloque)
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
            raise EventoNoEncontrado(
                "No se encontró ese evento en el calendario Personal."
            )
        if len(bloques_eventos) > 1:
            raise EventoAmbiguo(
                "El identificador aparece en varios eventos; "
                "no se eliminó ninguno."
            )

        inicio_bloque, fin_bloque = bloques_eventos[0]
        del lineas[inicio_bloque:fin_bloque]
        self._guardar("\r\n".join(lineas) + "\r\n")

    # --- internos ---

    def _validar_categorias(self, categorias: set[str]) -> None:
        disponibles = self.categorias_disponibles()
        desconocidas = {categoria.lower() for categoria in categorias}
        desconocidas -= disponibles | {ORIGEN_EDITABLE}
        if desconocidas:
            raise CategoriaDesconocida(
                f"Categoría inválida: {', '.join(sorted(desconocidas))}. Usa una "
                f"de estas: {', '.join(sorted(disponibles))}."
            )

    def _leer(self, origen: str) -> str:
        if origen == "personal":
            try:
                return self.ruta_personal.read_text(encoding="utf-8")
            except FileNotFoundError:
                return ""
        try:
            return self.ruta_academico.read_text(encoding="utf-8")
        except FileNotFoundError:
            raise OSError("No se encontró el calendario académico.")

    def _leer_para_agregar(self) -> str:
        try:
            contenido = self.ruta_personal.read_text(encoding="utf-8")
        except FileNotFoundError:
            contenido = ""
        if not contenido.strip():
            return CABECERA_PERSONAL
        lineas_calendario = (
            contenido.replace("\r\n", "\n").replace("\r", "\n").splitlines()
        )
        if (
            not lineas_calendario
            or lineas_calendario[0] != "BEGIN:VCALENDAR"
            or lineas_calendario[-1] != "END:VCALENDAR"
        ):
            raise CalendarioInvalido(
                "El archivo de calendario personal no es válido."
            )
        return "\r\n".join(lineas_calendario[:-1])

    def _guardar(self, contenido: str) -> None:
        ruta = self.ruta_personal
        ruta.parent.mkdir(parents=True, exist_ok=True)
        temporal = None
        try:
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
                archivo.write(contenido)
            os.replace(temporal, ruta)
        finally:
            if temporal and os.path.exists(temporal):
                os.unlink(temporal)


def origenes_disponibles() -> tuple[str, ...]:
    """Devuelve los orígenes (calendarios) disponibles."""
    return ORIGENES


def categorias_disponibles(store: "CalendarStore | None" = None) -> set[str]:
    """Devuelve las categorías del calendario académico."""
    return (store if store is not None else CalendarStore()).categorias_disponibles()


def _extraer_categorias(contenido: str) -> set[str]:
    """Recopila los valores de la propiedad ICS ``CATEGORIES``."""
    categorias: set[str] = set()
    for linea in _desplegar_lineas(contenido.splitlines()):
        if linea.startswith("CATEGORIES:"):
            for valor in linea.split(":", 1)[1].split(","):
                valor = valor.strip().lower()
                if valor:
                    categorias.add(valor)
    return categorias


def _desplegar_lineas(lineas: list[str]) -> list[str]:
    """Une las líneas de continuación del plegado ICS."""
    desplegadas = []
    for linea in lineas:
        if linea.startswith((" ", "\t")) and desplegadas:
            desplegadas[-1] += linea[1:]
        else:
            desplegadas.append(linea)
    return desplegadas


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


def _parsear_eventos(
    contenido: str,
    origen: str,
    fecha_inicio: date | None,
    fecha_fin: date | None,
    categorias: set[str] | None,
) -> list[dict[str, Any]]:
    lineas_plegadas = _desplegar_lineas(contenido.splitlines())
    categorias_normalizadas = (
        None
        if categorias is None
        else {categoria.lower() for categoria in categorias}
    )

    eventos_encontrados = []
    evento_actual: dict[str, Any] = {}
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
                categorias_normalizadas is None
                or categoria.lower() in categorias_normalizadas
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

            dentro_de_rango = (
                (fecha_fin is None or inicio_fecha <= fecha_fin)
                and (fecha_inicio is None or fin_fecha >= fecha_inicio)
            )
            if dentro_de_rango:
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
                        "editable": origen == ORIGEN_EDITABLE,
                    }
                )
        elif en_evento and ":" in linea:
            clave_completa, valor = linea.split(":", 1)
            clave = clave_completa.split(";")[0]
            evento_actual[clave] = valor

            if clave in ("DTSTART", "DTEND"):
                try:
                    if "VALUE=DATE" in clave_completa or len(valor) == 8:
                        objeto: date | datetime = datetime.strptime(
                            valor, "%Y%m%d"
                        ).date()
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


def _construir_vevent(
    identificador: str,
    inicio: date,
    fin: date,
    titulo: str,
    descripcion: str,
    hora_inicio: time | None,
    hora_fin: time | None,
) -> list[str]:
    if hora_inicio is not None and hora_fin is not None:
        fecha_hora_inicio = datetime.combine(inicio, hora_inicio)
        fecha_hora_fin = datetime.combine(fin, hora_fin)
        propiedad_inicio = f"DTSTART:{fecha_hora_inicio.strftime('%Y%m%dT%H%M%S')}"
        propiedad_fin = f"DTEND:{fecha_hora_fin.strftime('%Y%m%dT%H%M%S')}"
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
    return evento
