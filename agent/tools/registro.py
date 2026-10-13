"""Metadatos de las herramientas que puede usar el agente.

Cada herramienta se declara una sola vez. La descripción que ve el modelo se
toma del propio docstring de la función, mientras que ``categoria`` y
``palabras_clave`` quedarán disponibles para el enrutamiento por embeddings sin
duplicar información.
"""

from dataclasses import dataclass
from typing import Callable


def _descripcion_de(funcion: Callable) -> str:
    """Resume en una línea el docstring de la herramienta."""
    doc = (funcion.__doc__ or "").strip()
    if not doc:
        return ""
    return doc.splitlines()[0].strip()


@dataclass(frozen=True)
class Herramienta:
    """Información declarativa de una herramienta del agente."""

    nombre: str
    funcion: Callable
    categoria: str
    palabras_clave: tuple[str, ...] = ()

    @property
    def descripcion(self) -> str:
        """Resumen legible tomado del docstring de la función."""
        return _descripcion_de(self.funcion)
