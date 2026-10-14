"""Pruebas del calendario: repositorio de Data y orquestación de Core (sin Tk)."""

import inspect
import tempfile
import unittest
from datetime import date
from pathlib import Path

import core.calendar as core_calendar
from core.calendar import (
    borrar_evento_personal,
    buscar_eventos,
    crear_evento,
    obtener_eventos_semana,
)
from data.calendar import (
    CalendarioInvalido,
    CalendarStore,
    EventoAmbiguo,
    EventoNoEncontrado,
)


ACADEMICO = (
    "BEGIN:VCALENDAR\r\n"
    "VERSION:2.0\r\n"
    "BEGIN:VEVENT\r\n"
    "UID:ev-1@aethera\r\n"
    "DTSTART;VALUE=DATE:20261105\r\n"
    "DTEND;VALUE=DATE:20261107\r\n"
    "SUMMARY:Semana de examenes\r\n"
    "CATEGORIES:evaluation_week\r\n"
    "END:VEVENT\r\n"
    "BEGIN:VEVENT\r\n"
    "UID:ev-2@aethera\r\n"
    "DTSTART:20261106T090000\r\n"
    "DTEND:20261106T110000\r\n"
    "SUMMARY:Taller de bienestar\r\n"
    "CATEGORIES:wellbeing_activity\r\n"
    "DESCRIPTION:Con respaldo\r\n"
    "END:VEVENT\r\n"
    "END:VCALENDAR\r\n"
)


class CalendarStoreTests(unittest.TestCase):
    def setUp(self):
        self.directorio = Path(tempfile.mkdtemp(prefix="aethera-cal-test-"))
        self.academico = self.directorio / "academico.ics"
        self.academico.write_text(ACADEMICO, encoding="utf-8")
        self.personal = self.directorio / "personal.ics"
        self.store = CalendarStore(
            ruta_personal=self.personal, ruta_academico=self.academico
        )

    def _store(self):
        return CalendarStore(
            ruta_personal=self.personal, ruta_academico=self.academico
        )

    def test_listar_academico_sin_filtros(self):
        eventos = self._store().listar("academico")

        self.assertEqual(
            [evento["resumen"] for evento in eventos],
            ["Semana de examenes", "Taller de bienestar"],
        )

    def test_listar_filtra_por_categoria(self):
        eventos = self._store().listar(
            "academico", categorias={"evaluation_week"}
        )

        self.assertEqual([evento["uid"] for evento in eventos], ["ev-1@aethera"])

    def test_listar_filtra_por_rango(self):
        eventos = self._store().listar(
            "academico", fecha_inicio=date(2026, 11, 6), fecha_fin=date(2026, 11, 6)
        )

        self.assertEqual(
            [evento["resumen"] for evento in eventos],
            ["Semana de examenes", "Taller de bienestar"],
        )

    def test_evento_con_hora_expone_horas(self):
        evento = self._store().listar(
            "academico", categorias={"wellbeing_activity"}
        )[0]

        self.assertEqual(evento["hora_inicio"], "09:00")
        self.assertEqual(evento["hora_fin"], "11:00")
        self.assertEqual(evento["fecha_inicio"], "2026-11-06")

    def test_personal_inexistente_equivale_a_vacio(self):
        self.assertEqual(self.store.listar("personal"), [])

    def test_agregar_y_listar_personal(self):
        uid = self.store.agregar(
            "Repaso",
            date(2026, 12, 1),
            date(2026, 12, 2),
            "Detalle",
        )

        eventos = self.store.listar("personal")

        self.assertEqual(len(eventos), 1)
        self.assertEqual(eventos[0]["uid"], uid)
        self.assertEqual(eventos[0]["resumen"], "Repaso")
        self.assertEqual(eventos[0]["categoria"], "personal")
        self.assertEqual(eventos[0]["descripcion"], "Detalle")

    def test_eliminar_quita_el_evento(self):
        uid = self.store.agregar("Uno", date(2026, 12, 1))
        self.store.agregar("Dos", date(2026, 12, 2))

        self.store.eliminar(uid)

        self.assertEqual(
            [evento["resumen"] for evento in self.store.listar("personal")],
            ["Dos"],
        )

    def test_eliminar_inexistente_lanza_excepcion(self):
        self.store.agregar("Uno", date(2026, 12, 1))

        with self.assertRaises(EventoNoEncontrado):
            self.store.eliminar("no-existe@aethera")

    def test_eliminar_identificador_ambiguo(self):
        self.personal.write_text(
            "BEGIN:VCALENDAR\r\n"
            "BEGIN:VEVENT\r\nUID:dup@aethera\r\n"
            "DTSTART;VALUE=DATE:20261201\r\nDTEND;VALUE=DATE:20261202\r\n"
            "SUMMARY:A\r\nEND:VEVENT\r\n"
            "BEGIN:VEVENT\r\nUID:dup@aethera\r\n"
            "DTSTART;VALUE=DATE:20261203\r\nDTEND;VALUE=DATE:20261204\r\n"
            "SUMMARY:B\r\nEND:VEVENT\r\n"
            "END:VCALENDAR\r\n",
            encoding="utf-8",
        )

        with self.assertRaises(EventoAmbiguo):
            self.store.eliminar("dup@aethera")

    def test_agregar_sobre_archivo_invalido(self):
        self.personal.write_text("contenido roto", encoding="utf-8")

        with self.assertRaises(CalendarioInvalido):
            self.store.agregar("X", date(2026, 12, 1))

    def test_eliminar_de_archivo_invalido(self):
        self.personal.write_text("contenido roto", encoding="utf-8")

        with self.assertRaises(CalendarioInvalido):
            self.store.eliminar("x@aethera")


