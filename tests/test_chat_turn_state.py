"""Pruebas de integración entre la cola de eventos y el modelo del chat."""

import unittest

from ui.chat.logica import ChatLogic
from ui.estado.chat import ChatStore


def _quiz():
    return {
        "quiz_id": "quiz_turno",
        "quiz_titulo": "Quiz del turno",
        "paginas": [
            {
                "id": "p1",
                "tipo": "alternativa",
                "pregunta": "¿2 + 2?",
                "alternativas": {"A": "4", "B": "5"},
                "retroalimentacion": {"A": "Correcto.", "B": "Incorrecto."},
                "respuesta_correcta": "A",
            }
        ],
    }


class _FakeQueue:
    def __init__(self):
        self.items = []

    def put(self, item):
        self.items.append(item)

    def get_nowait(self):
        if not self.items:
            import queue

            raise queue.Empty
        return self.items.pop(0)


class _FakeRoot:
    def __init__(self):
        self.callbacks = []

    def after(self, _delay, callback=None):
        self.callbacks.append(callback)
        return len(self.callbacks)

    def after_idle(self, callback=None):
        self.callbacks.append(callback)
        return len(self.callbacks)

    def after_cancel(self, _identifier):
        pass


class _Host(ChatLogic):
    def __init__(self, historial, current_page="Calendario"):
        self.chat_store = ChatStore(historial)
        self.event_queue = _FakeQueue()
        self.root = _FakeRoot()
        self.current_page = current_page


class ChatTurnStateTests(unittest.TestCase):
    def test_los_tokens_no_se_pierden_fuera_de_la_pagina(self):
        host = _Host([{"role": "user", "content": "Pregunta"}])
        host.chat_store.iniciar_turno()
        host.event_queue.put(("token", "Hola "))
        host.event_queue.put(("token", "mundo"))

        host._process_queue()

        self.assertEqual(host.chat_store.stream_texto, "Hola mundo")
        self.assertIn(
            {"rol": "stream", "texto": "Hola mundo"},
            host.chat_store.entradas(),
        )

    def test_complete_cierra_el_turno_y_el_historial_lo_sustituye(self):
        historial = [{"role": "user", "content": "P"}]
        host = _Host(historial)
        host.chat_store.iniciar_turno()
        host.event_queue.put(("token", "parcial"))
        # El worker añade el mensaje antes de emitir 'complete'.
        historial.append({"role": "assistant", "content": "respuesta final"})
        host.event_queue.put(("complete", None))

        host._process_queue()

        self.assertFalse(host.chat_store.ocupado)
        self.assertEqual(
            host.chat_store.entradas()[-1],
            {"rol": "assistant", "texto": "respuesta final"},
        )

    def test_complete_guarda_la_respuesta_en_la_vista_separada(self):
        host = _Host([{"role": "user", "content": "Pregunta"}])
        host._active_chat_id = "activo"
        host._chat_stores = {"activo": host.chat_store}
        host.chat_store.iniciar_turno()

        host._handle_chat_event("activo", "complete", "Respuesta nueva")

        self.assertEqual(
            host.chat_store.entradas()[-1],
            {"rol": "assistant", "texto": "Respuesta nueva"},
        )

    def test_error_queda_registrado_en_la_conversacion(self):
        host = _Host([{"role": "user", "content": "P"}])
        host.chat_store.iniciar_turno()
        host.event_queue.put(("error", "el modelo no respondió"))

        host._process_queue()

        entrada = host.chat_store.entradas()[-1]
        self.assertEqual(entrada["rol"], "error")
        self.assertIn("el modelo no respondió", entrada["texto"])

    def test_quiz_generado_se_guarda_en_el_modelo_del_turno(self):
        host = _Host([])
        host.chat_store.iniciar_turno()
        quiz = _quiz()
        host.event_queue.put(("quiz_generated", quiz))
        host.event_queue.put(("complete", None))

        host._process_queue()

        self.assertEqual(host.chat_store.quices_del_turno(), [quiz])

    def test_eventos_de_un_chat_inactivo_no_contaminan_el_chat_abierto(self):
        host = _Host([])
        host._active_chat_id = "activo"
        host._chat_stores = {
            "activo": ChatStore([]),
            "inactivo": ChatStore([]),
        }
        host._chat_stores["inactivo"].iniciar_turno()

        host._handle_chat_event("inactivo", "token", "respuesta del otro chat")

        self.assertEqual(host._chat_stores["activo"].stream_texto, "")
        self.assertEqual(
            host._chat_stores["inactivo"].stream_texto,
            "respuesta del otro chat",
        )


if __name__ == "__main__":
    unittest.main()
