import json
import tempfile
import unittest
from types import SimpleNamespace

from core.quizzes import (
    QuizManager,
    cargar_intento,
    crear_quiz,
    eliminar_intento,
    evaluar_quiz,
    guardar_intento,
    quiz_desde_mensaje,
    quiz_desde_resultado_herramienta,
    validar_quiz,
)


class FakeMotor:
    def __init__(self, content):
        self.content = content
        self.historial = None

    def generar_respuesta(self, historial):
        self.historial = historial
        return SimpleNamespace(message=SimpleNamespace(content=self.content))


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
            [["alternative", "¿1 + 1?", ["2", "3"], "2"]],
        )

        self.assertEqual(quiz["quiz_titulo"], "Quiz generado")
        self.assertEqual(quiz["quiz_id"].split("_", 1)[0], "quiz")
        self.assertEqual(validar_quiz(quiz)["paginas"][0]["id"], "p1")

    def test_persiste_y_carga_quiz_mediante_core(self):
        with tempfile.TemporaryDirectory() as directorio:
            manager = QuizManager(directorio)
            manager.guardar(self.quiz)

            self.assertEqual(manager.cargar("demo_quiz"), self.quiz)
            self.assertEqual(manager.listar(), [self.quiz])

    def test_guarda_carga_y_elimina_intento(self):
        with tempfile.TemporaryDirectory() as directorio:
            guardar_intento(
                self.quiz,
                1,
                {"p1": "A", "p2": "Respuesta parcial."},
                directorio,
            )

            self.assertEqual(
                cargar_intento(self.quiz, directorio),
                {
                    "indice": 1,
                    "respuestas": {
                        "p1": "A",
                        "p2": "Respuesta parcial.",
                    },
                },
            )
            eliminar_intento("demo_quiz", directorio)
            self.assertIsNone(cargar_intento(self.quiz, directorio))

    def test_rechaza_respuesta_guardada_que_no_existe(self):
        with tempfile.TemporaryDirectory() as directorio:
            with self.assertRaisesRegex(ValueError, "no es válida"):
                guardar_intento(self.quiz, 0, {"p1": "Z"}, directorio)

    def test_califica_respuesta_abierta_y_alternativa(self):
        contenido = json.dumps({
            "evaluaciones": [
                {
                    "pregunta_id": "p2",
                    "porcentaje": 50,
                    "retroalimentacion": "La respuesta está parcialmente completa.",
                }
            ]
        })

        motor = FakeMotor(contenido)
        resultado = evaluar_quiz(
            motor,
            self.quiz,
            {"p1": "A", "p2": "Respuesta parcial."},
        )

        self.assertEqual(resultado["puntaje"], 100)
        self.assertEqual(resultado["porcentaje_desarrollo"], 50)
        self.assertEqual(
            [mensaje["role"] for mensaje in motor.historial],
            ["system", "user"],
        )
        self.assertEqual(
            [item["pregunta_id"] for item in resultado["retroalimentacion"]],
            ["p1", "p2"],
        )

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
