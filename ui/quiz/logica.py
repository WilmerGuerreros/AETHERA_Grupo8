"""Operaciones de carga, continuidad y evaluación de quizzes."""

import json
import ast
import re
from pathlib import Path
from typing import Any

from dominio.quices import QuizManager, QuizSession, validar_test


class QuizLogic:
    def __init__(self, motor, directorio_intentos: Path | None = None):
        self.motor = motor
        self.manager = QuizManager()
        self.directorio_intentos = directorio_intentos or (
            self.manager.directorio / ".intentos"
        )

    def listar_quices(self) -> list[dict[str, Any]]:
        return self.manager.listar()

    def cargar_intento(self, quiz: dict[str, Any]) -> dict[str, Any] | None:
        ruta = self._ruta_intento(quiz["test_id"])
        try:
            intento = json.loads(ruta.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return None
        except (OSError, json.JSONDecodeError) as error:
            raise ValueError(f"No se pudo leer el intento guardado: {error}") from error

        if not isinstance(intento, dict):
            raise ValueError(f"El intento guardado de '{quiz['test_id']}' no es válido.")
        paginas = {pagina["id"]: pagina for pagina in quiz["paginas"]}
        respuestas = intento.get("respuestas", {})
        if intento.get("test_id") != quiz["test_id"] or not isinstance(respuestas, dict):
            raise ValueError(f"El intento guardado de '{quiz['test_id']}' no es válido.")
        for pregunta_id, respuesta in respuestas.items():
            pagina = paginas.get(pregunta_id)
            if pagina is None or not isinstance(respuesta, str):
                raise ValueError(f"Hay una respuesta inválida en '{pregunta_id}'.")
            if pagina["tipo"] == "alternativa" and respuesta not in pagina["alternativas"]:
                raise ValueError(f"La respuesta guardada para '{pregunta_id}' no es válida.")
        indice = intento.get("indice", 0)
        if not isinstance(indice, int) or isinstance(indice, bool):
            raise ValueError("El índice del intento guardado no es válido.")
        return {
            "indice": min(max(indice, 0), len(quiz["paginas"]) - 1),
            "respuestas": respuestas,
        }

    def guardar_intento(
        self,
        quiz: dict[str, Any],
        indice: int,
        respuestas: dict[str, str],
    ) -> None:
        self.directorio_intentos.mkdir(parents=True, exist_ok=True)
        ruta = self._ruta_intento(quiz["test_id"])
        ruta.write_text(
            json.dumps(
                {
                    "test_id": quiz["test_id"],
                    "indice": indice,
                    "respuestas": respuestas,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

    def eliminar_intento(self, test_id: str) -> None:
        ruta = self._ruta_intento(test_id)
        try:
            ruta.unlink()
        except FileNotFoundError:
            pass

    def evaluar(
        self,
        quiz: dict[str, Any],
        respuestas: dict[str, str],
    ) -> dict[str, Any]:
        quiz = validar_test(quiz)
        session = QuizSession(quiz)
        alternativas = []
        desarrollo = []
        total_alternativas = sum(
            pagina["tipo"] == "alternativa" for pagina in quiz["paginas"]
        )
        total_desarrollo = len(quiz["paginas"]) - total_alternativas
        retroalimentacion = []

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
            else:
                if respuesta.strip():
                    session.guardar_respuesta_desarrollo(pregunta_id, respuesta)
                    desarrollo.append(
                        {
                            "pregunta_id": pregunta_id,
                            "pregunta": pagina["pregunta"],
                            "respuesta_alumno": respuesta,
                            "guia_evaluacion": pagina["guia_evaluacion"],
                            "respuesta_sugerida": pagina["respuesta_sugerida"],
                        }
                    )
                else:
                    retroalimentacion.append(
                        {
                            "pregunta_id": pregunta_id,
                            "porcentaje": 0,
                            "retroalimentacion": "Pregunta sin responder.",
                        }
                    )

        if desarrollo:
            evaluaciones = self._evaluar_desarrollo(quiz, desarrollo)
            retroalimentacion.extend(evaluaciones)

        feedback_por_id = {
            item["pregunta_id"]: item
            for item in [*alternativas, *retroalimentacion]
        }
        correctas_alternativas = sum(
            item["correcta"] for item in alternativas
        )
        desarrollo_porcentaje = [
            feedback_por_id[pagina["id"]]["porcentaje"]
            for pagina in quiz["paginas"]
            if pagina["tipo"] == "desarrollo"
        ]
        return {
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

    def _evaluar_desarrollo(
        self,
        quiz: dict[str, Any],
        respuestas: list[dict[str, str]],
    ) -> list[dict[str, Any]]:
        prompt = (
            "Evalúa las respuestas de desarrollo de un quiz educativo. Para cada "
            "respuesta asigna porcentaje de acierto de 0 a 100 según la guía y "
            "respuesta sugerida. Considera respuestas equivalentes aunque tengan "
            "otra redacción. Devuelve exclusivamente JSON válido con la forma "
            '{"evaluaciones":[{"pregunta_id":"...","porcentaje":0,'
            '"retroalimentacion":"..."}]}. Incluye cada pregunta exactamente una vez.\n\n'
            + json.dumps(
                {
                    "titulo": quiz["test_titulo"],
                    "respuestas": respuestas,
                },
                ensure_ascii=False,
            )
        )
        response = self.motor.generar_respuesta(
            historial=[
                {
                    "role": "system",
                    "content": (
                        "Eres un evaluador docente justo. Analiza solo la "
                        "información proporcionada y devuelve el JSON solicitado."
                    ),
                },
                {"role": "user", "content": prompt},
            ]
        )
        message = getattr(response, "message", None)
        content = (
            getattr(message, "content", "")
            if message is not None
            else response.get("message", {}).get("content", "")
        )
        parsed = _parse_json_object(content)
        evaluaciones = parsed.get("evaluaciones")
        expected_ids = {item["pregunta_id"] for item in respuestas}
        if not isinstance(evaluaciones, list):
            raise ValueError("El modelo no devolvió la lista de evaluaciones esperada.")
        evaluaciones_por_id = {}
        for evaluacion in evaluaciones:
            if not isinstance(evaluacion, dict):
                raise ValueError("El modelo devolvió una evaluación con formato inválido.")
            pregunta_id = evaluacion.get("pregunta_id")
            porcentaje = evaluacion.get("porcentaje")
            feedback = evaluacion.get("retroalimentacion")
            if (
                pregunta_id not in expected_ids
                or not isinstance(porcentaje, (int, float))
                or isinstance(porcentaje, bool)
                or not 0 <= porcentaje <= 100
                or not isinstance(feedback, str)
                or not feedback.strip()
                or pregunta_id in evaluaciones_por_id
            ):
                raise ValueError("El modelo devolvió una evaluación inválida.")
            evaluaciones_por_id[pregunta_id] = {
                "pregunta_id": pregunta_id,
                "porcentaje": round(porcentaje),
                "retroalimentacion": feedback.strip(),
            }
        if set(evaluaciones_por_id) != expected_ids:
            raise ValueError("El modelo no evaluó todas las respuestas de desarrollo.")
        return [evaluaciones_por_id[item["pregunta_id"]] for item in respuestas]

    def _ruta_intento(self, test_id: str) -> Path:
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,79}", test_id):
            raise ValueError("El identificador del quiz no es válido.")
        return self.directorio_intentos / f"{test_id}.json"


def quiz_desde_mensaje(texto: str) -> dict[str, Any] | None:
    """Extrae un quiz JSON válido de la respuesta completa del agente."""
    decoder = json.JSONDecoder()
    for match in re.finditer(r"\{", texto):
        try:
            candidato, _ = decoder.raw_decode(texto[match.start():])
            return validar_test(candidato)
        except (json.JSONDecodeError, ValueError):
            continue
    return None


def quiz_desde_resultado_herramienta(texto: str) -> dict[str, Any] | None:
    """Recupera el quiz que la herramienta crear_test devolvió al agente."""
    try:
        resultado = ast.literal_eval(texto)
    except (SyntaxError, ValueError):
        return None
    if not isinstance(resultado, dict) or "quiz_data" not in resultado:
        return None
    try:
        return validar_test(resultado["quiz_data"])
    except ValueError:
        return None


def _parse_json_object(texto: str) -> dict[str, Any]:
    result = quiz_desde_json_general(texto)
    if not isinstance(result, dict):
        raise ValueError("El modelo no devolvió un objeto JSON.")
    return result


def quiz_desde_json_general(texto: str) -> Any:
    decoder = json.JSONDecoder()
    for match in re.finditer(r"[\[{]", texto):
        try:
            return decoder.raw_decode(texto[match.start():])[0]
        except json.JSONDecodeError:
            continue
    raise ValueError("El modelo no devolvió JSON válido para evaluar.")
