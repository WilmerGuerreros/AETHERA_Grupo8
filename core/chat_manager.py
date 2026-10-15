"""Creación y persistencia de conversaciones independientes."""

import logging
import shutil
import threading
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from agent.llm import LLMEngine
from agent.tools.registro import Herramienta
from core.conversation import Conversacion
from core.memory import Memoria
from data.chat_sessions import ChatArchiveStore
from data.memory import MemoryStore
from data.paths import application_data_directory

log = logging.getLogger(__name__)


@dataclass
class ChatSession:
    """Dependencias y estado persistente de una conversación."""

    chat_id: str
    title: str
    directory: Path
    history: list[dict[str, Any]]
    memory: Memoria
    conversation: Conversacion


class ChatManager:
    """Mantiene conversaciones con prompt y modelo comunes, pero memoria propia."""

    def __init__(
        self,
        motor: LLMEngine,
        herramientas: dict[str, Herramienta],
        system_prompt: str,
        root: Path | str | None = None,
        initial_history: list[dict[str, Any]] | None = None,
        initial_save_interaction: Callable[[str, str, str], None] | None = None,
    ) -> None:
        self.motor = motor
        self.herramientas = herramientas
        self.system_prompt = system_prompt
        self.archive_store = ChatArchiveStore(root)
        self._lock = threading.RLock()
        self.sessions: dict[str, ChatSession] = {}
        self._initial_history = initial_history
        self._initial_save_interaction = initial_save_interaction
        self._load_sessions()
        if not self.sessions:
            self.create_session(importar_memoria_anterior=root is None)

    def create_session(self, importar_memoria_anterior: bool = False) -> ChatSession:
        """Crea un chat y su estructura de memoria aislada."""
        with self._lock:
            chat_id = uuid.uuid4().hex
            directory = self.archive_store.create_directory(chat_id, "Nuevo chat")
            memory_root = directory / "MEMORIA"
            memory = Memoria(
                MemoryStore(memory_root),
                modelo=self.motor.modelo,
            )
            if importar_memoria_anterior:
                self._import_legacy_memory(memory_root)
                memory = Memoria(
                    MemoryStore(memory_root),
                    modelo=self.motor.modelo,
                )
            if self._initial_history is not None:
                history = self._apply_system_prompt(self._initial_history)
            else:
                history = self._history_with_memory(memory)
            session = self._build_session(
                chat_id,
                "Nuevo chat",
                directory,
                history,
                memory,
                self._initial_save_interaction,
            )
            self._initial_history = None
            self._initial_save_interaction = None
            self.sessions[chat_id] = session
            self.archive_store.save_metadata(self.sessions.values())
            self.save_history(chat_id)
            log.info("Se creó el chat %s en %s", chat_id, directory)
            return session

    def rename_session(self, chat_id: str, title: str) -> None:
        """Actualiza el nombre visible de un chat."""
        with self._lock:
            session = self.sessions[chat_id]
            clean_title = " ".join(title.split()).strip()
            if not clean_title:
                return
            clean_title = clean_title[:60]
            session.directory = self.archive_store.rename_directory(
                chat_id,
                clean_title,
            )
            session.title = clean_title
            self.archive_store.save_metadata(self.sessions.values())

    def delete_session(self, chat_id: str, keep_memory: bool) -> None:
        """Elimina el chat, opcionalmente conservando su memoria archivada."""
        with self._lock:
            if chat_id not in self.sessions:
                raise KeyError(f"No existe el chat: {chat_id}")
            if keep_memory:
                self.archive_store.archive_memory(chat_id)
            self.archive_store.delete_directory(chat_id)
            del self.sessions[chat_id]
            self.archive_store.save_metadata(self.sessions.values())

    def store_attachment(self, chat_id: str, source: str | Path) -> Path:
        """Guarda un documento adjunto en la memoria de su conversación."""
        if chat_id not in self.sessions:
            raise KeyError(f"No existe el chat: {chat_id}")
        return self.archive_store.store_attachment(chat_id, source)

    def save_history(self, chat_id: str) -> None:
        """Guarda la transcripción completa del chat en su propio directorio."""
        with self._lock:
            session = self.sessions[chat_id]
            self.archive_store.save_history(chat_id, session.history)

    def _load_sessions(self) -> None:
        for metadata in self.archive_store.load_metadata():
            chat_id = metadata["id"]
            directory = self.archive_store.session_directory(
                chat_id,
                metadata["title"],
                metadata.get("folder"),
            )
            memory = Memoria(
                MemoryStore(directory / "MEMORIA"),
                modelo=self.motor.modelo,
            )
            history = self.archive_store.load_history(chat_id)
            if history is None:
                history = self._history_with_memory(memory)
            else:
                history = self._apply_system_prompt(
                    history,
                    memory.contexto_inicial()[1:],
                )
            self.sessions[chat_id] = self._build_session(
                chat_id,
                metadata["title"],
                directory,
                history,
                memory,
            )

    def _build_session(
        self,
        chat_id: str,
        title: str,
        directory: Path,
        history: list[dict[str, Any]],
        memory: Memoria,
        guardar_interaccion: Callable[[str, str, str], None] | None = None,
    ) -> ChatSession:
        conversation = Conversacion(
            self.motor,
            history,
            self.herramientas,
            guardar_interaccion or memory.guardar,
        )
        return ChatSession(
            chat_id,
            title,
            directory,
            history,
            memory,
            conversation,
        )

    def _apply_system_prompt(
        self,
        history: list[dict[str, Any]],
        memory_context: list[dict[str, str]] | None = None,
    ) -> list[dict[str, Any]]:
        messages = [message for message in history if message.get("role") != "system"]
        return [
            {"role": "system", "content": self.system_prompt},
            *(memory_context or []),
            *messages,
        ]

    def _history_with_memory(self, memory: Memoria) -> list[dict[str, Any]]:
        return self._apply_system_prompt(memory.contexto_inicial()[1:])

    @staticmethod
    def _import_legacy_memory(memory_root: Path) -> None:
        legacy_root = application_data_directory() / "memoria"
        if not legacy_root.is_dir() or legacy_root.resolve() == memory_root.resolve():
            return
        shutil.copytree(legacy_root, memory_root, dirs_exist_ok=True)


def title_from_message(message: str) -> str:
    """Genera un título breve a partir del primer mensaje visible."""
    text = message.strip()
    if text.startswith("Fecha:"):
        _, separator, text = text.partition("\n")
        if not separator:
            return "Nuevo chat"
    for line in text.splitlines():
        if line.startswith("document: "):
            continue
        if line.strip():
            return " ".join(line.split())[:60]
    return "Nuevo chat"
