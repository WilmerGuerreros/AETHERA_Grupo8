"""Estado de presentación del chat que sobrevive a los cambios de sección.

La vista inicial se construye desde ``MEMORIA BRUTA`` y se mantiene separada de
la transcripción completa del agente. Los turnos nuevos, errores y quizzes se
guardan en este modelo para reconstruir la interfaz al navegar entre secciones.

Capas: este módulo pertenece a la UI (estado de presentación), interpreta
mensajes ya procesados usando ``core.quizzes`` y no importa ``tkinter`` ni
``data``. No corrige quizzes ni escribe en disco.
"""

import threading
from collections import deque
from typing import Any

from core.quizzes import (
    quiz_desde_mensaje,
    quiz_desde_resultado_herramienta,
)

ESTADO_LIBRE = "Disponible"
ESTADO_PENSANDO = "GuIA está pensando"
SALUDO = "¡Hola! Soy GuIA. ¿Qué te gustaría organizar o conversar hoy."


def _tiene_texto(contenido: Any) -> bool:
    """True si el contenido aporta texto visible (no solo espacios/saltos)."""
    return contenido is not None and bool(str(contenido).strip())


class ChatStore:
    """Transcripción visible del chat, independiente de los widgets."""

    def __init__(
        self,
        historial: list[dict[str, Any]] | None = None,
        older_history_folder: str | None = None,
    ):
        self._historial: list[dict[str, Any]] = historial if historial is not None else []
        self._lock = threading.RLock()
        self._stream_texto = ""
        self._stream_activo = False
        # Cada entrada extra recuerda cuántos mensajes tenía el historial al
        # crearse, de modo que se vuelca en su posición real y no al final.
        self._extras: list[dict[str, Any]] = []
        self._marca_turno = 0
        self._ocupado = False
        self._estado = ESTADO_LIBRE
        self._older_history_folder = older_history_folder

    @classmethod
    def desde_memoria_bruta(
        cls,
        interacciones: list[dict[str, str]],
        nombre_carpeta: str,
        limit: int = 20,
    ) -> "ChatStore":
        """Crea la vista inicial exclusivamente desde interacciones de memoria bruta."""
        if limit < 1:
            raise ValueError("El límite de interacciones visibles debe ser positivo.")
        historial = []
        for interaccion in interacciones[-limit:]:
            historial.extend(
                [
                    {"role": "user", "content": interaccion["usuario"]},
                    {"role": "assistant", "content": interaccion["aethera"]},
                ]
            )
        carpeta_historial_anterior = (
            nombre_carpeta if len(interacciones) > limit else None
        )
        return cls(historial, older_history_folder=carpeta_historial_anterior)

    def agregar_mensaje(self, role: str, content: str) -> None:
        """Añade al historial visible un mensaje producido durante esta sesión."""
        if role not in {"user", "assistant"}:
            raise ValueError("El rol del mensaje visible no es válido.")
        with self._lock:
            self._historial.append({"role": role, "content": content})

    @property
    def ocupado(self) -> bool:
        return self._ocupado

    @property
    def estado(self) -> str:
        return self._estado

    @property
    def stream_texto(self) -> str:
        return self._stream_texto

    @property
    def stream_activo(self) -> bool:
        return self._stream_activo

    def iniciar_turno(self, estado: str = ESTADO_PENSANDO) -> None:
        """Abre una respuesta en curso y marca al asistente como ocupado."""
        with self._lock:
            self._ocupado = True
            self._estado = estado
            self._stream_texto = ""
            self._stream_activo = True
            self._marca_turno = len(self._extras)

    def agregar_token(self, token: str) -> None:
        """Acumula un fragmento de la respuesta sin depender de la página."""
        with self._lock:
            if self._stream_activo:
                self._stream_texto += token

    def finalizar_turno(self) -> None:
        """Cierra la respuesta: su texto ya quedó guardado en el historial."""
        with self._lock:
            self._cerrar_stream()
            self._ocupado = False
            self._estado = ESTADO_LIBRE

    def marcar_error(self, mensaje: str) -> None:
        """Registra un fallo del turno como entrada visible en la conversación."""
        with self._lock:
            self._cerrar_stream()
            self._ocupado = False
            self._estado = ESTADO_LIBRE
            if mensaje:
                self._extras.append(
                    {"rol": "error", "texto": mensaje, "indice": len(self._historial)}
                )

    def agregar_quiz(self, quiz: dict[str, Any]) -> None:
        """Anota un quiz generado durante el turno sin duplicarlo después."""
        with self._lock:
            self._extras.append(
                {"rol": "quiz", "quiz": quiz, "indice": len(self._historial)}
            )

    def quices_del_turno(self) -> list[dict[str, Any]]:
        """Quizzes generados en el turno en curso, para incrustarlos en vivo."""
        with self._lock:
            return [
                extra["quiz"]
                for extra in self._extras[self._marca_turno :]
                if extra["rol"] == "quiz"
            ]

    def actualizar_estado(self, estado: str) -> None:
        """Actualiza el texto del indicador solo mientras el turno sigue vivo."""
        with self._lock:
            if self._ocupado:
                self._estado = estado

    def liberar(self) -> None:
        """Deja al asistente disponible sin tocar la transcripción."""
        with self._lock:
            self._ocupado = False
            self._estado = ESTADO_LIBRE

    def entradas(self) -> list[dict[str, Any]]:
        """Devuelve, en orden, las entradas que la vista debe dibujar."""
        with self._lock:
            mensajes = list(self._historial)
            pendientes = deque(self._extras)
            stream_activo = self._stream_activo
            stream_texto = self._stream_texto

        embebidos = self._ids_quiz_embebidos(mensajes)
        emitidos: set[str] = set()
        salidas: list[dict[str, Any]] = (
            [{"rol": "archive_notice", "folder_name": self._older_history_folder}]
            if self._older_history_folder is not None
            else []
        )
        mensajes_visibles = enumerate(
            mensajes,
            start=1,
        )
        consumidos = 0

        def volcar_hasta(indice: int) -> None:
            while pendientes and pendientes[0]["indice"] <= indice:
                extra = pendientes.popleft()
                if extra["rol"] == "quiz":
                    quiz_id = extra["quiz"]["quiz_id"]
                    if quiz_id in embebidos or quiz_id in emitidos:
                        continue
                    emitidos.add(quiz_id)
                salidas.append(extra)

        for posicion, mensaje in mensajes_visibles:
            salidas.extend(self._entradas_de_mensaje(mensaje, embebidos, emitidos))
            consumidos = posicion
            volcar_hasta(consumidos)
        volcar_hasta(consumidos)

        # Entradas creadas con un historial más largo de lo proyectado (poco
        # común, p. ej. al recargar) no se pierden: van al final.
        while pendientes:
            salidas.append(pendientes.popleft())
        if stream_activo:
            salidas.append({"rol": "stream", "texto": stream_texto})
        if not salidas:
            salidas.append({"rol": "saludo", "texto": SALUDO})
        return salidas

    def _cerrar_stream(self) -> None:
        self._stream_texto = ""
        self._stream_activo = False

    @staticmethod
    def _ids_quiz_embebidos(mensajes: list[dict[str, Any]]) -> set[str]:
        """Ids de los quizzes que se dibujan dentro de una respuesta."""
        embebidos: set[str] = set()
        for mensaje in mensajes:
            if mensaje.get("role") != "assistant":
                continue
            contenido = mensaje.get("content")
            if not _tiene_texto(contenido):
                continue
            quiz = quiz_desde_mensaje(contenido)
            if quiz is not None:
                embebidos.add(quiz["quiz_id"])
        return embebidos

    @staticmethod
    def _entradas_de_mensaje(
        mensaje: dict[str, Any],
        embebidos: set[str],
        emitidos: set[str],
    ) -> list[dict[str, Any]]:
        rol = mensaje.get("role")
        contenido = mensaje.get("content")
        if rol in {"assistant", "user"} and _tiene_texto(contenido):
            return [{"rol": rol, "texto": contenido}]
        if rol == "tool" and mensaje.get("name") == "crear_quiz":
            quiz = quiz_desde_resultado_herramienta(contenido or "")
            if quiz is None:
                return []
            quiz_id = quiz["quiz_id"]
            if quiz_id in embebidos or quiz_id in emitidos:
                return []
            emitidos.add(quiz_id)
            return [{"rol": "quiz", "quiz": quiz}]
        return []
