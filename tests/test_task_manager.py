"""Pruebas del registro de tareas de fondo (independiente de Tk)."""

import threading
import unittest

from UI.estado.tareas import CORRIENDO, ERROR, LISTO, TaskManager


class TaskManagerTests(unittest.TestCase):
    def setUp(self):
        self.eventos = []
        self.manager = TaskManager(emit=lambda evento, valor=None: self.eventos.append((evento, valor)))

    def test_lanzar_ejecuta_en_segundo_plano_y_notifica_el_resultado(self):
        liberado = threading.Event()

        def cuerpo(_tarea):
            liberado.wait(timeout=2)
            return 42

        tarea = self.manager.lanzar("demo", cuerpo)

        self.assertEqual(tarea.estado, CORRIENDO)
        liberado.set()
        self.assertTrue(self._esperar(lambda: self.manager.tarea(tarea.id).estado == LISTO))

        self.assertEqual(self.manager.tarea(tarea.id).resultado, 42)
        self.assertTrue(any(v and v["estado"] == LISTO for _, v in self.eventos))

    def test_fallar_captura_la_excepcion_sin_propagarla(self):
        def cuerpo(_tarea):
            raise ValueError("algo salió mal")

        tarea = self.manager.lanzar("demo", cuerpo)
        self.assertTrue(self._esperar(lambda: self.manager.tarea(tarea.id).estado == ERROR))

        self.assertEqual(self.manager.tarea(tarea.id).error, "algo salió mal")

    def test_activas_solo_incluye_tareas_pendientes_o_corriendo(self):
        liberado = threading.Event()
        tarea = self.manager.lanzar("demo", lambda _t: liberado.wait(timeout=2))

        self.assertEqual([t.id for t in self.manager.activas()], [tarea.id])

        liberado.set()
        self.assertTrue(self._esperar(lambda: self.manager.activas() == []))
        self.assertIsNone(self.manager.tarea("inexistente"))

    def test_actualizar_progreso_notifica_y_conserva_contexto(self):
        def cuerpo(tarea):
            self.manager.actualizar(tarea.id, progreso=0.5, mensaje="mitad")
            return "fin"

        tarea = self.manager.lanzar("demo", cuerpo, contexto={"origen": "test"})
        self.assertTrue(self._esperar(lambda: self.manager.tarea(tarea.id).estado == LISTO))

        final = self.manager.tarea(tarea.id)
        self.assertEqual(final.contexto, {"origen": "test"})
        self.assertEqual(final.progreso, 0.5)
        self.assertEqual(final.mensaje, "mitad")

    def test_completar_y_fallar_tareas_inexistentes_no_rompen(self):
        self.assertIsNone(self.manager.completar("nada", 1))
        self.assertIsNone(self.manager.fallar("nada", RuntimeError("x")))

    def _esperar(self, condicion, timeout=2.0):
        import time

        limite = time.monotonic() + timeout
        while time.monotonic() < limite:
            if condicion():
                return True
            time.sleep(0.005)
        return condicion()


if __name__ == "__main__":
    unittest.main()
