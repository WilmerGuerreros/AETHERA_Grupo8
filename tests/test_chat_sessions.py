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


if __name__ == "__main__":
    unittest.main()
