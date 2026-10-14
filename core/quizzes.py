"""Construcción, validación y reglas de corrección de quizzes."""

import json
import ast
import logging
import re
import string
import time
from pathlib import Path
from typing import Any

from data.paths import quizzes_directory
from data.quizzes import (
    eliminar_intento_quiz as eliminar_intento_persistido,
    guardar_intento_quiz,
    guardar_quiz_json,
    guardar_resultado_quiz,
    leer_intento_quiz,
    leer_quiz_json,
    listar_archivos_quiz,
)


DIRECTORIO_QUICES = quizzes_directory()
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


def _validar_texto(valor: Any, campo: str) -> str:
    if not isinstance(valor, str) or not valor.strip():
        raise ValueError(f"'{campo}' debe ser texto no vacío.")
    return valor.strip()


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


class QuizSession:
    """Mantiene en memoria las respuestas de un intento de quiz."""

    def __init__(self, quiz: dict[str, Any]):
        self.quiz = validar_quiz(quiz)
        self._respuestas_desarrollo: dict[str, str] = {}
        self._paginas = {pagina["id"]: pagina for pagina in self.quiz["paginas"]}

    @property
    def respuestas_desarrollo(self) -> dict[str, str]:
        """Devuelve una copia de las respuestas abiertas recibidas hasta ahora."""
        return self._respuestas_desarrollo.copy()

    def responder_alternativa(
        self, pregunta_id: str, respuesta: str
    ) -> dict[str, bool | str]:
        """Evalúa una alternativa y devuelve su corrección y retroalimentación."""
        pagina = self._obtener_pregunta(pregunta_id, "alternativa")
        if not isinstance(respuesta, str):
            raise ValueError("La respuesta debe ser una clave de alternativa.")
        respuesta = respuesta.strip()
        retroalimentacion = pagina["retroalimentacion"]
        if respuesta not in pagina["alternativas"]:
            raise ValueError(
                f"La opción '{respuesta}' no existe para la pregunta '{pregunta_id}'."
            )
        return {
            "correcta": respuesta == pagina["respuesta_correcta"],
            "retroalimentacion": retroalimentacion[respuesta],
        }

    def guardar_respuesta_desarrollo(
        self, pregunta_id: str, respuesta: str
    ) -> None:
        """Guarda o reemplaza la respuesta del alumno a una pregunta abierta."""
        self._obtener_pregunta(pregunta_id, "desarrollo")
        respuesta_validada = _validar_texto(
            respuesta, f"respuesta de la pregunta '{pregunta_id}'"
        )
        self._respuestas_desarrollo[pregunta_id] = respuesta_validada

    def preparar_evaluacion(self) -> str:
        """Consolida el quiz y respuestas abiertas en un JSON para el LLM."""
        respuestas = [
            {
                "pregunta_id": pagina["id"],
                "pregunta": pagina["pregunta"],
                "respuesta_alumno": self._respuestas_desarrollo[pagina["id"]],
                "guia_evaluacion": pagina["guia_evaluacion"],
                "respuesta_sugerida": pagina["respuesta_sugerida"],
            }
            for pagina in self.quiz["paginas"]
            if pagina["tipo"] == "desarrollo"
            and pagina["id"] in self._respuestas_desarrollo
        ]
        return json.dumps(
            {
                "quiz": self.quiz,
                "respuestas_desarrollo": respuestas,
            },
            ensure_ascii=False,
            indent=2,
        )

    def _obtener_pregunta(self, pregunta_id: str, tipo: str) -> dict[str, Any]:
        if not isinstance(pregunta_id, str) or pregunta_id not in self._paginas:
            raise ValueError(f"No existe una pregunta con id '{pregunta_id}'.")
        pagina = self._paginas[pregunta_id]
        if pagina["tipo"] != tipo:
            raise ValueError(
                f"La pregunta '{pregunta_id}' no es de tipo '{tipo}'."
            )
        return pagina


def evaluar_respuesta_alternativa(
    quiz: dict[str, Any],
    pregunta_id: str,
    respuesta: str,
) -> dict[str, bool | str]:
    """Devuelve la corrección de una alternativa para una pregunta."""
    return QuizSession(quiz).responder_alternativa(pregunta_id, respuesta)


