import json
import tempfile
import unittest
from pathlib import Path

from agent.llm import LLMEngine
from core.chat_manager import ChatManager
from UI.desktop_app import AetheraDesktopApp


class ChatSessionTests(unittest.TestCase):
    def test_interfaz_inicial_lee_solo_las_ultimas_20_de_memoria_bruta(self):
        with tempfile.TemporaryDirectory() as directory:
            manager = ChatManager(
                LLMEngine("nemotron-3-super:cloud", {}),
                {},
                "Prompt.",
                root=Path(directory) / "chats",
            )
            session = next(iter(manager.sessions.values()))
            session.conversation.historial.extend(
                [
                    {"role": "user", "content": "Solo en la transcripción JSON"},
                    {"role": "assistant", "content": "No debe aparecer al iniciar"},
                ]
            )
            for indice in range(25):
                session.memory.store.escribir(
                    1,
                    f"Pregunta bruta {indice}",
                    f"Respuesta bruta {indice}",
                )

            store = AetheraDesktopApp._new_chat_store(session)
            entradas = store.entradas()
            visibles = [
                entrada
                for entrada in entradas
                if entrada["rol"] in {"user", "assistant"}
            ]

            self.assertEqual(len(visibles), 40)
            self.assertEqual(visibles[0]["texto"], "Pregunta bruta 5")
            self.assertEqual(visibles[-1]["texto"], "Respuesta bruta 24")
            self.assertNotIn(
                "Solo en la transcripción JSON",
                [entrada["texto"] for entrada in visibles],
            )
            self.assertEqual(
                entradas[0],
                {
                    "rol": "archive_notice",
                    "folder_name": session.directory.name,
                },
            )

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
                "MEMORIA BRUTA",
                "RESUMEN",
                "INDICE",
                "ARCHIVOS ADJUNTOS",
                "ARCHIVOS GENERADOS",
            )
            self.assertNotEqual(primero.directory, segundo.directory)
            for session in (primero, segundo):
                self.assertTrue((session.directory / "CONVERSACION.json").is_file())
                for carpeta in carpetas_memoria:
                    self.assertTrue((session.directory / carpeta).is_dir())
                self.assertFalse((session.directory / "MEMORIA").exists())
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
            first.memory.guardar("Persistencia de chat uno", "Respuesta uno")
            second.memory.guardar("Persistencia de chat dos", "Respuesta dos")
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
            generated_report = keep.directory / "ARCHIVOS GENERADOS" / "quiz.json"
            generated_report.write_text('{"resultado": 100}', encoding="utf-8")
            manager.delete_session(remove.chat_id, keep_memory=False)

            self.assertEqual(
                saved.parent,
                keep.directory / "ARCHIVOS ADJUNTOS",
            )
            self.assertEqual(saved.read_bytes(), b"contenido pdf")
            self.assertFalse(remove.directory.exists())

            manager.delete_session(keep.chat_id, keep_memory=True)
            archived_memory = (
                root
                / "CHATS ARCHIVADOS"
                / keep.directory.name
            )
            self.assertTrue((archived_memory / "ARCHIVOS ADJUNTOS" / saved.name).is_file())
            self.assertTrue(
                (archived_memory / "ARCHIVOS GENERADOS" / generated_report.name).is_file()
            )
            self.assertTrue((archived_memory / "MEMORIA BRUTA").is_dir())
            self.assertTrue((archived_memory / "RESUMEN").is_dir())
            self.assertTrue((archived_memory / "INDICE").is_dir())
            self.assertTrue((archived_memory / "ARCHIVOS GENERADOS").is_dir())
            self.assertFalse((archived_memory / "MEMORIA").exists())
            self.assertFalse(keep.directory.exists())
            self.assertFalse(manager.sessions)

    def test_quiz_result_is_saved_as_json_in_the_originating_chat(self):
        with tempfile.TemporaryDirectory() as directory:
            manager = ChatManager(
                LLMEngine("nemotron-3-super:cloud", {}),
                {},
                "Prompt.",
                root=Path(directory) / "chats",
            )
            first = next(iter(manager.sessions.values()))
            second = manager.create_session()
            quiz = {
                "quiz_id": "estadistica_01",
                "quiz_titulo": "Estadística inferencial",
                "paginas": [
                    {
                        "id": "p1",
                        "tipo": "alternativa",
                        "pregunta": "¿Cuál es la media?",
                        "alternativas": {"A": "2", "B": "3"},
                        "respuesta_correcta": "A",
                        "retroalimentacion": {"A": "Correcto.", "B": "Revisa."},
                    }
                ],
            }
            answers = {"p1": "A"}
            result = {
                "porcentaje_total": 100,
                "retroalimentacion": [
                    {
                        "pregunta_id": "p1",
                        "tipo": "alternativa",
                        "correcta": True,
                        "porcentaje": 100,
                        "retroalimentacion": "Correcto.",
                    }
                ],
                "feedback_final": "Buen trabajo.",
            }

            saved = manager.save_quiz_result(first.chat_id, quiz, answers, result)

            self.assertEqual(
                saved.parent,
                first.directory / "ARCHIVOS GENERADOS",
            )
            self.assertTrue(saved.is_file())
            self.assertNotEqual(saved, manager.save_quiz_result(
                first.chat_id, quiz, answers, result
            ))
            data = json.loads(saved.read_text(encoding="utf-8"))
            self.assertEqual(data["quiz_id"], quiz["quiz_id"])
            self.assertEqual(data["respuestas"], answers)
            self.assertEqual(data["resultado"], result)
            self.assertEqual(
                data["preguntas"][0]["pregunta"],
                quiz["paginas"][0]["pregunta"],
            )
            self.assertEqual(
                data["preguntas"][0]["retroalimentacion_resultado"],
                "Correcto.",
            )
            self.assertEqual(
                list((second.directory / "ARCHIVOS GENERADOS").glob("*.json")),
                [],
            )

    def test_chat_legacy_creates_generated_files_folder_when_restored(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "chats"
            chat_directory = root / "Legacy_legacy01"
            raw_directory = chat_directory / "MEMORIA BRUTA"
            raw_directory.mkdir(parents=True)
            (raw_directory / "HISTORIAL_0001.txt").write_text(
                "Usuario: Interacción existente\nAethera: Respuesta existente",
                encoding="utf-8",
            )
            (root / "CHATS.json").write_text(
                json.dumps(
                    [
                        {
                            "id": "legacy01",
                            "title": "Legacy",
                            "folder": chat_directory.name,
                        }
                    ]
                ),
                encoding="utf-8",
            )

            manager = ChatManager(
                LLMEngine("nemotron-3-super:cloud", {}),
                {},
                "Prompt.",
                root=root,
            )

            self.assertTrue(
                (
                    manager.sessions["legacy01"].directory
                    / "ARCHIVOS GENERADOS"
                ).is_dir()
            )

    def test_restoration_repairs_missing_chat_folders(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "chats"
            manager = ChatManager(
                LLMEngine("nemotron-3-super:cloud", {}),
                {},
                "Prompt.",
                root=root,
            )
            session = next(iter(manager.sessions.values()))
            session.memory.guardar("Hola", "Buenas")
            (session.directory / "ARCHIVOS ADJUNTOS").rmdir()
            (session.directory / "ARCHIVOS GENERADOS").rmdir()
            (session.directory / "RESUMEN").rmdir()

            restored = ChatManager(
                manager.motor,
                {},
                "Prompt.",
                root=root,
            )

            restored_session = restored.sessions[session.chat_id]
            for folder in (
                "MEMORIA BRUTA",
                "ARCHIVOS ADJUNTOS",
                "RESUMEN",
                "INDICE",
                "ARCHIVOS GENERADOS",
            ):
                self.assertTrue((restored_session.directory / folder).is_dir())
            self.assertIn("Hola", restored_session.memory.store.leer_historial(1))

    def test_vaciar_memoria_bruta_y_resumen_retira_chat_y_archiva_sus_datos(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "chats"
            manager = ChatManager(
                LLMEngine("nemotron-3-super:cloud", {}),
                {},
                "Prompt.",
                root=root,
            )
            session = next(iter(manager.sessions.values()))
            session.history.extend(
                [
                    {"role": "user", "content": "Turno no persistido en memoria"},
                    {"role": "assistant", "content": "Respuesta recuperable"},
                ]
            )
            manager.save_history(session.chat_id)

            restored = ChatManager(
                manager.motor,
                {},
                "Prompt.",
                root=root,
            )

            self.assertNotIn(session.chat_id, restored.sessions)
            archived = root / "CHATS ARCHIVADOS" / session.directory.name
            self.assertTrue((archived / "CONVERSACION.json").is_file())
            self.assertTrue((archived / "MEMORIA BRUTA").is_dir())
            metadata = json.loads((root / "CHATS.json").read_text(encoding="utf-8"))
            self.assertNotIn(session.chat_id, {item["id"] for item in metadata})

    def test_existing_nested_memory_layout_is_migrated_to_sibling_folders(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "chats"
            chat_directory = root / "Legacy_legacy02"
            old_raw = chat_directory / "MEMORIA" / "HISTORIAL"
            old_raw.mkdir(parents=True)
            raw_file = old_raw / "HISTORIAL_0001.txt"
            raw_file.write_text("Usuario: Hola\nAethera: Buenas", encoding="utf-8")
            generated = chat_directory / "MEMORIA" / "ARCHIVOS GENERADOS"
            generated.mkdir()
            report = generated / "QUIZ_test.json"
            report.write_text('{"resultado": 100}', encoding="utf-8")
            (root / "CHATS.json").write_text(
                json.dumps(
                    [
                        {
                            "id": "legacy02",
                            "title": "Legacy",
                            "folder": chat_directory.name,
                        }
                    ]
                ),
                encoding="utf-8",
            )

            ChatManager(
                LLMEngine("nemotron-3-super:cloud", {}),
                {},
                "Prompt.",
                root=root,
            )

            self.assertTrue(
                (chat_directory / "MEMORIA BRUTA" / raw_file.name).is_file()
            )
            self.assertTrue(
                (chat_directory / "ARCHIVOS GENERADOS" / report.name).is_file()
            )
            self.assertFalse((chat_directory / "MEMORIA").exists())


if __name__ == "__main__":
    unittest.main()
