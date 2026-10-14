"""Lectura y escritura de quizzes JSON."""

import json
import logging
import os
import tempfile
from pathlib import Path
from typing import Any


# Metadatos internos que la aplicación agrega al archivo del quiz. No forman
# parte del esquema validable, así que se ocultan al leerlos para no romper la
# validación de ``core.quizzes.validar_quiz``.
_METADATOS_INTERNOS = ("avance", "resultado_final")


def guardar_quiz_json(
    directorio: Path, quiz: dict[str, Any]
) -> Path:
    """Guarda un quiz sin sobrescribir un archivo existente."""
    ruta_destino = directorio / f"{quiz['quiz_id']}.json"
    temporal = None
    try:
        directorio.mkdir(parents=True, exist_ok=True)
        contenido = json.dumps(quiz, ensure_ascii=False, indent=2) + "\n"
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="",
            dir=directorio,
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


def listar_archivos_quiz(directorio: Path) -> list[Path]:
    """Devuelve ordenadas las rutas de quizzes JSON almacenados."""
    if not directorio.exists():
        return []
    return sorted(directorio.glob("*.json"))


def leer_quiz_json(ruta: Path) -> Any:
    """Lee un quiz y oculta los metadatos de avance y resultado locales."""
    with ruta.open("r", encoding="utf-8") as archivo:
        quiz = json.load(archivo)
    if isinstance(quiz, dict):
        for clave in _METADATOS_INTERNOS:
            quiz.pop(clave, None)
    return quiz


def leer_intento_quiz(carpeta: Path, quiz_id: str) -> Any | None:
    """Lee el avance guardado dentro del JSON del quiz."""
    carpeta = Path(carpeta)
    ruta = carpeta / f"{quiz_id}.json"
    try:
        with ruta.open("r", encoding="utf-8") as archivo:
            quiz = json.load(archivo)
    except FileNotFoundError:
        return _leer_intento_heredado(carpeta, quiz_id)
    if not isinstance(quiz, dict):
        raise ValueError(f"El archivo del quiz '{quiz_id}' no es válido.")
    avance = quiz.get("avance")
    if avance is not None:
        return _decodificar_avance(avance, quiz_id)
    return _leer_intento_heredado(carpeta, quiz_id)


def guardar_intento_quiz(
    carpeta: Path,
    quiz_id: str,
    intento: dict[str, Any],
) -> Path:
    """Persiste el avance en el mismo JSON donde está guardado el quiz."""
    carpeta = Path(carpeta)
    ruta = carpeta / f"{quiz_id}.json"
    with ruta.open("r", encoding="utf-8") as archivo:
        quiz = json.load(archivo)
    if not isinstance(quiz, dict) or quiz.get("quiz_id") != quiz_id:
        raise ValueError(f"El archivo del quiz '{quiz_id}' no es válido.")
    quiz["avance"] = _codificar_avance(quiz, intento)
    _reemplazar_json(ruta, quiz)
    _eliminar_intento_heredado(carpeta, quiz_id)
    return ruta


def eliminar_intento_quiz(carpeta: Path, quiz_id: str) -> None:
    """Elimina el avance del JSON del quiz, si existe."""
    carpeta = Path(carpeta)
    ruta = carpeta / f"{quiz_id}.json"
    try:
        with ruta.open("r", encoding="utf-8") as archivo:
            quiz = json.load(archivo)
    except FileNotFoundError:
        _eliminar_intento_heredado(carpeta, quiz_id)
        return
    if not isinstance(quiz, dict):
        raise ValueError(f"El archivo del quiz '{quiz_id}' no es válido.")
    if quiz.pop("avance", None) is not None:
        _reemplazar_json(ruta, quiz)
    _eliminar_intento_heredado(carpeta, quiz_id)


def _leer_intento_heredado(carpeta: Path, quiz_id: str) -> Any | None:
    """Lee intentos del formato anterior para conservar progreso existente."""
    ruta = carpeta / ".intentos" / f"{quiz_id}.json"
    try:
        with ruta.open("r", encoding="utf-8") as archivo:
            return json.load(archivo)
    except FileNotFoundError:
        return None


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


def _eliminar_intento_heredado(carpeta: Path, quiz_id: str) -> None:
    ruta = carpeta / ".intentos" / f"{quiz_id}.json"
    try:
        ruta.unlink()
    except FileNotFoundError:
        pass


def guardar_resultado_quiz(
    quiz_id: str,
    puntaje_total: float | int,
    detalle_evaluaciones: list[dict[str, Any]] | dict[str, Any],
    carpeta: Path | None = None,
) -> Path:
    """Guarda el resultado final de un quiz en el JSON del usuario."""
    from data.paths import quizzes_directory

    carpeta = Path(carpeta) if carpeta else quizzes_directory()
    ruta = carpeta / f"{quiz_id}.json"
    try:
        with ruta.open("r", encoding="utf-8") as archivo:
            quiz = json.load(archivo)
    except FileNotFoundError:
        raise FileNotFoundError(f"No existe el quiz '{quiz_id}'.")
    if not isinstance(quiz, dict) or quiz.get("quiz_id") != quiz_id:
        raise ValueError(f"El archivo del quiz '{quiz_id}' no es válido.")

    resultado = {
        "puntaje_total": puntaje_total,
        "detalle_evaluaciones": detalle_evaluaciones,
    }
    quiz["resultado_final"] = resultado

    return _reemplazar_json(ruta, quiz)


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
