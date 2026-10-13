import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from ui.quiz.logica import (
    QuizLogic,
    quiz_desde_mensaje,
    quiz_desde_resultado_herramienta,
)


class FakeMotor:
    def __init__(self, response):
        self.response = response

    def generar_respuesta(self, historial):
        return SimpleNamespace(
            message=SimpleNamespace(content=self.response)
        )


class QuizLogicTests(unittest.TestCase):
    def setUp(self):
        self.quiz = {
            "test_id": "demo_quiz",
            "test_titulo": "Quiz de prueba",
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

    def test_extrae_quiz_json_de_respuesta_de_chat(self):
        texto = "Aquí tienes el quiz:\n" + json.dumps(
            self.quiz,
            ensure_ascii=False,
        )

        self.assertEqual(quiz_desde_mensaje(texto), self.quiz)
        self.assertIsNone(quiz_desde_mensaje("Respuesta normal del asistente."))

    def test_extrae_quiz_devuelto_por_la_herramienta(self):
        resultado_herramienta = repr(
            {
                "test_id": "demo_quiz",
                "ruta": "tests/fixtures/quices/demo_quiz.json",
                "quiz_data": self.quiz,
            }
        )

        self.assertEqual(
            quiz_desde_resultado_herramienta(resultado_herramienta),
            self.quiz,
        )

    def test_puntaje_de_alternativas_separa_porcentaje_de_desarrollo(self):
        model_response = json.dumps(
            {
                "evaluaciones": [
                    {
                        "pregunta_id": "p2",
                        "porcentaje": 50,
                        "retroalimentacion": "La respuesta está parcialmente completa.",
                    }
                ]
            }
        )
        with tempfile.TemporaryDirectory() as directory:
            logic = QuizLogic(
                FakeMotor(model_response),
                Path(directory) / "intentos",
            )

            result = logic.evaluar(
                self.quiz,
                {"p1": "A", "p2": "Respuesta parcial."},
            )

        self.assertEqual(result["puntaje"], 100)
        self.assertEqual(result["porcentaje_desarrollo"], 50)
        self.assertEqual(
            [item["pregunta_id"] for item in result["retroalimentacion"]],
            ["p1", "p2"],
        )
        self.assertEqual(result["retroalimentacion"][1]["porcentaje"], 50)

    def test_guardar_y_recuperar_intento_incompleto(self):
        with tempfile.TemporaryDirectory() as directory:
            logic = QuizLogic(FakeMotor("{}"), Path(directory) / "intentos")
            logic.guardar_intento(
                self.quiz,
                1,
                {"p1": "A", "p2": "Respuesta parcial."},
            )

            attempt = logic.cargar_intento(self.quiz)

        self.assertEqual(
            attempt,
            {
                "indice": 1,
                "respuestas": {
                    "p1": "A",
                    "p2": "Respuesta parcial.",
                },
            },
        )

    def test_rechaza_archivo_de_intento_con_formato_invalido(self):
        with tempfile.TemporaryDirectory() as directory:
            attempt_dir = Path(directory) / "intentos"
            logic = QuizLogic(FakeMotor("{}"), attempt_dir)
            attempt_dir.mkdir()
            (attempt_dir / "demo_quiz.json").write_text("[]", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "no es válido"):
                logic.cargar_intento(self.quiz)

    def test_rechaza_evaluacion_del_modelo_con_ids_incompletos(self):
        model_response = json.dumps({"evaluaciones": []})
        with tempfile.TemporaryDirectory() as directory:
            logic = QuizLogic(FakeMotor(model_response), Path(directory) / "intentos")

            with self.assertRaisesRegex(ValueError, "no evaluó todas"):
                logic.evaluar(self.quiz, {"p2": "Respuesta"})


if __name__ == "__main__":
    unittest.main()
