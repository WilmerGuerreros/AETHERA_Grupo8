import unittest

from ui.utilidades import MARKDOWN_LIST, analizar_markdown_en_linea
from ui.chat.components.chat_history import ChatHistory


class MarkdownRenderingTests(unittest.TestCase):
    def test_inline_styles_are_extracted_from_quiz_feedback(self):
        self.assertEqual(
            list(
                analizar_markdown_en_linea(
                    "-**Objetivo de la estadística inferencial**: "
                    "comprendiste la *idea principal*."
                )
            ),
            [
                ("-", None),
                ("Objetivo de la estadística inferencial", "bold"),
                (": comprendiste la ", None),
                ("idea principal", "italic"),
                (".", None),
            ],
        )

    def test_nested_emphasis_and_other_inline_markdown(self):
        self.assertEqual(
            list(analizar_markdown_en_linea(
                "***importante***, __fuerte__, ~~anterior~~ y `código`"
            )),
            [
                ("importante", "bold_italic"),
                (", ", None),
                ("fuerte", "bold"),
                (", ", None),
                ("anterior", "strike"),
                (" y ", None),
                ("código", "code"),
            ],
        )

    def test_lists_without_space_before_markdown_are_recognized(self):
        for line, marker, text in (
            ("-**Elemento**", "-", "**Elemento**"),
            ("1.**Elemento**", "1.", "**Elemento**"),
        ):
            with self.subTest(line=line):
                match = MARKDOWN_LIST.match(line)
                self.assertIsNotNone(match)
                self.assertEqual(match.groups(), ("", marker, text))

    def test_long_quiz_feedback_can_expand_for_scrollable_results(self):
        chat_history = ChatHistory()

        self.assertEqual(
            chat_history._estimate_message_lines("x" * 1000, 10, max_lines=None),
            50,
        )
        self.assertEqual(
            chat_history._estimate_message_lines("x" * 1000, 10),
            28,
        )


if __name__ == "__main__":
    unittest.main()
