"""Persistencia de los metadatos y transcripciones de cada chat."""

import json
from pathlib import Path
from typing import Any, Iterable

from data.paths import chat_archives_directory


class ChatArchiveStore:
    """Almacena chats en directorios separados bajo la raíz de datos de Aethera."""

    def __init__(self, root: Path | str | None = None) -> None:
        self.root = Path(root) if root is not None else chat_archives_directory()
        self.root.mkdir(parents=True, exist_ok=True)
        self._metadata_path = self.root / "CHATS.json"

    def create_directory(self, chat_id: str) -> Path:
        """Crea el directorio de archivo y sus cuatro carpetas de memoria."""
        directory = self.session_directory(chat_id)
        memory_root = directory / "MEMORIA"
        for name in ("HISTORIAL", "RESUMEN", "INDICE", "ARCHIVOS ADJUNTOS"):
            (memory_root / name).mkdir(parents=True, exist_ok=True)
        return directory

    def session_directory(self, chat_id: str) -> Path:
        """Devuelve la ruta para un ID de chat validado."""
        if not chat_id.isalnum():
            raise ValueError("El identificador del chat no es válido.")
        return self.root / f"chat_{chat_id}"

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
            entries.append({"id": item["id"], "title": item["title"]})
        return entries

    def save_metadata(self, sessions: Iterable[Any]) -> None:
        """Guarda de forma atómica el índice de chats disponibles."""
        entries = [
            {"id": session.chat_id, "title": session.title}
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
