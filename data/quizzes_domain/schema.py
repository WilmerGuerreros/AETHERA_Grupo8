"""Validación, construcción y extracción de quizzes, reglas de Data."""

import ast
import json
import re
import string
import time
from typing import Any


_QUIZ_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,79}$")
_QUIZ_KEYS = {"quiz_id", "quiz_titulo", "paginas"}
_ALTERNATIVE_PAGE_KEYS = {
    "tipo",
    "pregunta",
    "alternativas",
    "retroalimentacion",
    "respuesta_correcta",
}
_DEVELOPMENT_PAGE_KEYS = {
    "tipo",
    "pregunta",
    "guia_evaluacion",
    "respuesta_sugerida",
}


def _validar_texto(valor: Any, campo: str) -> str:
    if not isinstance(valor, str) or not valor.strip():
        raise ValueError(f"'{campo}' debe ser texto no vacío.")
    return valor.strip()


def crear_quiz(title: str, pages: list[list[Any]]) -> dict[str, Any]:
    """Valida el formato compacto y devuelve los datos del quiz."""
    if not isinstance(pages, list) or not pages:
        raise ValueError("pages debe ser una lista con al menos una pregunta.")

    paginas_quiz: list[dict[str, Any]] = []
    for indice, page in enumerate(pages, start=1):
        if not isinstance(page, list) or not page:
            raise ValueError(f"pages[{indice - 1}] debe ser una lista no vacía.")

        tipo = page[0]
        if tipo == "alternative":
            if len(page) != 5:
                raise ValueError(
                    f"pages[{indice - 1}] de alternativas debe tener "
                    "5 elementos, incluida la explicación de la respuesta correcta."
                )
            _, pregunta, opciones, respuesta_correcta, explicacion_correcta = page
            if not isinstance(opciones, list) or not 2 <= len(opciones) <= 26:
                raise ValueError(
                    f"pages[{indice - 1}] debe incluir entre 2 y 26 opciones."
                )
            if not all(
                isinstance(opcion, str) and opcion.strip()
                for opcion in opciones
            ):
                raise ValueError(
                    f"Todas las opciones de pages[{indice - 1}] "
                    "deben ser textos no vacíos."
                )
            if (
                not isinstance(respuesta_correcta, str)
                or not respuesta_correcta.strip()
            ):
                raise ValueError(
                    f"pages[{indice - 1}] debe indicar el texto de la "
                    "respuesta correcta."
                )
            explicacion_correcta = _validar_texto(
                explicacion_correcta,
                f"pages[{indice - 1}].explicacion_correcta",
            )
            claves = string.ascii_uppercase[: len(opciones)]
            alternativas = dict(zip(claves, opciones))
            coincidencias = [
                clave
                for clave, opcion in alternativas.items()
                if opcion.strip() == respuesta_correcta.strip()
            ]
            if len(coincidencias) != 1:
                raise ValueError(
                    f"El texto correcto de pages[{indice - 1}] debe "
                    "coincidir con exactamente una alternativa."
                )
            clave_correcta = coincidencias[0]
            paginas_quiz.append(
                {
                    "tipo": "alternativa",
                    "pregunta": pregunta,
                    "alternativas": alternativas,
                    "retroalimentacion": {
                        clave: (
                            explicacion_correcta
                            if clave == clave_correcta
                            else f"Incorrecto. {explicacion_correcta}"
                        )
                        for clave in claves
                    },
                    "respuesta_correcta": clave_correcta,
                }
            )
        elif tipo == "develope":
            if len(page) != 4:
                raise ValueError(
                    f"pages[{indice - 1}] de desarrollo debe tener "
                    "4 elementos."
                )
            _, pregunta, guia_orientativa, palabras_clave = page
            paginas_quiz.append(
                {
                    "tipo": "desarrollo",
                    "pregunta": pregunta,
                    "guia_evaluacion": guia_orientativa,
                    "respuesta_sugerida": palabras_clave,
                }
            )
        else:
            raise ValueError(
                f"pages[{indice - 1}] debe comenzar con 'alternative' "
                "o 'develope'."
            )

    return {
        "quiz_id": f"quiz_{time.time_ns()}",
        "quiz_titulo": title,
        "paginas": paginas_quiz,
    }


