"""Pruebas de los próximos eventos que muestra el Inicio (sin Tk)."""

import unittest

import ui.dashboard as dashboard
from ui.dashboard import DashboardSection


class ProximosEventosTests(unittest.TestCase):
    def _invocar(self, eventos):
        capturado = {}
        original = dashboard.buscar_eventos

        def buscar_falso(tipo, fecha_inicio=None, fecha_fin="2100-01-01", origen=None):
            capturado["tipo"] = tipo
            capturado["origen"] = origen
            return eventos

        dashboard.buscar_eventos = buscar_falso
        try:
            resultado = DashboardSection._get_upcoming_events(object())
        finally:
            dashboard.buscar_eventos = original
        return resultado, capturado

    def test_pide_todos_los_origenes(self):
        _, capturado = self._invocar([])

        self.assertIsNone(capturado["origen"])

    def test_incluye_personales_y_ordena_por_fecha_y_hora(self):
        eventos = [
            {
                "resumen": "Académico tarde",
                "fecha_inicio": "2026-10-20",
                "hora_inicio": None,
                "origen": "academico",
            },
            {
                "resumen": "Personal tarde",
                "fecha_inicio": "2026-10-15",
                "hora_inicio": "16:00",
                "origen": "personal",
            },
            {
                "resumen": "Personal mañana",
                "fecha_inicio": "2026-10-15",
                "hora_inicio": "09:00",
                "origen": "personal",
            },
        ]

        resultado, _ = self._invocar(eventos)

        self.assertEqual(
            [evento["resumen"] for evento in resultado],
            ["Personal mañana", "Personal tarde", "Académico tarde"],
        )

    def test_propaga_el_error_del_calendario(self):
        with self.assertRaises(ValueError):
            self._invocar([{"error": "No se pudieron cargar los calendarios."}])


if __name__ == "__main__":
    unittest.main()