def seleccionar_respuesta_alternativa(
    quiz: dict[str, Any],
    indice: int,
    respuestas: dict[str, str],
    pregunta_id: str,
    respuesta: str,
    directorio_intentos: Path | str | None = None,
) -> dict[str, Any]:
    """Evalúa y persiste una selección, sin permitir cambiar una respuesta."""
    quiz = validar_quiz(quiz)
    _validar_respuestas_intento(quiz, respuestas)
    intento_guardado = cargar_intento(quiz, directorio_intentos)
    respuestas_actualizadas = dict(respuestas)
    respuesta_previa = respuestas.get(pregunta_id)
    if intento_guardado is not None:
        respuesta_previa = intento_guardado["respuestas"].get(
            pregunta_id, respuesta_previa
        )
    if respuesta_previa is not None and respuesta_previa != respuesta:
        raise ValueError("La respuesta ya fue seleccionada y no se puede cambiar.")

    respuestas_actualizadas[pregunta_id] = respuesta
    resultado = evaluar_respuesta_alternativa(quiz, pregunta_id, respuesta)
    guardar_progreso_quiz(
        quiz,
        indice,
        respuestas_actualizadas,
        directorio_intentos,
    )
    return {
        **resultado,
        "respuesta": respuesta,
        "respuestas": respuestas_actualizadas,
    }


def guardar_progreso_quiz(
    quiz: dict[str, Any],
    indice: int,
    respuestas: dict[str, str],
    directorio_intentos: Path | str | None = None,
) -> dict[str, str]:
    """Persiste el avance enviado por la UI y devuelve las respuestas guardadas."""
    quiz = validar_quiz(quiz)
    _validar_respuestas_intento(quiz, respuestas)
    guardar_intento(
        quiz,
        indice,
        respuestas,
        directorio_intentos,
    )
    return dict(respuestas)


def resumir_quiz(quiz: dict[str, Any]) -> dict[str, int]:
    """Devuelve el conteo de preguntas por tipo para presentar un quiz."""
    quiz = validar_quiz(quiz)
    alternativas = sum(
        pagina["tipo"] == "alternativa" for pagina in quiz["paginas"]
    )
    return {
        "alternativas": alternativas,
        "desarrollo": len(quiz["paginas"]) - alternativas,
    }


def preparar_respuestas_desarrollo(
    quiz: dict[str, Any],
    respuestas: dict[str, str],
) -> list[dict[str, str]]:
    """Devuelve todas las preguntas abiertas junto con su respuesta, si existe."""
    quiz_validado = validar_quiz(quiz)
    desarrollo = []
    for pagina in quiz_validado["paginas"]:
        if pagina["tipo"] != "desarrollo":
            continue
        respuesta = respuestas.get(pagina["id"], "")
        desarrollo.append(
            {
                "pregunta_id": pagina["id"],
                "pregunta": pagina["pregunta"],
                "respuesta_alumno": respuesta,
                "guia_evaluacion": pagina["guia_evaluacion"],
                "respuesta_sugerida": pagina["respuesta_sugerida"],
            }
        )
    return desarrollo


def evaluar_quiz(
    motor: Any,
    quiz: dict[str, Any],
    respuestas: dict[str, str],
    historial_chat: list[dict[str, Any]] | None = None,
    directorio_intentos: Path | str | None = None,
) -> dict[str, Any]:
    """Orquesta evaluación, puntuación y feedback final del LLM."""
    from agent.quiz_evaluation import (
        evaluar_respuestas_desarrollo,
        generar_feedback_resultados,
    )

    quiz = validar_quiz(quiz)
    respuestas = guardar_progreso_quiz(
        quiz,
        0,
        respuestas,
        directorio_intentos,
    )
    desarrollo = preparar_respuestas_desarrollo(quiz, respuestas)
    evaluaciones_desarrollo = (
        evaluar_respuestas_desarrollo(
            motor,
            quiz["quiz_titulo"],
            desarrollo,
            historial_chat,
        )
        if any(pagina["tipo"] == "desarrollo" for pagina in quiz["paginas"])
        else []
    )
    resultado = construir_resultado_evaluacion(
        quiz,
        respuestas,
        evaluaciones_desarrollo,
    )
    resultado["feedback_final"] = generar_feedback_resultados(
        motor,
        historial_chat,
        quiz,
        resultado,
    )
    eliminar_intento(quiz["quiz_id"], directorio_intentos)
    return resultado