def validar_quiz(datos: dict[str, Any] | str) -> dict[str, Any]:
    """Interpreta y valida el esquema acordado para un quiz educativo."""
    if isinstance(datos, str):
        try:
            datos = json.loads(datos)
        except json.JSONDecodeError as error:
            raise ValueError(f"El JSON del quiz no es válido: {error.msg}.") from error

    if not isinstance(datos, dict):
        raise ValueError("El quiz debe ser un objeto JSON.")
    if set(datos) != _QUIZ_KEYS:
        faltantes = sorted(_QUIZ_KEYS - set(datos))
        adicionales = sorted(set(datos) - _QUIZ_KEYS)
        detalle = []
        if faltantes:
            detalle.append(f"faltan claves: {', '.join(faltantes)}")
        if adicionales:
            detalle.append(f"claves no permitidas: {', '.join(adicionales)}")
        raise ValueError(f"El esquema del quiz no es válido ({'; '.join(detalle)}).")

    quiz_id = _validar_texto(datos["quiz_id"], "quiz_id")
    if not _QUIZ_ID_PATTERN.fullmatch(quiz_id):
        raise ValueError(
            "'quiz_id' debe comenzar con una letra o número y contener "
            "solo letras, números, guiones o guiones bajos (máximo 80 caracteres)."
        )

    titulo = _validar_texto(datos["quiz_titulo"], "quiz_titulo")
    paginas = datos["paginas"]
    if not isinstance(paginas, list) or not paginas:
        raise ValueError("'paginas' debe ser una lista con al menos una pregunta.")

    paginas_validadas = []
    ids_pagina = set()
    for indice, pagina in enumerate(paginas, start=1):
        campo_pagina = f"paginas[{indice - 1}]"
        if not isinstance(pagina, dict):
            raise ValueError(f"'{campo_pagina}' debe ser un objeto.")

        tipo = pagina.get("tipo")
        if tipo == "alternativa":
            claves_esperadas = _ALTERNATIVE_PAGE_KEYS
        elif tipo == "desarrollo":
            claves_esperadas = _DEVELOPMENT_PAGE_KEYS
        else:
            raise ValueError(
                f"'{campo_pagina}.tipo' debe ser 'alternativa' o 'desarrollo'."
            )
        claves_recibidas = set(pagina)
        if claves_recibidas not in (claves_esperadas, claves_esperadas | {"id"}):
            faltantes = sorted(claves_esperadas - set(pagina))
            adicionales = sorted(claves_recibidas - claves_esperadas - {"id"})
            detalle = []
            if faltantes:
                detalle.append(f"faltan claves: {', '.join(faltantes)}")
            if adicionales:
                detalle.append(f"claves no permitidas: {', '.join(adicionales)}")
            raise ValueError(
                f"El esquema de '{campo_pagina}' no es válido "
                f"({'; '.join(detalle)})."
            )

        page_id = _validar_texto(
            pagina.get("id", f"p{indice}"),
            f"{campo_pagina}.id",
        )
        if page_id in ids_pagina:
            raise ValueError(f"El id '{page_id}' está repetido en 'paginas'.")
        ids_pagina.add(page_id)
        pagina_validada: dict[str, Any] = {
            "id": page_id,
            "tipo": tipo,
            "pregunta": _validar_texto(
                pagina["pregunta"], f"{campo_pagina}.pregunta"
            ),
        }

        if tipo == "alternativa":
            alternativas = pagina["alternativas"]
            retroalimentacion = pagina["retroalimentacion"]
            if not isinstance(alternativas, dict) or len(alternativas) < 2:
                raise ValueError(
                    f"'{campo_pagina}.alternativas' debe tener al menos dos opciones."
                )
            if not all(
                isinstance(clave, str) and re.fullmatch(r"[A-Z]", clave)
                for clave in alternativas
            ):
                raise ValueError(
                    f"Las claves de '{campo_pagina}.alternativas' "
                    "deben ser letras mayúsculas individuales."
                )
            alternativas_validadas = {
                clave: _validar_texto(
                    valor, f"{campo_pagina}.alternativas.{clave}"
                )
                for clave, valor in alternativas.items()
            }
            if not isinstance(retroalimentacion, dict):
                raise ValueError(
                    f"'{campo_pagina}.retroalimentacion' debe ser un objeto."
                )
            if set(retroalimentacion) != set(alternativas):
                raise ValueError(
                    f"'{campo_pagina}.retroalimentacion' debe tener una "
                    "entrada por cada alternativa y ninguna adicional."
                )
            retroalimentacion_validada = {
                clave: _validar_texto(
                    valor, f"{campo_pagina}.retroalimentacion.{clave}"
                )
                for clave, valor in retroalimentacion.items()
            }
            respuesta_correcta = _validar_texto(
                pagina["respuesta_correcta"],
                f"{campo_pagina}.respuesta_correcta",
            )
            if respuesta_correcta not in alternativas_validadas:
                raise ValueError(
                    f"'{campo_pagina}.respuesta_correcta' debe coincidir "
                    "con una clave de alternativas."
                )
            pagina_validada.update(
                {
                    "alternativas": alternativas_validadas,
                    "retroalimentacion": retroalimentacion_validada,
                    "respuesta_correcta": respuesta_correcta,
                }
            )
        else:
            pagina_validada.update(
                {
                    "guia_evaluacion": _validar_texto(
                        pagina["guia_evaluacion"],
                        f"{campo_pagina}.guia_evaluacion",
                    ),
                    "respuesta_sugerida": _validar_texto(
                        pagina["respuesta_sugerida"],
                        f"{campo_pagina}.respuesta_sugerida",
                    ),
                }
            )
        paginas_validadas.append(pagina_validada)

    return {
        "quiz_id": quiz_id,
        "quiz_titulo": titulo,
        "paginas": paginas_validadas,
    }


