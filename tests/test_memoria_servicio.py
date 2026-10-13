"""Pruebas del servicio de memoria con estado explícito."""

import json
import tempfile
import unittest
from pathlib import Path

from config_de_carpetas import RutasMemoria
from memoria.servicio import Memoria


def _rutas(base: Path) -> RutasMemoria:
    memoria = base / "memoria"
    return RutasMemoria(
        historial=memoria / "HISTORIAL",
        resumen=memoria / "RESUMEN",
        indice=memoria / "INDICE",
        adjuntos=memoria / "ARCHIVOS ADJUNTOS",
    )


class MemoriaTests(unittest.TestCase):
    def _memoria(self, base, max_mensajes=20):
        rutas = _rutas(Path(base))

        def resumir(archivo, numero_seccion, modelo):
            destino = rutas.resumen / f"RESUMEN_{numero_seccion:04d}.txt"
            destino.write_text(f"resumen {numero_seccion}", encoding="utf-8")
            return destino

        memoria = Memoria(
            rutas,
            max_mensajes_por_seccion=max_mensajes,
            resumir=resumir,
        )
        return rutas, memoria

    def test_no_crea_carpetas_hasta_iniciar(self):
        with tempfile.TemporaryDirectory() as tmp:
            rutas = _rutas(Path(tmp))
            self.assertFalse(rutas.historial.exists())

            Memoria(rutas)

            self.assertTrue(rutas.historial.is_dir())
            self.assertTrue(rutas.resumen.is_dir())
            self.assertTrue(rutas.indice.is_dir())

    def test_contexto_inicial_sin_memoria(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, memoria = self._memoria(tmp)

            self.assertEqual(memoria.contexto_inicial(), [{"": ""}])

    def test_guardar_rota_seccion_y_actualiza_indice(self):
        with tempfile.TemporaryDirectory() as tmp:
            rutas, memoria = self._memoria(tmp, max_mensajes=3)

            for indice in range(3):
                memoria.guardar(f"usuario {indice}", f"respuesta {indice}")

            self.assertEqual(memoria.numero_seccion, 2)
            self.assertEqual(memoria.contador_mensajes, 0)
            self.assertTrue((rutas.historial / "HISTORIAL_0001.txt").exists())
            self.assertTrue((rutas.resumen / "RESUMEN_0001.txt").exists())

            indice = json.loads(
                (rutas.indice / "INDICE_MEMORIA.json").read_text(encoding="utf-8")
            )
            self.assertEqual(
                [seccion["id"] for seccion in indice["secciones"]],
                [1],
            )

    def test_recupera_seccion_y_contador_desde_disco(self):
        with tempfile.TemporaryDirectory() as tmp:
            rutas, primera = self._memoria(tmp, max_mensajes=5)
            primera.guardar("hola", "respuesta")

            segunda = Memoria(
                rutas,
                max_mensajes_por_seccion=5,
                resumir=lambda *args: None,
            )

            self.assertEqual(segunda.numero_seccion, 1)
            self.assertEqual(segunda.contador_mensajes, 1)

            contexto = segunda.contexto_inicial()
            self.assertEqual(contexto[0], {"": ""})
            self.assertIn("hola", contexto[-1]["content"])


if __name__ == "__main__":
    unittest.main()
