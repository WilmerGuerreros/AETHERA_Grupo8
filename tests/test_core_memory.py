import tempfile
import unittest
from pathlib import Path

from core.memory import Memoria
from data.memory import MemoryStore


class CoreMemoryTests(unittest.TestCase):
    def _store(self, directory):
        return MemoryStore(Path(directory) / "memory")

    def test_inicia_contexto_vacio(self):
        with tempfile.TemporaryDirectory() as directory:
            memoria = Memoria(self._store(directory))

            self.assertEqual(memoria.contexto_inicial(), [{"": ""}])

    def test_persiste_turnos_y_cierra_seccion_con_resumen(self):
        with tempfile.TemporaryDirectory() as directory:
            store = self._store(directory)
            memoria = Memoria(
                store,
                max_mensajes_por_seccion=2,
                resumir=lambda contenido, modelo: "resumen generado",
            )

            memoria.guardar("hola", "respuesta 1")
            memoria.guardar("continuación", "respuesta 2")

            self.assertEqual(memoria.numero_seccion, 2)
            self.assertEqual(memoria.contador_mensajes, 0)
            self.assertEqual(store.contar_conversaciones(1), 2)
            self.assertEqual(
                [item["usuario"] for item in store.leer_interacciones(1)],
                ["hola", "continuación"],
            )
            self.assertEqual(store.leer_resumen(1), "resumen generado")
            indice = store.leer_indice()
            self.assertEqual(
                [item["id"] for item in indice["secciones"]],
                [1],
            )

    def test_recupera_seccion_y_contexto_reciente(self):
        with tempfile.TemporaryDirectory() as directory:
            store = self._store(directory)
            primera = Memoria(
                store,
                max_mensajes_por_seccion=5,
                resumir=lambda contenido, modelo: "resumen",
            )
            primera.guardar("hola", "respuesta")

            segunda = Memoria(
                store,
                max_mensajes_por_seccion=5,
                resumir=lambda contenido, modelo: "resumen",
            )
            contexto = segunda.contexto_inicial()

            self.assertEqual(segunda.numero_seccion, 1)
            self.assertEqual(segunda.contador_mensajes, 1)
            self.assertIn("hola", contexto[-1]["content"])


if __name__ == "__main__":
    unittest.main()