def finalizar_quiz(
    quiz_id: str | dict[str, Any],
    respuestas_usuario: dict[str, str] | None = None,
    origen: str = "barra_lateral",
    quiz: dict[str, Any] | None = None,
    motor: Any | None = None,
    historial_chat: list[dict[str, Any]] | None = None,
    directorio_intentos: Path | str | None = None,
    agent_session: Any | None = None,
) -> dict[str, Any]:
    """Finaliza un quiz y devuelve el resultado listo para la UI.

    Corrige las alternativas, envía en segundo plano las respuestas de
    desarrollo al modelo para que sean evaluadas, persiste el resultado final
    en Data e inyecta el resultado como contexto silencioso del agente cuando
    el quiz proviene del chat.
    """
    if quiz is not None:
        quiz_obj = validar_quiz(quiz)
    elif isinstance(quiz_id, dict):
        quiz_obj = validar_quiz(quiz_id)
    else:
        manager = QuizManager(
            Path(directorio_intentos) if directorio_intentos else DIRECTORIO_QUICES
        )
        quiz_obj = manager.cargar(quiz_id)

    if motor is None:
        raise ValueError("Se requiere un motor para evaluar el quiz.")

    resultado = evaluar_quiz(
        motor,
        quiz_obj,
        dict(respuestas_usuario or {}),
        historial_chat,
        directorio_intentos,
    )

    # Persistir el resultado final como metadato interno del quiz. Si el
    # guardado falla, igual se devuelve el resultado a la UI.
    try:
        guardar_resultado_quiz(
            quiz_obj["quiz_id"],
            resultado.get("porcentaje_total", 0),
            resultado.get("retroalimentacion", []),
            directorio_intentos,
        )
    except (OSError, ValueError):
        logging.exception("No se pudo guardar el resultado final del quiz.")

    # Compatibilidad con la estructura que consume la UI.
    resultado.setdefault("feedback_general", resultado.get("feedback_final", ""))
    resultado["puntaje_total"] = resultado.get("porcentaje_total", 0)
    resultado["detalle_evaluaciones"] = resultado.get("retroalimentacion", [])

    # Solo el chat inyecta el resultado como contexto silencioso del agente.
    if origen == "chat" and agent_session is not None:
        try:
            mensaje = (
                f"[QUIZ] {quiz_obj['quiz_titulo']} - Resultado: "
                f"{resultado.get('porcentaje_total', 0)}%"
            )
            if hasattr(agent_session, "agregar_contexto"):
                agent_session.agregar_contexto(mensaje)
        except Exception:
            logging.exception("No se pudo inyectar el resultado del quiz al agente.")

    return resultado


def cargar_intento(
    quiz: dict[str, Any],
    directorio_intentos: Path | str | None = None,
) -> dict[str, Any] | None:
    """Carga y valida el progreso guardado de un quiz."""
    quiz = validar_quiz(quiz)
    quiz_id = quiz["quiz_id"]
    _validar_quiz_id(quiz_id)
    directorio = Path(directorio_intentos) if directorio_intentos else DIRECTORIO_QUICES
    intento = leer_intento_quiz(directorio, quiz_id)
    if intento is None:
        return None
    if not isinstance(intento, dict):
        raise ValueError(f"El intento guardado de '{quiz_id}' no es válido.")
    paginas = {pagina["id"]: pagina for pagina in quiz["paginas"]}
    respuestas = intento.get("respuestas", {})
    if intento.get("quiz_id") != quiz_id or not isinstance(respuestas, dict):
        raise ValueError(f"El intento guardado de '{quiz_id}' no es válido.")
    for pregunta_id, respuesta in respuestas.items():
        pagina = paginas.get(pregunta_id)
        if pagina is None or not isinstance(respuesta, str):
            raise ValueError(f"Hay una respuesta inválida en '{pregunta_id}'.")
        if (
            pagina["tipo"] == "alternativa"
            and respuesta not in pagina["alternativas"]
        ):
            raise ValueError(
                f"La respuesta guardada para '{pregunta_id}' no es válida."
            )
    indice = intento.get("indice", 0)
    if not isinstance(indice, int) or isinstance(indice, bool):
        raise ValueError("El índice del intento guardado no es válido.")
    return {
        "indice": min(max(indice, 0), len(quiz["paginas"]) - 1),
        "respuestas": respuestas,
        "evaluaciones": {
            pregunta_id: evaluar_respuesta_alternativa(
                quiz, pregunta_id, respuesta
            )
            for pregunta_id, respuesta in respuestas.items()
            if paginas[pregunta_id]["tipo"] == "alternativa"
        },
    }


