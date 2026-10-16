"""Pruebas del flujo completo de quizzes: creación, persistencia y cierre."""

import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from core.quizzes import (
    QuizManager,
    cargar_intento,
    finalizar_quiz,
)
from data.quizzes import QuizStore
from ui.chat.logica import ChatLogic


def _quiz_de_ejemplo():
    return {
        "quiz_id": "quiz_flujo",
        "quiz_titulo": "Quiz de flujo",
        "paginas": [
            {
                "id": "p1",
                "tipo": "alternativa",
                "pregunta": "¿2 + 2?",
                "alternativas": {"A": "4", "B": "5"},
                "retroalimentacion": {"A": "Correcto.", "B": "Incorrecto."},
                "respuesta_correcta": "A",
            },
            {
                "id": "p2",
                "tipo": "desarrollo",
                "pregunta": "Explica.",
                "guia_evaluacion": "Menciona el concepto.",
                "respuesta_sugerida": "La explicación esperada.",
            },
        ],
    }


class _FakeMotor:
    def __init__(self):
        self.contents = [
            json.dumps(
                {
                    "evaluaciones": [
                        {
                            "pregunta_id": "p2",
                            "puntaje_normalizado": 0.5,
                            "feedback_especifico": "Vas por buen camino.",
                        }
                    ],
                }
            ),
            "Buen trabajo; sigue practicando.",
        ]
        self.historiales = []

    def generar_respuesta(self, historial):
        self.historiales.append(historial)
        return SimpleNamespace(message=SimpleNamespace(content=self.contents.pop(0)))


class _FakeAgentSession:
    def __init__(self):
        self.contextos = []

    def agregar_contexto(self, mensaje):
        self.contextos.append(mensaje)


class QuizFlowTests(unittest.TestCase):
    def test_listar_y_cargar_quiz_con_resultado_final_persistido(self):
        with tempfile.TemporaryDirectory() as directorio:
            directorio = Path(directorio)
            store = QuizStore(directorio)
            quiz = _quiz_de_ejemplo()
            QuizManager(store).guardar(quiz)
            # Simula un quiz ya finalizado: el archivo incluye resultado_final.
            store.guardar_resultado(
                quiz["quiz_id"],
                75.0,
                [{"pregunta_id": "p1", "correcta": True}],
            )

            en_disco = json.loads(
                (directorio / f"{quiz['quiz_id']}.json").read_text(encoding="utf-8")
            )
            self.assertIn("resultado_final", en_disco)

            manager = QuizManager(store)
            self.assertEqual(manager.cargar(quiz["quiz_id"]), quiz)
            self.assertEqual(manager.listar(), [quiz])

    def test_finalizar_quiz_evalua_desarrollo_y_persiste_resultado(self):
        with tempfile.TemporaryDirectory() as directorio:
            directorio = Path(directorio)
            store = QuizStore(directorio)
            quiz = _quiz_de_ejemplo()
            QuizManager(store).guardar(quiz)
            motor = _FakeMotor()
            sesion = _FakeAgentSession()

            resultado = finalizar_quiz(
                quiz,
                respuestas={"p1": "A", "p2": "Respuesta parcial."},
                motor=motor,
                historial_chat=[{"role": "user", "content": "Estoy repasando."}],
                origen="chat",
                store=store,
                agent_session=sesion,
            )

            self.assertEqual(resultado["porcentaje_total"], 75)
            self.assertEqual(resultado["feedback_final"], "Buen trabajo; sigue practicando.")
            self.assertEqual(
                [item["pregunta_id"] for item in resultado["retroalimentacion"]],
                ["p1", "p2"],
            )
            self.assertEqual(resultado["retroalimentacion"][0]["tipo"], "alternativa")
            self.assertTrue(resultado["retroalimentacion"][0]["correcta"])
            self.assertEqual(resultado["retroalimentacion"][1]["tipo"], "desarrollo")
            self.assertIsNone(resultado["retroalimentacion"][1]["correcta"])
            self.assertEqual(resultado["retroalimentacion"][1]["porcentaje"], 50)
            # El desarrollo viaja al modelo en segundo plano.
            payload = json.loads(
                motor.historiales[0][-1]["content"].split("\n\n", 1)[1]
            )
            self.assertEqual(payload["respuestas"][0]["respuesta_alumno"], "Respuesta parcial.")
            # El resultado queda persistido con el contrato canónico y el intento se elimina.
            en_disco = json.loads(
                (directorio / f"{quiz['quiz_id']}.json").read_text(encoding="utf-8")
            )
            resultado_final = en_disco["resultado_final"]
            self.assertEqual(resultado_final["porcentaje_total"], 75)
            self.assertTrue(resultado_final["retroalimentacion"])
            self.assertNotIn("puntaje_total", resultado_final)
            self.assertNotIn("detalle_evaluaciones", resultado_final)
            self.assertNotIn("avance", en_disco)
            self.assertIsNone(cargar_intento(quiz, store))
            # Listar sigue funcionando tras finalizar (era el fallo del chat).
            self.assertEqual(QuizManager(store).listar(), [quiz])
            self.assertEqual(len(sesion.contextos), 1)

    def test_finalizar_quiz_reenvia_error_de_persistencia(self):
        with tempfile.TemporaryDirectory() as directorio:
            store = QuizStore(directorio)
            quiz = _quiz_de_ejemplo()
            QuizManager(store).guardar(quiz)

            with patch.object(
                store,
                "guardar_resultado",
                side_effect=OSError("disco lleno"),
            ):
                with self.assertRaisesRegex(RuntimeError, "disco lleno"):
                    finalizar_quiz(
                        quiz,
                        respuestas={"p1": "A", "p2": "Respuesta parcial."},
                        motor=_FakeMotor(),
                        store=store,
                    )


