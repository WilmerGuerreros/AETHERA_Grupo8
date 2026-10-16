import unittest

from UI.desktop_app import AetheraDesktopApp


class ChatPopupPositionTests(unittest.TestCase):
    def test_popup_abre_a_la_izquierda_y_se_mantiene_en_pantalla(self):
        position = AetheraDesktopApp._chat_actions_position(
            pointer_x=190,
            pointer_y=80,
            width=160,
            height=80,
            screen_width=240,
            screen_height=200,
        )

        self.assertEqual(position, (30, 86))

    def test_popup_se_mueve_arriba_si_no_cabe_bajo_el_cursor(self):
        position = AetheraDesktopApp._chat_actions_position(
            pointer_x=20,
            pointer_y=190,
            width=160,
            height=80,
            screen_width=240,
            screen_height=200,
        )

        self.assertEqual(position, (0, 104))


if __name__ == "__main__":
    unittest.main()
