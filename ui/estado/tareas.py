"""Ejecución de tareas de fondo fuera de la vista.

Las tareas se registran en el ``TaskManager`` y no en los widgets, de modo que
siguen vivas al cambiar de sección. Las notificaciones se entregan mediante
``emit`` (por convención, la cola de eventos de la aplicación) para que el hilo
principal sea el único que toque Tk.
"""

import itertools
import threading
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

PENDIENTE = "pendiente"
CORRIENDO = "corriendo"
LISTO = "listo"
ERROR = "error"


@dataclass
class Tarea:
    """Estado de una tarea de fondo, independiente de cualquier widget."""

    id: str
    tipo: str
    estado: str = PENDIENTE
    progreso: float | None = None
    mensaje: str = ""
    resultado: Any = None
    error: str = ""
    contexto: dict[str, Any] = field(default_factory=dict)

    @property
    def activa(self) -> bool:
        return self.estado in (PENDIENTE, CORRIENDO)

    def como_dict(self) -> dict[str, Any]:
        """Copia serializable para cruzar de un hilo al hilo principal."""
        return {
            "id": self.id,
            "tipo": self.tipo,
            "estado": self.estado,
            "progreso": self.progreso,
            "mensaje": self.mensaje,
            "resultado": self.resultado,
            "error": self.error,
            "contexto": dict(self.contexto),
        }


class TaskManager:
    """Registra y ejecuta tareas en hilos daemon.

    ``emit(evento, valor)`` entrega las notificaciones; el emisor nunca toca Tk
    directamente, la UI decide cuándo reflejar los cambios. ``cuerpo(tarea)``
    puede llamar a ``actualizar`` para reportar progreso o mensajes.
    """

    def __init__(self, emit: Callable[[str, Any], None] | None = None):
        self._emit = emit or (lambda _evento, _valor=None: None)
        self._lock = threading.Lock()
        self._tareas: dict[str, Tarea] = {}
        self._contador = itertools.count(1)

    def lanzar(self, tipo: str, cuerpo: Callable[[Tarea], Any], contexto=None) -> Tarea:
        """Crea una tarea y ejecuta ``cuerpo(tarea)`` en un hilo daemon."""
        tarea = Tarea(
            id=f"{tipo}-{next(self._contador)}",
            tipo=tipo,
            contexto=dict(contexto or {}),
        )
        with self._lock:
            self._tareas[tarea.id] = tarea
        self.actualizar(tarea.id, estado=CORRIENDO)

        def runner():
            try:
                resultado = cuerpo(tarea)
            except Exception as error:  # se reporta a la UI, nunca se pierde
                self.fallar(tarea.id, error)
            else:
                self.completar(tarea.id, resultado)

        threading.Thread(target=runner, daemon=True).start()
        return tarea

    def actualizar(self, tarea_id: str, **campos: Any) -> Tarea | None:
        with self._lock:
            tarea = self._tareas.get(tarea_id)
            if tarea is None:
                return None
            for clave, valor in campos.items():
                setattr(tarea, clave, valor)
            snapshot = tarea.como_dict()
        self._emit("tarea_actualizada", snapshot)
        return tarea

    def completar(self, tarea_id: str, resultado: Any = None) -> Tarea | None:
        return self.actualizar(tarea_id, estado=LISTO, resultado=resultado)

    def fallar(self, tarea_id: str, error: Exception | str) -> Tarea | None:
        return self.actualizar(tarea_id, estado=ERROR, error=str(error))

    def tarea(self, tarea_id: str) -> Tarea | None:
        with self._lock:
            return self._tareas.get(tarea_id)

    def activas(self) -> list[Tarea]:
        with self._lock:
            return [tarea for tarea in self._tareas.values() if tarea.activa]

    def olvidar(self, tarea_id: str) -> None:
        with self._lock:
            self._tareas.pop(tarea_id, None)
