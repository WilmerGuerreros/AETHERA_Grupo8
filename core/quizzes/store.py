"""Persistencia del avance y de los quizzes mediante el repositorio de Data."""

import json
import logging
from pathlib import Path
from typing import Any

from data.quizzes import QuizStore

from .schema import (
    _QUIZ_ID_PATTERN,
    _validar_quiz_id,
    _validar_respuestas_intento,
    validar_quiz,
)
from .session import QuizSession, evaluar_respuesta_alternativa


def _resolver_store(store: QuizStore | None) -> QuizStore:
    """Devuelve el repositorio de quizzes indicado o el de producción."""
    return store if store is not None else QuizStore()


def cargar_intento(
    quiz: dict[str, Any],
    store: QuizStore | None = None,
) -> dict[str, Any] | None:
    """Carga y valida el progreso guardado de un quiz."""
    quiz = validar_quiz(quiz)
    quiz_id = quiz["quiz_id"]
    _validar_quiz_id(quiz_id)
    intento = _resolver_store(store).leer_avance(quiz_id)
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
    store: QuizStore | None = None,
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
    return _resolver_store(store).guardar_avance(
        quiz_id,
        {
            "quiz_id": quiz_id,
            "indice": indice,
            "respuestas": respuestas,
        },
    )


def eliminar_intento(
    quiz_id: str,
    store: QuizStore | None = None,
) -> None:
    """Elimina el progreso persistido de un quiz mediante Data."""
    _validar_quiz_id(quiz_id)
    _resolver_store(store).eliminar_avance(quiz_id)


def guardar_progreso_quiz(
    quiz: dict[str, Any],
    indice: int,
    respuestas: dict[str, str],
    store: QuizStore | None = None,
) -> dict[str, str]:
    """Persiste el avance enviado por la UI y devuelve las respuestas guardadas."""
    quiz = validar_quiz(quiz)
    _validar_respuestas_intento(quiz, respuestas)
    guardar_intento(quiz, indice, respuestas, store)
    return dict(respuestas)


def seleccionar_respuesta_alternativa(
    quiz: dict[str, Any],
    indice: int,
    respuestas: dict[str, str],
    pregunta_id: str,
    respuesta: str,
    store: QuizStore | None = None,
) -> dict[str, Any]:
    """Evalúa y persiste una selección, sin permitir cambiar una respuesta."""
    quiz = validar_quiz(quiz)
    _validar_respuestas_intento(quiz, respuestas)
    intento_guardado = cargar_intento(quiz, store)
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
    guardar_progreso_quiz(quiz, indice, respuestas_actualizadas, store)
    return {
        **resultado,
        "respuesta": respuesta,
        "respuestas": respuestas_actualizadas,
    }


class QuizManager:
    """Valida, guarda, lista y carga quizzes usando un repositorio de Data."""

    def __init__(self, store: QuizStore | None = None):
        self.store = _resolver_store(store)

    def guardar(self, datos: dict[str, Any] | str) -> dict[str, str]:
        """Guarda un quiz validado, sin sobrescribir el archivo existente."""
        quiz = validar_quiz(datos)
        try:
            ruta_destino = self.store.guardar(quiz)
        except FileExistsError as error:
            raise FileExistsError(
                f"Ya existe un quiz con el id '{quiz['quiz_id']}'. No se sobrescribió."
            ) from error
        except OSError:
            logging.exception("No se pudo guardar el quiz.")
            raise

        return {"quiz_id": quiz["quiz_id"], "ruta": str(ruta_destino)}

    def listar(self) -> list[dict[str, Any]]:
        """Lee y valida todos los quizzes almacenados."""
        quizzes = []
        for datos in self.store.listar():
            try:
                quizzes.append(validar_quiz(datos))
            except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
                identificador = (
                    datos.get("quiz_id") if isinstance(datos, dict) else None
                )
                raise ValueError(
                    f"No se pudo cargar el quiz '{identificador or 'desconocido'}': "
                    f"{error}"
                ) from error
        return quizzes

    def cargar(self, quiz_id: str) -> dict[str, Any]:
        """Carga un quiz guardado por identificador y valida sus datos."""
        if not isinstance(quiz_id, str) or not _QUIZ_ID_PATTERN.fullmatch(quiz_id):
            raise ValueError("El identificador del quiz no tiene un formato válido.")
        try:
            quiz = validar_quiz(self.store.cargar(quiz_id))
        except FileNotFoundError as error:
            raise FileNotFoundError(f"No existe el quiz '{quiz_id}'.") from error
        except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
            raise ValueError(f"No se pudo cargar el quiz '{quiz_id}': {error}") from error
        if quiz["quiz_id"] != quiz_id:
            raise ValueError(
                "El id del quiz no coincide con el contenido del archivo."
            )
        return quiz

    def iniciar(self, quiz_id: str) -> QuizSession:
        """Carga un quiz y crea una sesión local de respuestas."""
        return QuizSession(self.cargar(quiz_id))


def guardar_quiz(datos: dict[str, Any] | str) -> dict[str, str]:
    """Guarda un quiz validado en los datos persistentes del usuario."""
    return QuizManager().guardar(datos)


def listar_quices() -> list[dict[str, Any]]:
    """Devuelve los quizzes guardados en los datos persistentes del usuario."""
    return QuizManager().listar()
