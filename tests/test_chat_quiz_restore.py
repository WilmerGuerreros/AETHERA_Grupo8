import unittest
from unittest.mock import patch

from agent.tools.crear_quiz import crear_quiz as crear_quiz_herramienta
from core.quizzes import quiz_desde_resultado_herramienta


class ChatQuizRestoreTests(unittest.TestCase):
    def test_tool_result_keeps_quiz_recoverable_from_chat_history(self):
        quiz = {
            "quiz_id": "quiz_restore_test",
            "quiz_titulo": "Quiz de restauración",
            "paginas": [
                {
                    "id": "p1",
                    "tipo": "alternativa",
                    "pregunta": "¿Cuánto es 2 + 2?",
                    "alternativas": {"A": "4", "B": "5"},
                    "retroalimentacion": {
                        "A": "Correcto.",
                        "B": "Incorrecto.",
                    },
                    "respuesta_correcta": "A",
                }
            ],
        }
        with (
            patch("agent.tools.crear_quiz.construir_quiz", return_value=quiz),
            patch("agent.tools.crear_quiz.guardar_quiz") as guardar_quiz,
        ):
            resultado = crear_quiz_herramienta(
                "Quiz de restauración",
                [["alternative", "¿Cuánto es 2 + 2?", ["4", "5"], "4", "Correcto."]],
            )

        guardar_quiz.assert_called_once_with(quiz)
        self.assertEqual(quiz_desde_resultado_herramienta(resultado), quiz)


if __name__ == "__main__":
    unittest.main()
