"""Pruebas del modelo de presentación del chat (sin Tk)."""

import json
import unittest

from ui.estado.chat import ESTADO_LIBRE, ESTADO_PENSANDO, SALUDO, ChatStore


def _quiz(quiz_id="quiz_store"):
    return {
        "quiz_id": quiz_id,
        "quiz_titulo": "Quiz de prueba",
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


class ChatStoreTests(unittest.TestCase):
    def test_proyecta_el_historial_ignorando_mensajes_silenciosos(self):
        historial = [
            {"role": "system", "content": "Prompt inicial.", "silent": True},
            {"role": "user", "content": "Hola"},
            {"role": "assistant", "content": "Buenas"},
        ]
        entradas = ChatStore(historial).entradas()

        self.assertEqual(
            [(entrada["rol"], entrada["texto"]) for entrada in entradas],
            [("user", "Hola"), ("assistant", "Buenas")],
        )

    def test_sin_conversacion_presenta_el_saludo(self):
        self.assertEqual(
            ChatStore([]).entradas(),
            [{"rol": "saludo", "texto": SALUDO}],
        )

    def test_la_respuesta_en_curso_sobrevive_al_cambio_de_seccion(self):
        store = ChatStore([{"role": "user", "content": "Pregunta"}])
        store.iniciar_turno()
        store.agregar_token("Hola ")
        store.agregar_token("mundo")

        # Reconstruir equivale a pedir las entradas de nuevo tras navegar.
        primera = store.entradas()
        segunda = store.entradas()

        self.assertEqual(primera, segunda)
        self.assertEqual(primera[-1], {"rol": "stream", "texto": "Hola mundo"})
        self.assertTrue(store.ocupado)
        self.assertEqual(store.estado, ESTADO_PENSANDO)

    def test_finalizar_turno_quita_el_stream_porque_el_historial_lo_tiene(self):
        historial = [{"role": "user", "content": "P"}]
        store = ChatStore(historial)
        store.iniciar_turno()
        store.agregar_token("parcial")
        historial.append({"role": "assistant", "content": "parcial"})

        store.finalizar_turno()
        entradas = store.entradas()

        self.assertEqual(entradas[-1], {"rol": "assistant", "texto": "parcial"})
        self.assertFalse(store.ocupado)
        self.assertEqual(store.estado, ESTADO_LIBRE)
        self.assertEqual(store.stream_texto, "")

    def test_el_error_se_conserva_en_su_posicion_entre_turnos(self):
        historial = [{"role": "user", "content": "primera"}]
        store = ChatStore(historial)
        store.iniciar_turno()
        store.agregar_token("a medias")
        store.marcar_error("No pude completar la respuesta.")

        historial.append({"role": "user", "content": "segunda"})
        store.iniciar_turno()
        store.agregar_token("respuesta nueva")
        entradas = store.entradas()

        self.assertEqual(
            [entrada["rol"] for entrada in entradas],
            ["user", "error", "user", "stream"],
        )
        self.assertEqual(entradas[1]["texto"], "No pude completar la respuesta.")

    def test_el_quiz_del_turno_no_se_duplica_con_el_resultado_de_la_herramienta(self):
        quiz = _quiz()
        historial = [
            {"role": "user", "content": "créame un quiz"},
            {"role": "assistant", "content": ""},
            {
                "role": "tool",
                "name": "crear_quiz",
                "content": repr({"quiz_data": quiz}),
            },
        ]
        store = ChatStore(historial)
        store.agregar_quiz(quiz)

        quizzes = [e for e in store.entradas() if e["rol"] == "quiz"]

        self.assertEqual(len(quizzes), 1)
        self.assertEqual(quizzes[0]["quiz"]["quiz_id"], quiz["quiz_id"])

    def test_el_quiz_embebido_en_la_respuesta_no_se_duplica(self):
        quiz = _quiz()
        historial = [
            {"role": "user", "content": "créame un quiz"},
            {
                "role": "assistant",
                "content": "Te preparé uno.\n" + json.dumps(quiz, ensure_ascii=False),
            },
        ]
        store = ChatStore(historial)
        store.agregar_quiz(quiz)

        self.assertEqual(
            [entrada["rol"] for entrada in store.entradas()],
            ["user", "assistant"],
        )

    def test_no_proyecta_respuestas_sin_texto_visible(self):
        historial = [
            {"role": "user", "content": "créame un quiz"},
            {"role": "assistant", "content": "   \n", "tool_calls": [{"id": "1"}]},
            {"role": "assistant", "content": "Listo."},
        ]
        entradas = ChatStore(historial).entradas()

        self.assertEqual(
            [(entrada["rol"], entrada["texto"]) for entrada in entradas],
            [("user", "créame un quiz"), ("assistant", "Listo.")],
        )

    def test_restaura_las_ultimas_veinte_interacciones_de_memoria_bruta(self):
        interacciones = [
            {"usuario": f"Pregunta {indice}", "aethera": f"Respuesta {indice}"}
            for indice in range(25)
        ]
        store = ChatStore.desde_memoria_bruta(
            interacciones,
            nombre_carpeta="Estadística_2d34c0",
        )
        entradas = store.entradas()

        self.assertEqual(
            entradas[0],
            {"rol": "archive_notice", "folder_name": "Estadística_2d34c0"},
        )
        visibles = [entrada for entrada in entradas if entrada["rol"] == "user"]
        self.assertEqual(len(visibles), 20)
        self.assertEqual(visibles[0]["texto"], "Pregunta 5")
        self.assertEqual(visibles[-1]["texto"], "Pregunta 24")

        store.agregar_mensaje("user", "Pregunta actual")
        store.agregar_mensaje("assistant", "Respuesta actual")
        entradas_actualizadas = store.entradas()
        self.assertEqual(
            entradas_actualizadas[0],
            {"rol": "archive_notice", "folder_name": "Estadística_2d34c0"},
        )
        self.assertEqual(
            entradas_actualizadas[-2:],
            [
                {"rol": "user", "texto": "Pregunta actual"},
                {"rol": "assistant", "texto": "Respuesta actual"},
            ],
        )

    def test_menos_de_veinte_interacciones_no_muestra_aviso_de_archivo(self):
        interacciones = [
            {"usuario": f"Pregunta {indice}", "aethera": f"Respuesta {indice}"}
            for indice in range(3)
        ]

        entradas = ChatStore.desde_memoria_bruta(
            interacciones,
            nombre_carpeta="Chat_abc123",
        ).entradas()

        self.assertEqual(
            [(entrada["rol"], entrada["texto"]) for entrada in entradas],
            [
                ("user", "Pregunta 0"),
                ("assistant", "Respuesta 0"),
                ("user", "Pregunta 1"),
                ("assistant", "Respuesta 1"),
                ("user", "Pregunta 2"),
                ("assistant", "Respuesta 2"),
            ],
        )

    def test_mensajes_nuevos_se_anaden_a_la_vista_inicial(self):
        store = ChatStore.desde_memoria_bruta(
            [{"usuario": "Desde memoria bruta", "aethera": "Respuesta guardada"}],
            nombre_carpeta="Chat_abc123",
        )
        store.agregar_mensaje("user", "Pregunta de esta ejecución")
        store.agregar_mensaje("assistant", "Respuesta de esta ejecución")

        self.assertEqual(
            [entrada["texto"] for entrada in store.entradas() if entrada["rol"] != "archive_notice"],
            [
                "Desde memoria bruta",
                "Respuesta guardada",
                "Pregunta de esta ejecución",
                "Respuesta de esta ejecución",
            ],
        )

    def test_el_indicador_solo_se_actualiza_mientras_hay_turno(self):
        store = ChatStore([])
        store.actualizar_estado("Consultando crear quiz")
        self.assertEqual(store.estado, ESTADO_LIBRE)

        store.iniciar_turno()
        store.actualizar_estado("Consultando crear quiz")
        self.assertEqual(store.estado, "Consultando crear quiz")

        store.liberar()
        self.assertEqual(store.estado, ESTADO_LIBRE)
        self.assertFalse(store.ocupado)


if __name__ == "__main__":
    unittest.main()
