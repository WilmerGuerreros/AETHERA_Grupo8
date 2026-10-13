"""Lectura y escritura de quizzes JSON."""

import json
import logging
import os
import tempfile
from pathlib import Path
from typing import Any


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
    """Lee y decodifica un quiz JSON."""
    with ruta.open("r", encoding="utf-8") as archivo:
        return json.load(archivo)


def leer_intento_quiz(carpeta: Path, quiz_id: str) -> Any | None:
    """Lee el intento persistido para un quiz, si existe."""
    ruta = Path(carpeta) / f"{quiz_id}.json"
    try:
        with ruta.open("r", encoding="utf-8") as archivo:
            return json.load(archivo)
    except FileNotFoundError:
        return None


def guardar_intento_quiz(
    carpeta: Path,
    quiz_id: str,
    intento: dict[str, Any],
) -> Path:
    """Persiste el progreso de un intento en JSON UTF-8."""
    carpeta = Path(carpeta)
    carpeta.mkdir(parents=True, exist_ok=True)
    ruta = carpeta / f"{quiz_id}.json"
    ruta.write_text(
        json.dumps(intento, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return ruta


def eliminar_intento_quiz(carpeta: Path, quiz_id: str) -> None:
    """Elimina un intento guardado si existe."""
    ruta = Path(carpeta) / f"{quiz_id}.json"
    try:
        ruta.unlink()
    except FileNotFoundError:
        pass