class _ConversacionQuizTests(unittest.TestCase):
    def test_conversacion_finaliza_quiz_e_inyecta_contexto_en_chat(self):
        from core.conversation import Conversacion

        with tempfile.TemporaryDirectory() as directorio:
            directorio = Path(directorio)
            store = QuizStore(directorio)
            quiz = _quiz_de_ejemplo()
            QuizManager(store).guardar(quiz)
            historial = [
                {"role": "system", "content": "Prompt inicial."},
                {"role": "user", "content": "Estoy estudiando."},
            ]
            conversacion = Conversacion(
                _FakeMotor(),
                historial,
                {},
                guardar_interaccion=lambda *_args: None,
                quiz_store=store,
            )

            resultado = conversacion.finalizar_quiz(
                quiz,
                {"p1": "A", "p2": "Respuesta parcial."},
                origen="chat",
            )

            self.assertEqual(resultado["porcentaje_total"], 75)
            contexto = historial[-1]
            self.assertEqual(contexto["role"], "system")
            self.assertTrue(contexto["silent"])
            self.assertIn("[QUIZ]", contexto["content"])


class _FakeQueue:
    def __init__(self):
        self.items = []

    def put(self, item):
        self.items.append(item)


class _FakeChat:
    def __init__(self, tool_message):
        self.historial = []
        self._tool_message = tool_message

    def procesar_turno(self, _texto):
        self.historial.append(self._tool_message)
        return iter(())


class ChatTurnQuizTests(unittest.TestCase):
    def _make_host(self, quizzes_ref):
        class _Host(ChatLogic):
            def __init__(self):
                self.chat = None
                self.event_queue = _FakeQueue()
                self._quizzes = quizzes_ref

            def _listar_quices_seguro(self):
                return self._quizzes

        return _Host()

    def test_no_duplica_el_quiz_generado_en_el_turno(self):
        quiz = _quiz_de_ejemplo()
        host = self._make_host([])
        host.chat = _FakeChat(
            {
                "role": "tool",
                "name": "crear_quiz",
                "content": repr({"quiz_data": quiz}),
            }
        )

        def procesar(_texto):
            host.chat.historial.append(
                {
                    "role": "tool",
                    "name": "crear_quiz",
                    "content": repr({"quiz_data": quiz}),
                }
            )
            host._quizzes = [quiz]
            return iter(())

        host.chat.procesar_turno = procesar
        host._run_chat_turn("crea un quiz")

        generados = [
            item for item in host.event_queue.items if item[0] == "quiz_generated"
        ]
        self.assertEqual(len(generados), 1)
        self.assertEqual(generados[0][1]["quiz_id"], quiz["quiz_id"])
        self.assertIn(("complete", None), host.event_queue.items)

    def test_listar_quices_seguro_sobrevive_a_un_archivo_danado(self):
        host = ChatLogic()
        with (
            patch("ui.chat.logica.listar_quices", side_effect=ValueError("dañado")),
            patch("ui.chat.logica.logging.exception"),
        ):
            self.assertEqual(host._listar_quices_seguro(), [])


if __name__ == "__main__":
    unittest.main()
