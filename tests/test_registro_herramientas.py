"""Pruebas del registro de herramientas y del bucle de ejecución del agente."""

import unittest

from agente.agent_session import AgentSession
from agente.tools import REGISTRO_HERRAMIENTAS
from agente.tools.registro import Herramienta


class RegistroHerramientasTest(unittest.TestCase):
    def test_cada_clave_coincide_con_el_nombre(self):
        for clave, herramienta in REGISTRO_HERRAMIENTAS.items():
            with self.subTest(clave=clave):
                self.assertEqual(clave, herramienta.nombre)

    def test_todas_las_herramientas_tienen_metadatos(self):
        for herramienta in REGISTRO_HERRAMIENTAS.values():
            with self.subTest(herramienta=herramienta.nombre):
                self.assertTrue(herramienta.descripcion)
                self.assertTrue(herramienta.categoria)


class _MotorFalso:
    """Motor de prueba que entrega flujos de fragmentos predefinidos."""

    def __init__(self, flujos):
        self.flujos = list(flujos)
        self.herramientas_recibidas = []
        self.modelo = "modelo-de-prueba"

    def generar_stream(self, historial, herramientas=None):
        self.herramientas_recibidas.append(herramientas)
        return self.flujos.pop(0)


class AgentSessionHerramientasTest(unittest.TestCase):
    def test_envia_las_funciones_del_registro_al_motor(self):
        motor = _MotorFalso([[{"message": {"content": "hola"}}]])
        sesion = AgentSession(motor, [], REGISTRO_HERRAMIENTAS)

        sesion.procesar_turno("consulta", lambda texto: None, lambda estado: None)

        enviadas = motor.herramientas_recibidas[0]
        self.assertEqual(
            [funcion.__name__ for funcion in enviadas],
            list(REGISTRO_HERRAMIENTAS),
        )

    def test_ejecuta_una_herramienta_del_registro(self):
        llamadas = []

        def herramienta_falsa(tipo, fecha_inicio="1900-01-01"):
            """Herramienta de prueba para verificar la ejecución."""
            llamadas.append((tipo, fecha_inicio))
            return "resultado-falso"

        registro = {
            "herramienta_falsa": Herramienta(
                "herramienta_falsa", herramienta_falsa, "prueba"
            )
        }
        motor = _MotorFalso([
            [
                {
                    "message": {
                        "content": "",
                        "tool_calls": [
                            {
                                "function": {
                                    "name": "herramienta_falsa",
                                    "arguments": {"tipo": "examen"},
                                }
                            }
                        ],
                    }
                }
            ],
            [{"message": {"content": "listo"}}],
        ])
        sesion = AgentSession(motor, [], registro)

        sesion.procesar_turno("consulta", lambda texto: None, lambda estado: None)

        self.assertEqual(llamadas, [("examen", "1900-01-01")])
        self.assertIn(
            {"role": "tool", "content": "resultado-falso", "name": "herramienta_falsa"},
            sesion.historial,
        )


if __name__ == "__main__":
    unittest.main()
