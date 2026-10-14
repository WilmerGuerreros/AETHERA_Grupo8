"""Lectura de recursos de referencia empaquetados con Aethera."""

import csv
import json
from pathlib import Path
from typing import Any

from data.paths import resource_path


def leer_recurso_csv(nombre: str) -> list[dict[str, str]]:
    """Lee las filas de un CSV de referencia por nombre de recurso."""
    return leer_csv(resource_path(nombre))


def leer_recurso_json(nombre: str) -> Any:
    """Lee y decodifica un JSON de referencia por nombre de recurso."""
    return leer_json(resource_path(nombre))


def leer_recurso_texto(nombre: str) -> str:
    """Lee un texto de referencia por nombre de recurso."""
    return leer_texto(resource_path(nombre))


def leer_csv(ruta: Path) -> list[dict[str, str]]:
    """Lee filas de un CSV codificado en UTF-8."""
    with ruta.open(mode="r", encoding="utf-8", newline="") as archivo:
        return list(csv.DictReader(archivo))


def leer_json(ruta: Path) -> Any:
    """Lee y decodifica un archivo JSON."""
    with ruta.open(encoding="utf-8") as archivo:
        return json.load(archivo)


def leer_texto(ruta: Path) -> str:
    """Lee un archivo de texto codificado en UTF-8."""
    return ruta.read_text(encoding="utf-8")
