"""Smoke de interfaz: los procesos en curso sobreviven a la navegación.

Estos tests construyen la ventana real de Tk y se saltan si no hay display
disponible (por ejemplo, en un entorno de integración sin servidor gráfico).
"""

import time
import tkinter as tk
import unittest


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


def _burbujas_asistente_vacias(app):
    """Cuenta las burbujas del asistente dibujadas sin ningún cuerpo."""
    vacias = 0
    for contenedor in app.message_list.winfo_children():
        hijos = contenedor.winfo_children()
        if not hijos:
            continue
        burbuja = hijos[0]
        etiquetas = [
            hijo for hijo in burbuja.winfo_children() if isinstance(hijo, tk.Label)
        ]
        tiene_nombre = any(
            etiqueta.cget("text") == "GuIA" for etiqueta in etiquetas
        )
        if not tiene_nombre:
            continue
        cuerpo = [
            hijo
            for hijo in burbuja.winfo_children()
            if not (isinstance(hijo, tk.Label) and hijo.cget("text") == "GuIA")
        ]
        if not cuerpo:
            vacias += 1
    return vacias


@unittest.skipUnless(DISPLAY_DISPONIBLE, "requiere un display para Tk")
class NavegacionConProcesosTests(unittest.TestCase):
    def setUp(self):
        from UI.desktop_app import AetheraDesktopApp

        self.app = AetheraDesktopApp(
            _MotorFalso(),
            [{"role": "system", "content": "sistema"}],
            {},
            lambda *_args: None,
        )
        self.app.root.withdraw()

    def tearDown(self):
        self.app.cerrar()

    def _pump(self, condition, timeout=10.0):
        limite = time.monotonic() + timeout
        while time.monotonic() < limite:
            self.app.root.update()
            if condition():
                return True
            time.sleep(0.02)
        return condition()

    def test_navegar_no_pierde_los_tokens_en_curso(self):
        self.app.show_page("Asistente IA")
        self.app.root.update()
        self.app.chat_store.iniciar_turno()
        self.app.event_queue.put(("token", "Hola "))
        self.app.event_queue.put(("token", "mundo"))
        self.app._process_queue()

        self.app.show_page("Calendario")
        self.app.root.update()

        self.assertEqual(self.app.chat_store.stream_texto, "Hola mundo")
        self.app.show_page("Asistente IA")
        self.app.root.update()
        roles = [entrada["rol"] for entrada in self.app.chat_store.entradas()]
        self.assertEqual(roles, ["stream"])

    def test_turno_completo_reconstruye_la_transcripcion(self):
        def turno_falso(usuario):
            self.app.chat.historial.append({"role": "user", "content": usuario})
            for palabra in ("Respuesta", "de", "prueba"):
                yield "token", palabra + " "
            self.app.chat.historial.append(
                {"role": "assistant", "content": "Respuesta de prueba"}
            )
            yield "complete", (usuario, "Respuesta de prueba")

        self.app.chat.procesar_turno = turno_falso
        self.app.show_page("Asistente IA")
        self.app.root.update()
        self.app.message_input.insert("1.0", "hola")
        self.app._send_message()

        self.assertTrue(self.app.chat_store.ocupado)
        self.app.show_page("Calendario")
        self.app.root.update()

        self.assertTrue(
            self._pump(lambda: not self.app.chat_store.ocupado),
            "el turno no terminó",
        )
        entradas = self.app.chat_store.entradas()
        self.assertEqual(
            [entrada["rol"] for entrada in entradas], ["user", "assistant"]
        )
        self.assertEqual(entradas[-1]["texto"], "Respuesta de prueba")

        self.app.show_page("Asistente IA")
        self.app.root.update()
        self.assertFalse(self.app.send_button.disabled)

    def test_no_dibuja_burbujas_vacias_del_asistente(self):
        self.app.chat.historial[:] = [
            {"role": "system", "content": "sistema"},
            {"role": "user", "content": "créame un quiz"},
            {"role": "assistant", "content": "   \n", "tool_calls": [{"id": "1"}]},
            {"role": "assistant", "content": "Listo, aquí está tu quiz."},
        ]
        self.app.show_page("Asistente IA")
        self.app.root.update()

        self.assertEqual(_burbujas_asistente_vacias(self.app), 0)

    def test_el_stream_sin_texto_visible_no_crea_burbuja(self):
        self.app.show_page("Asistente IA")
        self.app.root.update()
        self.app.chat_store.iniciar_turno()

        self.app.event_queue.put(("token", "   \n"))
        self.app._process_queue()
        self.assertFalse(hasattr(self.app, "stream_bubble"))

        self.app.event_queue.put(("token", "Hola"))
        self.app._process_queue()
        self.assertTrue(hasattr(self.app, "stream_bubble"))

    def test_indicador_de_tareas_refleja_el_trabajo_de_fondo(self):
        base = {
            "id": "t1",
            "tipo": "prueba",
            "progreso": None,
            "mensaje": "",
            "resultado": None,
            "error": "",
            "contexto": {},
        }
        self.app._handle_tarea_actualizada({**base, "estado": "corriendo"})
        self.assertNotEqual(self.app.task_indicator.cget("text"), "")
        self.app._handle_tarea_actualizada({**base, "estado": "listo"})
        self.assertEqual(self.app.task_indicator.cget("text"), "")


if __name__ == "__main__":
    unittest.main()
