import tempfile
import unittest
from pathlib import Path

from core.memory import Memoria
from data.memory import (
    contar_conversaciones,
    leer_indice_memoria,
    leer_interacciones,
    leer_resumen_memoria,
)
from data.paths import MemoryPaths


class CoreMemoryTests(unittest.TestCase):
    def _paths(self, directory):
        root = Path(directory) / "memory"
        return MemoryPaths(
            historial=root / "HISTORIAL",
            resumen=root / "RESUMEN",
            indice=root / "INDICE",
            adjuntos=root / "ATTACHMENTS",
        )

    def test_inicia_contexto_vacio(self):
        with tempfile.TemporaryDirectory() as directory:
            memoria = Memoria(self._paths(directory))

            self.assertEqual(memoria.contexto_inicial(), [{"": ""}])

    def test_persiste_turnos_y_cierra_seccion_con_resumen(self):
        with tempfile.TemporaryDirectory() as directory:
            rutas = self._paths(directory)
            memoria = Memoria(
                rutas,
                max_mensajes_por_seccion=2,
                resumir=lambda contenido, modelo: "resumen generado",
            )

            memoria.guardar("hola", "respuesta 1")
            memoria.guardar("continuación", "respuesta 2")

            self.assertEqual(memoria.numero_seccion, 2)
            self.assertEqual(memoria.contador_mensajes, 0)
            historial = rutas.historial / "HISTORIAL_0001.txt"
            self.assertEqual(contar_conversaciones(historial), 2)
            self.assertEqual(
                [item["usuario"] for item in leer_interacciones(historial)],
                ["hola", "continuación"],
            )
            self.assertEqual(
                leer_resumen_memoria(rutas.resumen, 1),
                "resumen generado",
            )
            indice = leer_indice_memoria(rutas.indice)
            self.assertEqual(
                [item["id"] for item in indice["secciones"]],
                [1],
            )

    def test_recupera_seccion_y_contexto_reciente(self):
        with tempfile.TemporaryDirectory() as directory:
            rutas = self._paths(directory)
            primera = Memoria(
                rutas,
                max_mensajes_por_seccion=5,
                resumir=lambda contenido, modelo: "resumen",
            )
            primera.guardar("hola", "respuesta")

            segunda = Memoria(
                rutas,
                max_mensajes_por_seccion=5,
                resumir=lambda contenido, modelo: "resumen",
            )
            contexto = segunda.contexto_inicial()

            self.assertEqual(segunda.numero_seccion, 1)
            self.assertEqual(segunda.contador_mensajes, 1)
            self.assertIn("hola", contexto[-1]["content"])


if __name__ == "__main__":
    unittest.main()
