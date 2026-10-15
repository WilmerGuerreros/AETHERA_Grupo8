import tempfile
import unittest
from pathlib import Path

from agent.llm import LLMEngine
from core.chat_manager import ChatManager


class ChatSessionTests(unittest.TestCase):
    def test_chats_tienen_historial_memoria_y_archivos_independientes(self):
        with tempfile.TemporaryDirectory() as directory:
            motor = LLMEngine("nemotron-3-super:cloud", {})
            manager = ChatManager(
                motor,
                {},
                "Prompt de sistema compartido.",
                root=Path(directory) / "CHATS DE AETHERA AI",
            )
            primero = next(iter(manager.sessions.values()))
            segundo = manager.create_session()

            carpetas_memoria = (
                "HISTORIAL",
                "RESUMEN",
                "INDICE",
                "ARCHIVOS ADJUNTOS",
            )
            self.assertNotEqual(primero.directory, segundo.directory)
            for session in (primero, segundo):
                self.assertTrue((session.directory / "CONVERSACION.json").is_file())
                for carpeta in carpetas_memoria:
                    self.assertTrue((session.directory / "MEMORIA" / carpeta).is_dir())
                self.assertEqual(session.history[0]["content"], "Prompt de sistema compartido.")
                self.assertIs(session.conversation.motor, motor)

            primero.memory.guardar("dato exclusivo uno", "respuesta uno")
            segundo.memory.guardar("dato exclusivo dos", "respuesta dos")
            manager.save_history(primero.chat_id)
            manager.save_history(segundo.chat_id)

            recuperado = ChatManager(
                motor,
                {},
                "Prompt de sistema compartido.",
                root=Path(directory) / "CHATS DE AETHERA AI",
            )
            historial_uno = recuperado.sessions[primero.chat_id].history
            historial_dos = recuperado.sessions[segundo.chat_id].history

            texto_uno = "\n".join(m["content"] for m in historial_uno if "content" in m)
            texto_dos = "\n".join(m["content"] for m in historial_dos if "content" in m)
            self.assertIn("dato exclusivo uno", texto_uno)
            self.assertNotIn("dato exclusivo dos", texto_uno)
            self.assertIn("dato exclusivo dos", texto_dos)
            self.assertNotIn("dato exclusivo uno", texto_dos)
            self.assertEqual(
                {session.conversation.motor.modelo for session in recuperado.sessions.values()},
                {"nemotron-3-super:cloud"},
            )

    def test_renombrar_usa_slug_y_codigo_hexadecimal_sin_colisiones(self):
        with tempfile.TemporaryDirectory() as directory:
            manager = ChatManager(
                LLMEngine("nemotron-3-super:cloud", {}),
                {},
                "Prompt.",
                root=Path(directory) / "chats",
            )
            first = next(iter(manager.sessions.values()))
            second = manager.create_session()
            manager.rename_session(first.chat_id, "Planificación de Álgebra")
            manager.rename_session(second.chat_id, "Planificación de Álgebra")

            self.assertIn("Planificación_de_Álgebra", first.directory.name)
            self.assertTrue(first.directory.name.endswith(first.chat_id))
            self.assertTrue(second.directory.name.endswith(second.chat_id))
            self.assertNotEqual(first.directory, second.directory)
            self.assertTrue((first.directory / "CONVERSACION.json").exists())

            restored = ChatManager(
                manager.motor,
                {},
                "Prompt.",
                root=Path(directory) / "chats",
            )
            self.assertEqual(
                restored.sessions[first.chat_id].directory.name,
                first.directory.name,
            )

    def test_delete_archive_and_attachment_storage_are_scoped_to_chat(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "chats"
            manager = ChatManager(
                LLMEngine("nemotron-3-super:cloud", {}),
                {},
                "Prompt.",
                root=root,
            )
            keep = next(iter(manager.sessions.values()))
            remove = manager.create_session()
            source = Path(directory) / "guia.pdf"
            source.write_bytes(b"contenido pdf")

            saved = manager.store_attachment(keep.chat_id, source)
            manager.delete_session(remove.chat_id, keep_memory=False)

            self.assertEqual(
                saved.parent,
                keep.directory / "MEMORIA" / "ARCHIVOS ADJUNTOS",
            )
            self.assertEqual(saved.read_bytes(), b"contenido pdf")
            self.assertFalse(remove.directory.exists())

            manager.delete_session(keep.chat_id, keep_memory=True)
            archived_memory = (
                root
                / "CHATS ARCHIVADOS"
                / keep.directory.name
                / "MEMORIA"
            )
            self.assertTrue((archived_memory / "ARCHIVOS ADJUNTOS" / saved.name).is_file())
            self.assertFalse(keep.directory.exists())
            self.assertFalse(manager.sessions)


if __name__ == "__main__":
    unittest.main()
