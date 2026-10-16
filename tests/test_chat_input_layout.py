"""Layout del composer de chat: el botón de enviar no puede salirse.

El campo de texto de Tk tiene un ancho natural de 80 caracteres; si se
empaqueta antes que el botón de envío, se lleva todo el ancho disponible y
deja al botón reducido a un píxel fuera del composer. Este test congela ese
comportamiento.
"""

import tkinter as tk
import unittest

from ui.desktop_app import AetheraDesktopApp


class _MotorFalso:
    modelo = "modelo-falso"

    def __call__(self, *_args, **_kwargs):
        raise RuntimeError("el motor real no debe invocarse en los tests")


def _hay_display():
    try:
        raiz = tk.Tk()
    except tk.TclError:
        return False
    raiz.withdraw()
    raiz.destroy()
    return True


DISPLAY_DISPONIBLE = _hay_display()


@unittest.skipUnless(DISPLAY_DISPONIBLE, "requiere un display para Tk")
class ChatInputLayoutTests(unittest.TestCase):
    def setUp(self):
        self.app = AetheraDesktopApp(
            _MotorFalso(),
            [{"role": "system", "content": "sistema"}],
            {},
            lambda *_args: None,
        )
        self.app.show_page("Asistente IA")
        self.app.root.update()

    def tearDown(self):
        self.app.cerrar()

    def _geometria(self):
        boton = self.app.send_button
        composer = boton.master
        self.app.root.update_idletasks()
        self.app.root.update()
        return boton, composer

    def assert_boton_cabe(self, mensaje):
        boton, composer = self._geometria()
        self.assertGreaterEqual(
            boton.winfo_width(),
            boton.winfo_reqwidth(),
            f"{mensaje}: el botón quedó comprimido ({boton.winfo_width()} px)",
        )
        self.assertLessEqual(
            boton.winfo_rootx() + boton.winfo_width(),
            composer.winfo_rootx() + composer.winfo_width(),
            f"{mensaje}: el botón se sale del composer",
        )
        self.assertLessEqual(
            boton.winfo_rootx() + boton.winfo_width(),
            self.app.root.winfo_rootx() + self.app.root.winfo_width(),
            f"{mensaje}: el botón se sale de la ventana",
        )

    def test_el_boton_de_enviar_cabe_en_el_composer(self):
        self.assert_boton_cabe("ventana")

    def test_el_boton_de_enviar_cabe_en_pantalla_completa(self):
        try:
            self.app._toggle_fullscreen()
            self.app.root.update()
        except tk.TclError:
            self.skipTest("el entorno gráfico no admite pantalla completa")
        try:
            self.assert_boton_cabe("pantalla completa")
        finally:
            self.app._toggle_fullscreen()
            self.app.root.update()


if __name__ == "__main__":
    unittest.main()
