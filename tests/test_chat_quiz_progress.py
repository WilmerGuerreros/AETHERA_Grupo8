import unittest
from unittest.mock import Mock, patch

from ui.chat.components.chat_quiz_view import ChatQuizView


class FakeWidget:
    def __init__(self, text=""):
        self.text = text

    def winfo_exists(self):
        return True

    def get(self, _start, _end):
        return self.text


class FakeShell(FakeWidget):
    def __init__(self):
        super().__init__()
        self.after_cancel = Mock()


class ChatQuizProgressTests(unittest.TestCase):
    def setUp(self):
        self.host = ChatQuizView()
        shell = FakeShell()
        text = FakeWidget("Borrador sin guardar")
        quiz = {
            "paginas": [
                {"id": "p1", "tipo": "desarrollo"},
                {"id": "p2", "tipo": "alternativa"},
            ]
        }
        self.state = {
            "index": 0,
            "answers": {},
            "text": text,
            "progress_pending": False,
            "progress_target": None,
            "progress_after_id": "save-id",
            "progress_dirty": True,
            "answer_pending": False,
            "answer_error": "",
            "draw_page": Mock(),
        }
        self.host._active_chat_quiz_sessions = [(shell, quiz, self.state)]

    @patch("ui.chat.components.chat_quiz_view.guardar_progreso_quiz")
    def test_flushes_unsaved_draft_before_navigation(self, save_progress):
        save_progress.side_effect = lambda _quiz, _index, answers: answers.copy()

        self.assertTrue(self.host._flush_chat_quiz_progress_before_navigation())

        save_progress.assert_called_once_with(
            self.host._active_chat_quiz_sessions[0][1],
            0,
            {"p1": "Borrador sin guardar"},
        )
        self.host._active_chat_quiz_sessions[0][0].after_cancel.assert_called_once_with(
            "save-id"
        )
        self.assertFalse(self.state["progress_dirty"])
        self.assertEqual(self.state["answers"], {"p1": "Borrador sin guardar"})

    @patch(
        "ui.chat.components.chat_quiz_view.guardar_progreso_quiz",
        side_effect=OSError("disco no disponible"),
    )
    def test_blocks_navigation_and_shows_error_when_flush_fails(self, _save_progress):
        self.assertFalse(self.host._flush_chat_quiz_progress_before_navigation())

        self.assertEqual(
            self.state["answer_error"],
            "No se pudo guardar el avance: disco no disponible",
        )
        self.state["draw_page"].assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