def guardar_intento(
    quiz: dict[str, Any],
    indice: int,
    respuestas: dict[str, str],
    directorio_intentos: Path | str | None = None,
) -> Path:
    """Valida y persiste el progreso de un quiz mediante Data."""
    quiz = validar_quiz(quiz)
    quiz_id = quiz["quiz_id"]
    _validar_quiz_id(quiz_id)
    if not isinstance(indice, int) or isinstance(indice, bool):
        raise ValueError("El índice del intento no es válido.")
    if not 0 <= indice < len(quiz["paginas"]):
        raise ValueError("El índice del intento está fuera del quiz.")
    if not isinstance(respuestas, dict):
        raise ValueError("Las respuestas del intento deben ser un objeto.")
    _validar_respuestas_intento(quiz, respuestas)
    directorio = Path(directorio_intentos) if directorio_intentos else DIRECTORIO_QUICES
    return guardar_intento_quiz(
        directorio,
        quiz_id,
        {
            "quiz_id": quiz_id,
            "indice": indice,
            "respuestas": respuestas,
        },
    )


def eliminar_intento(
    quiz_id: str,
    directorio_intentos: Path | str | None = None,
) -> None:
    """Elimina el progreso persistido de un quiz mediante Data."""
    _validar_quiz_id(quiz_id)
    directorio = Path(directorio_intentos) if directorio_intentos else DIRECTORIO_QUICES
    eliminar_intento_persistido(directorio, quiz_id)


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


