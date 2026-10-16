"""Pruebas de la búsqueda de servicios de apoyo (sin Tk)."""

import inspect
import unittest

from agent.tools.servicios_ayuda import (
    buscar_servicios_ayuda as herramienta_buscar_servicios_ayuda,
)
from core.services import buscar_servicios_ayuda
from data.services import (
    CategoriaDesconocida,
    DistritoDesconocido,
    ServiciosFaltantes,
    SERVICIOS_POR_CATEGORIA,
    buscar_servicios,
    categorias_disponibles,
    distritos_disponibles,
    listar_servicios,
)


class ListarServiciosDataTests(unittest.TestCase):
    def test_devuelve_los_servicios_de_la_categoria_sin_distrito(self):
        servicios = listar_servicios(SERVICIOS_POR_CATEGORIA["academic_pressure"])

        self.assertEqual(len(servicios), 6)
        for servicio in servicios:
            self.assertIn("service_id", servicio)
            self.assertIn("ubicacion", servicio)
            self.assertIn("horario_atencion", servicio)

    def test_filtra_por_distrito(self):
        servicios = listar_servicios(
            SERVICIOS_POR_CATEGORIA["academic_pressure"], "DIST_VECTOR"
        )

        self.assertTrue(servicios)
        self.assertTrue(
            all(
                servicio["ubicacion"]["distrito_id"] == "DIST_VECTOR"
                for servicio in servicios
            )
        )

    def test_sin_coincidencias_devuelve_lista_vacia(self):
        self.assertEqual(listar_servicios({"SRV_AE_001"}, "DIST_NEBULA"), [])

    def test_distrito_desconocido_lanza_excepcion(self):
        with self.assertRaises(DistritoDesconocido):
            listar_servicios({"SRV_AE_001"}, "DIST_INEXISTENTE")

    def test_servicio_faltante_lanza_excepcion(self):
        with self.assertRaises(ServiciosFaltantes):
            listar_servicios({"SRV_AE_999"})

    def test_distritos_disponibles(self):
        self.assertEqual(
            distritos_disponibles(),
            {
                "DIST_GAIA",
                "DIST_HORIZON",
                "DIST_NEBULA",
                "DIST_QUANTUM",
                "DIST_VECTOR",
            },
        )


class BuscarServiciosDataTests(unittest.TestCase):
    def test_devuelve_la_categoria_y_el_distrito_normalizados(self):
        resultado = buscar_servicios("Academic_Pressure", "dist_vector")

        self.assertEqual(resultado["categoria"], "academic_pressure")
        self.assertEqual(resultado["distrito"], "DIST_VECTOR")
        self.assertTrue(resultado["servicios"])

    def test_distrito_omitido_no_filtra(self):
        resultado = buscar_servicios("academic_pressure")

        self.assertIsNone(resultado["distrito"])
        self.assertEqual(len(resultado["servicios"]), 6)

    def test_categoria_desconocida_lanza_excepcion(self):
        with self.assertRaises(CategoriaDesconocida):
            buscar_servicios("no-existe")

    def test_categoria_con_tipo_invalido_lanza_excepcion(self):
        with self.assertRaises(CategoriaDesconocida):
            buscar_servicios(123)

    def test_distrito_con_tipo_invalido_lanza_excepcion(self):
        with self.assertRaises(DistritoDesconocido):
            buscar_servicios("academic_pressure", 123)

    def test_distrito_vacio_lanza_excepcion(self):
        with self.assertRaises(DistritoDesconocido):
            buscar_servicios("academic_pressure", "   ")

    def test_distrito_desconocido_lanza_excepcion_con_opciones(self):
        with self.assertRaises(DistritoDesconocido) as contexto:
            buscar_servicios("academic_pressure", "dist_inexistente")

        self.assertIn("DIST_GAIA", str(contexto.exception))

    def test_categorias_disponibles(self):
        self.assertEqual(
            categorias_disponibles(),
            {
                "academic_pressure",
                "social_support",
                "career_concern",
                "sleep_and_routine",
                "service_navigation",
            },
        )


class BuscarServiciosCoreTests(unittest.TestCase):
    """Core solo transmite a Data y reenvía su resultado o su excepción."""

    def test_categoria_invalida_devuelve_error(self):
        self.assertIn("error", buscar_servicios_ayuda("no-existe"))

    def test_distrito_con_tipo_invalido_devuelve_error(self):
        self.assertIn("error", buscar_servicios_ayuda("academic_pressure", 123))

    def test_distrito_vacio_devuelve_error(self):
        self.assertIn("error", buscar_servicios_ayuda("academic_pressure", "   "))

    def test_distrito_desconocido_devuelve_error_con_opciones(self):
        resultado = buscar_servicios_ayuda("academic_pressure", "dist_inexistente")

        self.assertIn("error", resultado)
        self.assertIn("DIST_GAIA", resultado["error"])

    def test_devuelve_los_servicios_de_una_categoria_valida(self):
        resultado = buscar_servicios_ayuda("academic_pressure", "DIST_VECTOR")

        self.assertEqual(resultado["categoria"], "academic_pressure")
        self.assertEqual(resultado["distrito"], "DIST_VECTOR")
        self.assertTrue(resultado["servicios"])

    def test_filtros_validos_sin_coincidencias_no_es_error(self):
        import data.services as servicios

        original = servicios.listar_servicios
        servicios.listar_servicios = lambda ids_servicio, distrito=None: []
        try:
            resultado = buscar_servicios_ayuda("academic_pressure", "DIST_GAIA")
        finally:
            servicios.listar_servicios = original

        self.assertNotIn("error", resultado)
        self.assertEqual(resultado["servicios"], [])

    def test_core_no_conoce_el_recurso_ni_su_lectura(self):
        import core.services as servicios

        codigo = inspect.getsource(servicios)

        self.assertNotIn("D6_services_map", codigo)
        self.assertNotIn("leer_recurso", codigo)
        self.assertNotIn("open(", codigo)

    def test_core_no_conoce_las_categorias(self):
        import core.services as servicios

        codigo = inspect.getsource(servicios)

        for categoria in SERVICIOS_POR_CATEGORIA:
            self.assertNotIn(categoria, codigo)


class HerramientaServiciosTests(unittest.TestCase):
    def test_descripcion_incluye_categorias_y_distritos_disponibles(self):
        descripcion = herramienta_buscar_servicios_ayuda.__doc__

        self.assertIsNotNone(descripcion)
        for categoria in categorias_disponibles():
            self.assertIn(categoria, descripcion)
        for distrito in distritos_disponibles():
            self.assertIn(distrito, descripcion)


if __name__ == "__main__":
    unittest.main()
