"""Persistencia de los metadatos y transcripciones de cada chat."""

import json
import re
import shutil
from pathlib import Path
from typing import Any, Iterable
from uuid import uuid4

from data.paths import chat_archives_directory


class ChatArchiveStore:
    """Almacena chats en directorios separados bajo la raíz de datos de Aethera."""

    def __init__(self, root: Path | str | None = None) -> None:
        self.root = Path(root) if root is not None else chat_archives_directory()
        self.root.mkdir(parents=True, exist_ok=True)
        self._metadata_path = self.root / "CHATS.json"
        self._directories: dict[str, Path] = {}

    def create_directory(self, chat_id: str, title: str = "Nuevo chat") -> Path:
        """Crea el directorio de archivo y sus cuatro carpetas de memoria."""
        directory = self.session_directory(chat_id, title)
        memory_root = directory / "MEMORIA"
        for name in ("HISTORIAL", "RESUMEN", "INDICE", "ARCHIVOS ADJUNTOS"):
            (memory_root / name).mkdir(parents=True, exist_ok=True)
        return directory

    def session_directory(
        self,
        chat_id: str,
        title: str | None = None,
        folder: str | None = None,
    ) -> Path:
        """Devuelve o migra el directorio legible y único de un chat."""
        if not chat_id.isalnum():
            raise ValueError("El identificador del chat no es válido.")
        if chat_id in self._directories and folder is None and title is None:
            return self._directories[chat_id]
        directory_name = folder or self._directory_name(title or "chat", chat_id)
        if Path(directory_name).name != directory_name or directory_name in {".", ".."}:
            raise ValueError("El nombre de carpeta del chat no es válido.")
        directory = self.root / directory_name
        legacy_directory = self.root / f"chat_{chat_id}"
        if not directory.exists() and legacy_directory.is_dir():
            legacy_directory.replace(directory)
        self._directories[chat_id] = directory
        return directory

    def rename_directory(self, chat_id: str, title: str) -> Path:
        """Renombra la carpeta conservando el código hexadecimal del chat."""
        current = self.session_directory(chat_id)
        destination = self.root / self._directory_name(title, chat_id)
        if current != destination:
            if destination.exists():
                raise FileExistsError(f"Ya existe la carpeta del chat: {destination}")
            current.replace(destination)
        self._directories[chat_id] = destination
        return destination

    def archive_memory(self, chat_id: str) -> Path | None:
        """Mueve solo la memoria del chat a ``CHATS ARCHIVADOS``."""
        directory = self.session_directory(chat_id)
        memory = directory / "MEMORIA"
        if not memory.exists():
            return None
        archive_root = self.root / "CHATS ARCHIVADOS"
        archive_root.mkdir(parents=True, exist_ok=True)
        archive_directory = archive_root / directory.name
        archive_directory.mkdir(parents=True, exist_ok=False)
        destination = archive_directory / "MEMORIA"
        memory.replace(destination)
        return destination

    def delete_directory(self, chat_id: str) -> None:
        """Elimina la carpeta activa y sus archivos adjuntos/transcripción."""
        directory = self.session_directory(chat_id)
        if directory.exists():
            shutil.rmtree(directory)
        self._directories.pop(chat_id, None)

    def store_attachment(self, chat_id: str, source: str | Path) -> Path:
        """Copia un adjunto a la memoria del chat con nombre único."""
        source_path = Path(source)
        if not source_path.is_file():
            raise FileNotFoundError(f"No se encontró el archivo adjunto: {source_path}")
        memory = self.session_directory(chat_id) / "MEMORIA" / "ARCHIVOS ADJUNTOS"
        memory.mkdir(parents=True, exist_ok=True)
        safe_name = re.sub(r"[^\w.-]+", "_", source_path.name).strip("._")
        if not safe_name:
            safe_name = "adjunto"
        destination = memory / f"{uuid4().hex}_{safe_name}"
        shutil.copy2(source_path, destination)
        return destination

    def load_metadata(self) -> list[dict[str, str]]:
        """Carga la lista de chats o devuelve una lista vacía si es nueva."""
        if not self._metadata_path.exists():
            return []
        data = json.loads(self._metadata_path.read_text(encoding="utf-8"))
        if not isinstance(data, list):
            raise ValueError(f"El índice de chats no tiene un formato válido: {self._metadata_path}")
        entries = []
        for item in data:
            if (
                not isinstance(item, dict)
                or not isinstance(item.get("id"), str)
                or not isinstance(item.get("title"), str)
            ):
                raise ValueError(f"El índice de chats contiene una entrada inválida: {self._metadata_path}")
            entry = {"id": item["id"], "title": item["title"]}
            if isinstance(item.get("folder"), str):
                entry["folder"] = item["folder"]
            entries.append(entry)
        return entries

    def save_metadata(self, sessions: Iterable[Any]) -> None:
        """Guarda de forma atómica el índice de chats disponibles."""
        entries = [
            {
                "id": session.chat_id,
                "title": session.title,
                "folder": session.directory.name,
            }
            for session in sessions
        ]
        self._write_json(self._metadata_path, entries)

    def load_history(self, chat_id: str) -> list[dict[str, Any]] | None:
        """Carga la transcripción de un chat, si ya existe."""
        path = self.session_directory(chat_id) / "CONVERSACION.json"
        if not path.exists():
            return None
        history = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(history, list) or any(
            not isinstance(message, dict) for message in history
        ):
            raise ValueError(f"La transcripción del chat no es válida: {path}")
        return history

    @staticmethod
    def _directory_name(title: str, chat_id: str) -> str:
        slug = re.sub(r"[^\w-]+", "_", title, flags=re.UNICODE).strip("_-")
        slug = slug[:60] or "chat"
        return f"{slug}_{chat_id}"

    def save_history(self, chat_id: str, history: list[dict[str, Any]]) -> None:
        """Guarda la transcripción JSON en la carpeta de su chat."""
        self._write_json(
            self.session_directory(chat_id) / "CONVERSACION.json",
            history,
        )

    @staticmethod
    def _write_json(path: Path, data: Any) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path = path.with_suffix(path.suffix + ".tmp")
        temporary_path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        temporary_path.replace(path)
