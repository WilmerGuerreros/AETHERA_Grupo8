from importlib import import_module
import inspect
import unittest
from tempfile import TemporaryDirectory
from unittest.mock import patch

from agente.tools.crear_test import crear_test as herramienta_crear_test
from dominio.quices import creacion


crear_test_module = import_module("agente.tools.crear_test")


class CrearTestToolTests(unittest.TestCase):
    def setUp(self):
        self.quiz = {
            "title": "Quiz de prueba",
            "pages": [
                [
                    "alternative",
                    "¿Cuál es la respuesta?",
                    ["Incorrecta", "Correcta"],
                    "Correcta",
                ]
            ],
        }
        self.temp_dir = TemporaryDirectory()
        self.manager = crear_test_module.QuizManager(self.temp_dir.name)
        self.manager_patcher = patch.object(
            crear_test_module,
            "QuizManager",
            return_value=self.manager,
        )
        self.manager_patcher.start()
        self.addCleanup(self.manager_patcher.stop)
        self.addCleanup(self.temp_dir.cleanup)

    def test_genera_id_timestamp_sin_pedirlo_en_datos(self):
        with patch.object(creacion.time, "time_ns", return_value=123456789):
            result = crear_test_module.crear_test(**self.quiz)

        self.assertEqual(result, "Quiz creado y guardado correctamente.")
        self.assertNotIn("123456789", result)
        quiz = self.manager.cargar("quiz_123456789")
        self.assertEqual(quiz["test_titulo"], self.quiz["title"])
        self.assertEqual(quiz["paginas"][0]["id"], "p1")
        self.assertEqual(quiz["paginas"][0]["respuesta_correcta"], "B")

    def test_crea_pregunta_de_desarrollo_sin_id_de_pagina(self):
        payload = {
            "title": "Quiz de desarrollo",
            "pages": [
                [
                    "develope",
                    "Explica la respuesta.",
                    "Menciona las causas principales.",
                    "causa, consecuencia",
                ]
            ],
        }

        result = crear_test_module.crear_test(**payload)

        self.assertEqual(result, "Quiz creado y guardado correctamente.")
        quiz = self.manager.listar()[0]
        self.assertEqual(quiz["paginas"][0]["id"], "p1")
        self.assertEqual(quiz["paginas"][0]["tipo"], "desarrollo")

    def test_rechaza_respuesta_correcta_que_no_es_una_alternativa(self):
        payload = {
            "title": "Quiz inválido",
            "pages": [["alternative", "Pregunta", ["A", "B"], "C"]],
        }

        result = crear_test_module.crear_test(**payload)

        self.assertIn("No se pudo crear", result)
        self.assertIn("coincidir con exactamente una alternativa", result)
        self.assertEqual(self.manager.listar(), [])

    def test_docstring_documenta_argumentos_simples_y_respuesta_correcta(self):
        docstring = inspect.getdoc(herramienta_crear_test)
        self.assertIn("title", docstring)
        self.assertIn("pages", docstring)
        self.assertIn("respuesta_correcta", docstring)


if __name__ == "__main__":
    unittest.main()