class CalendarioCoreTests(unittest.TestCase):
    def setUp(self):
        self.directorio = Path(tempfile.mkdtemp(prefix="aethera-cal-core-"))
        self.academico = self.directorio / "academico.ics"
        self.academico.write_text(ACADEMICO, encoding="utf-8")
        self.personal = self.directorio / "personal.ics"
        self.store = CalendarStore(
            ruta_personal=self.personal, ruta_academico=self.academico
        )

    def test_fecha_invalida(self):
        resultado = buscar_eventos("any", fecha_inicio="2026/11/05")

        self.assertIn("error", resultado[0])

    def test_rango_invertido(self):
        resultado = buscar_eventos(
            "any", fecha_inicio="2026-11-05", fecha_fin="2026-11-01"
        )

        self.assertIn("error", resultado[0])

    def test_categoria_invalida(self):
        resultado = buscar_eventos("no-existe", store=self.store)

        self.assertIn("error", resultado[0])

    def test_origen_invalido(self):
        resultado = buscar_eventos("any", origen="otro", store=self.store)

        self.assertIn("error", resultado[0])

    def test_busqueda_valida_ordena_por_fecha_y_resumen(self):
        eventos = buscar_eventos(
            "any",
            fecha_inicio="2026-11-01",
            fecha_fin="2026-11-30",
            origen="academico",
            store=self.store,
        )

        self.assertEqual(
            [evento["resumen"] for evento in eventos],
            ["Semana de examenes", "Taller de bienestar"],
        )

    def test_busqueda_delega_el_filtro_de_categoria(self):
        eventos = buscar_eventos(
            "evaluation_week",
            fecha_inicio="2026-11-01",
            fecha_fin="2026-11-30",
            origen="academico",
            store=self.store,
        )

        self.assertEqual([evento["uid"] for evento in eventos], ["ev-1@aethera"])

    def test_obtener_eventos_semana_origen_invalido(self):
        with self.assertRaises(ValueError):
            obtener_eventos_semana(
                date(2026, 11, 2), date(2026, 11, 8), "Otro", "Bienestar"
            )

    def test_obtener_eventos_semana_filtra_por_categoria(self):
        eventos = obtener_eventos_semana(
            date(2026, 11, 2),
            date(2026, 11, 8),
            "Académico",
            "Bienestar",
            store=self.store,
        )

        self.assertEqual([evento["uid"] for evento in eventos], ["ev-2@aethera"])

    def test_crear_evento_valida_titulo(self):
        self.assertIn("error", crear_evento("   ", "2026-11-05", store=self.store))

    def test_crear_evento_valida_horas(self):
        resultado = crear_evento(
            "X",
            "2026-11-05",
            hora_inicio="09:00",
            hora_fin="",
            store=self.store,
        )

        self.assertIn("error", resultado)

    def test_crear_y_borrar_evento_personal(self):
        resultado = crear_evento(
            "Reunión",
            "2026-11-05",
            hora_inicio="09:30",
            hora_fin="11:00",
            store=self.store,
        )

        self.assertEqual(resultado["mensaje"], "Evento creado en el calendario Personal.")
        creados = self.store.listar("personal")
        self.assertEqual(len(creados), 1)

        borrado = borrar_evento_personal(creados[0], store=self.store)

        self.assertEqual(
            borrado["mensaje"], "Evento eliminado del calendario Personal."
        )
        self.assertEqual(self.store.listar("personal"), [])

    def test_borrar_rechaza_eventos_academicos(self):
        resultado = borrar_evento_personal(
            {"origen": "academico", "uid": "x"}, store=self.store
        )

        self.assertIn("error", resultado)

    def test_core_no_conoce_el_formato_ni_las_rutas(self):
        codigo = inspect.getsource(core_calendar)

        self.assertNotIn("BEGIN:VEVENT", codigo)
        self.assertNotIn("VCALENDAR", codigo)
        self.assertNotIn(".ics", codigo)
        self.assertNotIn("read_text", codigo)
        self.assertNotIn("resource_path", codigo)
        self.assertNotIn("user_calendar_path", codigo)


if __name__ == "__main__":
    unittest.main()
