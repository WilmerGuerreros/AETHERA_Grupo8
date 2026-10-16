"""El historial del agente debe serializar a JSON tras usar herramientas.

Ollama devuelve las llamadas a herramientas como modelos pydantic
(``Message.ToolCall``). Si el agente los guarda tal cual en el historial,
Data no puede escribir la transcripción y el turno completo falla *después*
de que la herramienta ya se haya ejecutado.
"""

import json
import tempfile
import unittest
from pathlib import Path

import ollama

from agent.session import AgentSession
from agent.tools.registro import Herramienta
from data.chat_sessions import ChatArchiveStore


class _MotorConToolCall:
    """Motor falso que devuelve una llamada a herramienta real de ollama."""

    modelo = "modelo-falso"

    def __init__(self) -> None:
        self.rondas = 0

    def generar_stream(self, historial, herramientas=None):
        self.rondas += 1
        if self.rondas == 1:
            yield {
                "message": {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [
                        ollama.Message.ToolCall(
                            function=ollama.Message.ToolCall.Function(
                                name="crear_quiz",
                                arguments={"tema": "algebra"},
                            )
                        )
                    ],
                }
            }
            return
        yield {"message": {"role": "assistant", "content": "Te preparé el quiz."}}


class HistorialConToolCallsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.historial: list[dict] = [{"role": "system", "content": "sistema"}]
        self.argumentos_recibidos: dict = {}

        def crear_quiz(tema: str):
            """Crea un quiz sobre el tema indicado."""
            self.argumentos_recibidos["tema"] = tema
            return '{"quiz_id": "q1"}'

        registro = {
            "crear_quiz": Herramienta(
                nombre="crear_quiz",
                funcion=crear_quiz,
                categoria="quiz",
            )
        }
        self.sesion = AgentSession(_MotorConToolCall(), self.historial, registro)

    def test_el_historial_queda_serializable_en_json(self) -> None:
        eventos = list(self.sesion.procesar_turno("crea un quiz de algebra"))

        self.assertIn("complete", [tipo for tipo, _ in eventos])
        try:
            json.dumps(self.historial, ensure_ascii=False)
        except TypeError as error:
            self.fail(f"El historial no se puede guardar en JSON: {error}")

    def test_las_llamadas_quedan_como_dicts_planos(self) -> None:
        list(self.sesion.procesar_turno("crea un quiz de algebra"))

        asistente = next(m for m in self.historial if m.get("tool_calls"))
        llamada = asistente["tool_calls"][0]
        self.assertIsInstance(llamada, dict)
        self.assertEqual(llamada["function"]["name"], "crear_quiz")
        self.assertEqual(llamada["function"]["arguments"], {"tema": "algebra"})
        self.assertEqual(self.argumentos_recibidos["tema"], "algebra")

    def test_data_puede_guardar_y_recargar_la_transcripcion(self) -> None:
        list(self.sesion.procesar_turno("crea un quiz de algebra"))

        with tempfile.TemporaryDirectory() as tmpdir:
            store = ChatArchiveStore(root=Path(tmpdir))
            store.create_directory("a1b2c3d4", "Quiz de algebra")
            store.save_history("a1b2c3d4", self.historial)
            recargado = store.load_history("a1b2c3d4")

        self.assertEqual(recargado, self.historial)
        asistente = next(m for m in recargado if m.get("tool_calls"))
        self.assertEqual(
            asistente["tool_calls"][0]["function"]["arguments"],
            {"tema": "algebra"},
        )


if __name__ == "__main__":
    unittest.main()
