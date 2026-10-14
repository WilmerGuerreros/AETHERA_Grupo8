import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from core.conversation import Conversacion
from core.quizzes import (
    QuizManager,
    cargar_intento,
    crear_quiz,
    eliminar_intento,
    evaluar_quiz,
    guardar_intento,
    preparar_respuestas_desarrollo,
    quiz_desde_mensaje,
    quiz_desde_resultado_herramienta,
    seleccionar_respuesta_alternativa,
    validar_quiz,
)
from data.quizzes import QuizStore


class FakeMotor:
    def __init__(self, content, feedback="Buen trabajo; sigue practicando."):
        self.contents = [content, feedback]
        self.historial = None
        self.historiales = []

    def generar_respuesta(self, historial):
        self.historial = historial
        self.historiales.append(historial)
        content = self.contents.pop(0)
        return SimpleNamespace(message=SimpleNamespace(content=content))


class CoreQuizTests(unittest.TestCase):
    def setUp(self):
        self.quiz = {
            "quiz_id": "demo_quiz",
            "quiz_titulo": "Quiz de prueba",
            "paginas": [
                {
                    "id": "p1",
                    "tipo": "alternativa",
                    "pregunta": "¿2 + 2?",
                    "alternativas": {"A": "4", "B": "5"},
                    "retroalimentacion": {
                        "A": "Correcto.",
                        "B": "Incorrecto.",
                    },
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

    def test_crea_y_valida_esquema_de_quiz(self):
        quiz = crear_quiz(
            "Quiz generado",
            [
                [
                    "alternative",
                    "¿1 + 1?",
                    ["2", "3"],
                    "2",
                    "La suma de uno y uno es dos.",
                ]
            ],
        )

        self.assertEqual(quiz["quiz_titulo"], "Quiz generado")
        self.assertEqual(quiz["quiz_id"].split("_", 1)[0], "quiz")
        pagina = validar_quiz(quiz)["paginas"][0]
        self.assertEqual(pagina["id"], "p1")
        self.assertEqual(
            pagina["retroalimentacion"]["A"],
            "La suma de uno y uno es dos.",
        )
        self.assertEqual(
            pagina["retroalimentacion"]["B"],
            "Incorrecto. La suma de uno y uno es dos.",
        )

    def test_persiste_y_carga_quiz_mediante_core(self):
        with tempfile.TemporaryDirectory() as directorio:
            manager = QuizManager(QuizStore(directorio))
            manager.guardar(self.quiz)

            self.assertEqual(manager.cargar("demo_quiz"), self.quiz)
            self.assertEqual(manager.listar(), [self.quiz])

    def test_guarda_carga_y_elimina_intento(self):
        with tempfile.TemporaryDirectory() as directorio:
            store = QuizStore(directorio)
            QuizManager(store).guardar(self.quiz)
            guardar_intento(
                self.quiz,
                1,
                {"p1": "A", "p2": "Respuesta parcial."},
                store,
            )

            quiz_en_disco = json.loads(
                (Path(directorio) / "demo_quiz.json").read_text(encoding="utf-8")
            )
            self.assertEqual(
                quiz_en_disco["avance"]["respuestas"],
                [
                    {"pregunta_id": "p1", "respuesta": "A"},
                    {"pregunta_id": "p2", "respuesta": "Respuesta parcial."},
                ],
            )
            self.assertEqual(QuizManager(store).cargar("demo_quiz"), self.quiz)
            self.assertEqual(
                cargar_intento(self.quiz, store),
                {
                    "indice": 1,
                    "respuestas": {
                        "p1": "A",
                        "p2": "Respuesta parcial.",
                    },
                    "evaluaciones": {
                        "p1": {
                            "correcta": True,
                            "retroalimentacion": "Correcto.",
                        }
                    },
                },
            )
            eliminar_intento("demo_quiz", store)
            self.assertIsNone(cargar_intento(self.quiz, store))
            quiz_en_disco = json.loads(
                (Path(directorio) / "demo_quiz.json").read_text(encoding="utf-8")
            )
            self.assertNotIn("avance", quiz_en_disco)

    def test_selecciona_y_persiste_alternativa_sin_permitir_cambiarla(self):
        with tempfile.TemporaryDirectory() as directorio:
            store = QuizStore(directorio)
            QuizManager(store).guardar(self.quiz)
            resultado = seleccionar_respuesta_alternativa(
                self.quiz,
                0,
                {"p2": "Borrador de desarrollo"},
                "p1",
                "B",
                store,
            )

            self.assertFalse(resultado["correcta"])
            self.assertEqual(resultado["retroalimentacion"], "Incorrecto.")
            self.assertEqual(
                cargar_intento(self.quiz, store)["respuestas"],
                {"p1": "B", "p2": "Borrador de desarrollo"},
            )
            quiz_en_disco = json.loads(
                (Path(directorio) / "demo_quiz.json").read_text(encoding="utf-8")
            )
            self.assertEqual(
                quiz_en_disco["avance"]["respuestas"],
                [
                    {"pregunta_id": "p1", "respuesta": "B"},
                    {
                        "pregunta_id": "p2",
                        "respuesta": "Borrador de desarrollo",
                    },
                ],
            )
            with self.assertRaisesRegex(ValueError, "no se puede cambiar"):
                seleccionar_respuesta_alternativa(
                    self.quiz,
                    0,
                    {"p1": "B"},
                    "p1",
                    "A",
                    store,
                )

    def test_rechaza_respuesta_guardada_que_no_existe(self):
        with tempfile.TemporaryDirectory() as directorio:
            store = QuizStore(directorio)
            QuizManager(store).guardar(self.quiz)
            with self.assertRaisesRegex(ValueError, "no es válida"):
                guardar_intento(self.quiz, 0, {"p1": "Z"}, store)

    def test_califica_respuesta_abierta_y_alternativa(self):
        contenido = json.dumps({
            "evaluaciones": [
                {
                    "pregunta_id": "p2",
                    "puntaje_normalizado": 0.5,
                    "feedback_especifico": "La respuesta está parcialmente completa.",
                }
            ]
        })

        motor = FakeMotor(contenido)
        historial_chat = [
            {"role": "system", "content": "Instrucciones originales."},
            {"role": "user", "content": "Estoy repasando."},
        ]
        with tempfile.TemporaryDirectory() as directorio:
            store = QuizStore(directorio)
            QuizManager(store).guardar(self.quiz)
            resultado = evaluar_quiz(
                motor,
                self.quiz,
                {"p1": "A", "p2": "Respuesta parcial."},
                historial_chat,
                store,
            )

        self.assertEqual(resultado["porcentaje_alternativas"], 100)
        self.assertEqual(resultado["porcentaje_desarrollo"], 50)
        self.assertEqual(resultado["porcentaje_total"], 75)
        self.assertEqual(
            resultado["feedback_final"],
            "Buen trabajo; sigue practicando.",
        )
        self.assertEqual(
            [mensaje["role"] for mensaje in motor.historial],
            ["system", "user", "user"],
        )
        self.assertEqual(len(motor.historiales), 2)
        self.assertEqual(
            motor.historiales[0][1]["content"],
            "Estoy repasando.",
        )
        self.assertEqual(
            motor.historiales[1][1]["content"],
            "Estoy repasando.",
        )
        evaluacion_payload = json.loads(
            motor.historiales[0][-1]["content"].split("\n\n", 1)[1]
        )
        self.assertEqual(
            evaluacion_payload["respuestas"][0]["guia_evaluacion"],
            "Menciona el concepto.",
        )
        feedback_payload = json.loads(
            motor.historiales[1][-1]["content"].split("\n\n", 1)[1]
        )
        self.assertEqual(
            feedback_payload["resultados"]["porcentaje_total"],
            75,
        )
        self.assertEqual(
            [item["pregunta_id"] for item in resultado["retroalimentacion"]],
            ["p1", "p2"],
        )
        self.assertEqual(cargar_intento(self.quiz, store), None)

    def test_envia_resultado_de_quiz_sin_desarrollo_al_modelo_con_historial(self):
        quiz = {
            "quiz_id": "solo_alternativas",
            "quiz_titulo": "Quiz de alternativas",
            "paginas": [self.quiz["paginas"][0]],
        }
        historial = [
            {"role": "system", "content": "Prompt inicial."},
            {"role": "user", "content": "Ayúdame a estudiar."},
        ]
        motor = FakeMotor("Buen dominio del tema.")
        with tempfile.TemporaryDirectory() as directorio:
            store = QuizStore(directorio)
            QuizManager(store).guardar(quiz)
            conversacion = Conversacion(
                motor,
                historial,
                {},
                guardar_interaccion=lambda *_args: None,
                quiz_store=store,
            )

            resultado = conversacion.evaluar_quiz(quiz, {"p1": "A"})

        self.assertEqual(len(motor.historiales), 1)
        self.assertEqual(resultado["porcentaje_total"], 100)
        self.assertEqual(resultado["feedback_final"], "Buen dominio del tema.")
        self.assertEqual(
            [mensaje["role"] for mensaje in motor.historiales[0]],
            ["system", "user", "user"],
        )
        payload = json.loads(
            motor.historiales[0][-1]["content"].split("\n\n", 1)[1]
        )
        self.assertEqual(payload["resultados"]["porcentaje_total"], 100)
        self.assertEqual(
            payload["resultados"]["retroalimentacion"][0]["correcta"],
            True,
        )

    def test_prepara_todas_las_preguntas_de_desarrollo_incluso_sin_respuesta(self):
        quiz = {
            **self.quiz,
            "paginas": [
                *self.quiz["paginas"],
                {
                    "id": "p3",
                    "tipo": "desarrollo",
                    "pregunta": "Explica el segundo concepto.",
                    "guia_evaluacion": "Incluye la idea principal.",
                    "respuesta_sugerida": "Idea principal.",
                },
            ],
        }

        respuestas = preparar_respuestas_desarrollo(
            quiz,
            {"p2": "Respuesta."},
        )

        self.assertEqual([item["pregunta_id"] for item in respuestas], ["p2", "p3"])
        self.assertEqual(respuestas[1]["respuesta_alumno"], "")

    def test_evalua_tambien_desarrollo_sin_respuesta_al_finalizar(self):
        quiz = {
            **self.quiz,
            "paginas": [
                *self.quiz["paginas"],
                {
                    "id": "p3",
                    "tipo": "desarrollo",
                    "pregunta": "Explica el segundo concepto.",
                    "guia_evaluacion": "Incluye la idea principal.",
                    "respuesta_sugerida": "Idea principal.",
                },
            ],
        }
        contenido = json.dumps({
            "evaluaciones": [
                {
                    "pregunta_id": "p2",
                    "puntaje_normalizado": 0.5,
                    "feedback_especifico": "Parcial.",
                },
                {
                    "pregunta_id": "p3",
                    "puntaje_normalizado": 0.0,
                    "feedback_especifico": "No respondiste esta pregunta.",
                },
            ]
        })
        motor = FakeMotor(contenido)

        with tempfile.TemporaryDirectory() as directorio:
            store = QuizStore(directorio)
            QuizManager(store).guardar(quiz)
            resultado = evaluar_quiz(
                motor,
                quiz,
                {"p2": "Respuesta parcial."},
                store=store,
            )

        evaluacion_payload = json.loads(
            motor.historiales[0][-1]["content"].split("\n\n", 1)[1]
        )
        self.assertEqual(
            [
                item["pregunta_id"]
                for item in evaluacion_payload["respuestas"]
            ],
            ["p2", "p3"],
        )
        self.assertEqual(
            evaluacion_payload["respuestas"][1]["respuesta_alumno"],
            "",
        )
        self.assertEqual(resultado["porcentaje_total"], 17)

    def test_extrae_quiz_desde_texto_y_resultado_de_tool(self):
        quiz_json = json.dumps(self.quiz, ensure_ascii=False)
        self.assertEqual(
            quiz_desde_mensaje(f"Quiz generado:\n{quiz_json}"),
            self.quiz,
        )
        resultado = repr({"quiz_data": self.quiz})
        self.assertEqual(quiz_desde_resultado_herramienta(resultado), self.quiz)


if __name__ == "__main__":
    unittest.main()