def _validar_quiz_id(quiz_id: str) -> None:
    if not isinstance(quiz_id, str) or not _QUIZ_ID_PATTERN.fullmatch(quiz_id):
        raise ValueError("El identificador del quiz no es válido.")


def _validar_respuestas_intento(
    quiz: dict[str, Any],
    respuestas: dict[str, str],
) -> None:
    paginas = {pagina["id"]: pagina for pagina in quiz["paginas"]}
    for pregunta_id, respuesta in respuestas.items():
        pagina = paginas.get(pregunta_id)
        if pagina is None or not isinstance(respuesta, str):
            raise ValueError(f"Hay una respuesta inválida en '{pregunta_id}'.")
        if (
            pagina["tipo"] == "alternativa"
            and respuesta not in pagina["alternativas"]
        ):
            raise ValueError(
                f"La respuesta para '{pregunta_id}' no es válida."
            )


def quiz_desde_mensaje(texto: str) -> dict[str, Any] | None:
    """Extrae un quiz válido desde un mensaje del agente."""
    decoder = json.JSONDecoder()
    for match in re.finditer(r"\{", texto):
        try:
            candidato, _ = decoder.raw_decode(texto[match.start():])
            return validar_quiz(candidato)
        except (json.JSONDecodeError, ValueError):
            continue
    return None


def quiz_desde_resultado_herramienta(texto: str) -> dict[str, Any] | None:
    """Extrae los datos de un quiz del resultado serializado de una herramienta."""
    try:
        resultado = ast.literal_eval(texto)
    except (SyntaxError, ValueError):
        return None
    if not isinstance(resultado, dict) or "quiz_data" not in resultado:
        return None
    try:
        return validar_quiz(resultado["quiz_data"])
    except ValueError:
        return None


__all__ = [
    "_validar_quiz_id",
    "_validar_respuestas_intento",
    "crear_quiz",
    "quiz_desde_mensaje",
    "quiz_desde_resultado_herramienta",
    "validar_quiz",
]
