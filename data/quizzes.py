"""Lectura y escritura de quizzes JSON."""

import json
import logging
import os
import tempfile
from pathlib import Path
from typing import Any

from data.paths import quizzes_directory


# Metadatos internos que la aplicación agrega al archivo del quiz. No forman
# parte del esquema validable, así que se ocultan al leerlos antes de aplicar
# la validación de ``data.quizzes_domain.schema.validar_quiz``.
_METADATOS_INTERNOS = ("avance", "resultado_final")


class QuizStore:
    """Repositorio de quizzes que encapsula rutas, lectura y escritura.

    El directorio solo se indica para inyectar una ubicación alternativa en
    pruebas; en producción se resuelve con ``quizzes_directory()``.
    """

    def __init__(self, directorio: Path | str | None = None) -> None:
        self.directorio = (
            Path(directorio) if directorio is not None else quizzes_directory()
        )

    # --- quizzes ---

    def guardar(self, quiz: dict[str, Any]) -> Path:
        """Guarda un quiz sin sobrescribir un archivo existente."""
        ruta_destino = self._ruta(quiz["quiz_id"])
        temporal = None
        try:
            self.directorio.mkdir(parents=True, exist_ok=True)
            contenido = json.dumps(quiz, ensure_ascii=False, indent=2) + "\n"
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                newline="",
                dir=self.directorio,
                prefix=f".{quiz['quiz_id']}.",
                suffix=".tmp",
                delete=False,
            ) as archivo:
                temporal = archivo.name
                archivo.write(contenido)
                archivo.flush()
                os.fsync(archivo.fileno())
            os.link(temporal, ruta_destino)
        finally:
            if temporal and os.path.exists(temporal):
                try:
                    os.unlink(temporal)
                except OSError:
                    logging.exception("No se pudo limpiar el archivo temporal del quiz.")
        return ruta_destino

    def listar(self) -> list[Any]:
        """Devuelve los quizzes guardados, con sus metadatos internos ocultos."""
        if not self.directorio.exists():
            return []
        return [self._leer(ruta) for ruta in sorted(self.directorio.glob("*.json"))]

    def cargar(self, quiz_id: str) -> Any:
        """Lee un quiz por identificador, ocultando los metadatos internos."""
        return self._leer(self._ruta(quiz_id))

    # --- avance ---

    def leer_avance(self, quiz_id: str) -> Any | None:
        """Lee el avance guardado dentro del JSON del quiz."""
        try:
            quiz = self._leer_crudo(self._ruta(quiz_id))
        except FileNotFoundError:
            return None
        if not isinstance(quiz, dict):
            raise ValueError(f"El archivo del quiz '{quiz_id}' no es válido.")
        avance = quiz.get("avance")
        if avance is None:
            return None
        return _decodificar_avance(avance, quiz_id)

    def guardar_avance(self, quiz_id: str, intento: dict[str, Any]) -> Path:
        """Persiste el avance en el mismo JSON donde está guardado el quiz."""
        ruta = self._ruta(quiz_id)
        quiz = self._leer_crudo(ruta)
        if not isinstance(quiz, dict) or quiz.get("quiz_id") != quiz_id:
            raise ValueError(f"El archivo del quiz '{quiz_id}' no es válido.")
        quiz["avance"] = _codificar_avance(quiz, intento)
        return _reemplazar_json(ruta, quiz)

    def eliminar_avance(self, quiz_id: str) -> None:
        """Elimina el avance del JSON del quiz, si existe."""
        ruta = self._ruta(quiz_id)
        try:
            quiz = self._leer_crudo(ruta)
        except FileNotFoundError:
            return
        if not isinstance(quiz, dict):
            raise ValueError(f"El archivo del quiz '{quiz_id}' no es válido.")
        if quiz.pop("avance", None) is not None:
            _reemplazar_json(ruta, quiz)

    # --- resultado final ---

    def guardar_resultado(
        self,
        quiz_id: str,
        porcentaje_total: float | int,
        retroalimentacion: list[dict[str, Any]] | dict[str, Any],
    ) -> Path:
        """Guarda el resultado final de un quiz en el JSON del usuario."""
        ruta = self._ruta(quiz_id)
        try:
            quiz = self._leer_crudo(ruta)
        except FileNotFoundError:
            raise FileNotFoundError(f"No existe el quiz '{quiz_id}'.")
        if not isinstance(quiz, dict) or quiz.get("quiz_id") != quiz_id:
            raise ValueError(f"El archivo del quiz '{quiz_id}' no es válido.")

        quiz["resultado_final"] = {
            "porcentaje_total": porcentaje_total,
            "retroalimentacion": retroalimentacion,
        }
        return _reemplazar_json(ruta, quiz)

    # --- helpers internos ---

    def _ruta(self, quiz_id: str) -> Path:
        return self.directorio / f"{quiz_id}.json"

    def _leer(self, ruta: Path) -> Any:
        datos = self._leer_crudo(ruta)
        if isinstance(datos, dict):
            for clave in _METADATOS_INTERNOS:
                datos.pop(clave, None)
        return datos

    @staticmethod
    def _leer_crudo(ruta: Path) -> Any:
        with ruta.open("r", encoding="utf-8") as archivo:
            return json.load(archivo)


def _codificar_avance(
    quiz: dict[str, Any],
    intento: dict[str, Any],
) -> dict[str, Any]:
    respuestas = intento.get("respuestas", {})
    paginas = quiz.get("paginas", [])
    orden_preguntas = {
        pagina.get("id", f"p{indice}"): indice
        for indice, pagina in enumerate(paginas)
        if isinstance(pagina, dict)
    }
    respuestas_en_orden = sorted(
        respuestas.items(),
        key=lambda item: orden_preguntas.get(item[0], len(orden_preguntas)),
    )
    return {
        "indice": intento.get("indice", 0),
        "respuestas": [
            {"pregunta_id": pregunta_id, "respuesta": respuesta}
            for pregunta_id, respuesta in respuestas_en_orden
        ],
    }


def _decodificar_avance(avance: Any, quiz_id: str) -> dict[str, Any]:
    if not isinstance(avance, dict):
        raise ValueError("El avance guardado no tiene un formato válido.")
    respuestas = avance.get("respuestas")
    if not isinstance(respuestas, list):
        raise ValueError("La lista de respuestas del avance no es válida.")
    respuestas_por_id = {}
    for item in respuestas:
        if (
            not isinstance(item, dict)
            or not isinstance(item.get("pregunta_id"), str)
            or not isinstance(item.get("respuesta"), str)
            or item["pregunta_id"] in respuestas_por_id
        ):
            raise ValueError("Una respuesta del avance no tiene un formato válido.")
        respuestas_por_id[item["pregunta_id"]] = item["respuesta"]
    return {
        "quiz_id": quiz_id,
        "indice": avance.get("indice", 0),
        "respuestas": respuestas_por_id,
    }


def _reemplazar_json(ruta: Path, datos: dict[str, Any]) -> Path:
    temporal = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="",
            dir=ruta.parent,
            prefix=f".{ruta.stem}.",
            suffix=".tmp",
            delete=False,
        ) as archivo:
            temporal = archivo.name
            json.dump(datos, archivo, ensure_ascii=False, indent=2)
            archivo.write("\n")
            archivo.flush()
            os.fsync(archivo.fileno())
        os.replace(temporal, ruta)
    except Exception:
        if temporal and os.path.exists(temporal):
            try:
                os.unlink(temporal)
            except OSError:
                logging.exception("No se pudo limpiar el archivo temporal del quiz.")
        raise
    return ruta