def construir_resultado_evaluacion(
    quiz: dict[str, Any],
    respuestas: dict[str, str],
    evaluaciones_desarrollo: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Aplica reglas de corrección y calcula puntajes del quiz."""
    quiz = validar_quiz(quiz)
    session = QuizSession(quiz)
    alternativas = []
    retroalimentacion = []
    total_alternativas = sum(
        pagina["tipo"] == "alternativa" for pagina in quiz["paginas"]
    )
    total_desarrollo = len(quiz["paginas"]) - total_alternativas

    for pagina in quiz["paginas"]:
        pregunta_id = pagina["id"]
        respuesta = respuestas.get(pregunta_id, "")
        if pagina["tipo"] == "alternativa":
            if respuesta:
                resultado = session.responder_alternativa(pregunta_id, respuesta)
                correcta = resultado["correcta"]
                feedback = resultado["retroalimentacion"]
            else:
                correcta = False
                feedback = "Pregunta sin responder."
            alternativas.append(
                {
                    "pregunta_id": pregunta_id,
                    "correcta": correcta,
                    "retroalimentacion": feedback,
                }
            )

    evaluaciones_desarrollo = evaluaciones_desarrollo or []
    if len(evaluaciones_desarrollo) != total_desarrollo:
        if total_desarrollo:
            raise ValueError("Faltan evaluaciones para las preguntas de desarrollo.")
    retroalimentacion.extend(evaluaciones_desarrollo)

    feedback_por_id = {
        item["pregunta_id"]: item
        for item in [*alternativas, *retroalimentacion]
    }
    correctas_alternativas = sum(item["correcta"] for item in alternativas)
    desarrollo_porcentaje = [
        feedback_por_id[pagina["id"]]["porcentaje"]
        for pagina in quiz["paginas"]
        if pagina["tipo"] == "desarrollo"
    ]
    puntos_totales = 0
    for pagina in quiz["paginas"]:
        resultado_pregunta = feedback_por_id[pagina["id"]]
        if pagina["tipo"] == "alternativa":
            puntos_totales += 100 if resultado_pregunta["correcta"] else 0
        else:
            puntos_totales += resultado_pregunta["porcentaje"]
    return {
        "porcentaje_total": round(puntos_totales / len(quiz["paginas"])),
        "puntaje": (
            round(correctas_alternativas / total_alternativas * 100)
            if total_alternativas
            else None
        ),
        "correctas_alternativas": correctas_alternativas,
        "total_alternativas": total_alternativas,
        "porcentaje_desarrollo": (
            round(sum(desarrollo_porcentaje) / total_desarrollo)
            if total_desarrollo
            else None
        ),
        "retroalimentacion": [
            feedback_por_id[pagina["id"]] for pagina in quiz["paginas"]
        ],
    }


class QuizManager:
    """Valida, guarda, lista y carga quizzes desde disco."""

    def __init__(self, directorio: Path | str = DIRECTORIO_QUICES):
        self.directorio = Path(directorio)

    def guardar(self, datos: dict[str, Any] | str) -> dict[str, str]:
        """Guarda un quiz UTF-8 en el directorio configurado, sin sobrescribir."""
        quiz = validar_quiz(datos)
        ruta_destino = self.directorio / f"{quiz['quiz_id']}.json"
        try:
            ruta_destino = guardar_quiz_json(self.directorio, quiz)
        except FileExistsError as error:
            raise FileExistsError(
                f"Ya existe un quiz con el id '{quiz['quiz_id']}'. No se sobrescribió."
            ) from error
        except OSError:
            logging.exception("No se pudo guardar el quiz.")
            raise

        return {"quiz_id": quiz["quiz_id"], "ruta": str(ruta_destino)}

    def listar(self) -> list[dict[str, Any]]:
        """Lee y valida todos los quizzes JSON de la carpeta de almacenamiento."""
        quizzes = []
        for ruta in listar_archivos_quiz(self.directorio):
            try:
                quizzes.append(validar_quiz(leer_quiz_json(ruta)))
            except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
                raise ValueError(f"No se pudo cargar el quiz '{ruta.name}': {error}") from error
        return quizzes

    def cargar(self, quiz_id: str) -> dict[str, Any]:
        """Carga un quiz guardado por identificador y valida sus datos."""
        if not isinstance(quiz_id, str) or not _QUIZ_ID_PATTERN.fullmatch(quiz_id):
            raise ValueError("El identificador del quiz no tiene un formato válido.")
        ruta = self.directorio / f"{quiz_id}.json"
        try:
            quiz = validar_quiz(leer_quiz_json(ruta))
        except FileNotFoundError as error:
            raise FileNotFoundError(f"No existe el quiz '{quiz_id}'.") from error
        except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
            raise ValueError(f"No se pudo cargar el quiz '{quiz_id}': {error}") from error
        if quiz["quiz_id"] != quiz_id:
            raise ValueError(
                f"El id del archivo '{ruta.name}' no coincide con el contenido del quiz."
            )
        return quiz

    def iniciar(self, quiz_id: str) -> QuizSession:
        """Carga un quiz y crea una sesión local de respuestas."""
        return QuizSession(self.cargar(quiz_id))


def guardar_quiz(datos: dict[str, Any] | str) -> dict[str, str]:
    """Función compatible para guardar un quiz en los datos persistentes del usuario."""
    return QuizManager().guardar(datos)


def listar_quices() -> list[dict[str, Any]]:
    """Devuelve los quizzes guardados en los datos persistentes del usuario."""
    return QuizManager().listar()


def crear_y_guardar_quiz(title: str, pages: list[list[Any]]) -> dict[str, str]:
    """Construye, valida y guarda el quiz generado por una herramienta."""
    return QuizManager().guardar(crear_quiz(title, pages))
