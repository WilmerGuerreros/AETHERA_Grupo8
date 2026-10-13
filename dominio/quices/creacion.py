"""Herramienta del agente para validar y guardar quizzes educativos."""

import string
import time
from typing import Any

from test.quiz_manager import QuizManager


def crear_test(title: str, pages: list[list[Any]]) -> str:
    """
    Crea y guarda un quiz.

    Args:
        title: Título del quiz.
    pages: Lista ordenada de preguntas. Cada pregunta usa uno de estos formatos:
        - Alternativas: ['alternative', pregunta, [opciones...], texto_respuesta_correcta]
        - Desarrollo: ['develope', pregunta, guia_orientativa, palabras_clave_rubrica]
    """
    try:
        if not isinstance(pages, list) or not pages:
            raise ValueError("pages debe ser una lista con al menos una pregunta.")

        paginas_quiz: list[dict[str, Any]] = []
        for indice, page in enumerate(pages, start=1):
            if not isinstance(page, list) or not page:
                raise ValueError(f"pages[{indice - 1}] debe ser una lista no vacía.")

            tipo = page[0]
            if tipo == "alternative":
                if len(page) != 4:
                    raise ValueError(
                        f"pages[{indice - 1}] de alternativas debe tener "
                        "4 elementos."
                    )
                _, pregunta, opciones, respuesta_correcta = page
                if not isinstance(opciones, list) or not 2 <= len(opciones) <= 26:
                    raise ValueError(
                        f"pages[{indice - 1}] debe incluir entre 2 y 26 opciones."
                    )
                if not all(
                    isinstance(opcion, str) and opcion.strip()
                    for opcion in opciones
                ):
                    raise ValueError(
                        f"Todas las opciones de pages[{indice - 1}] "
                        "deben ser textos no vacíos."
                    )
                if not isinstance(respuesta_correcta, str) or not respuesta_correcta.strip():
                    raise ValueError(
                        f"pages[{indice - 1}] debe indicar el texto de la "
                        "respuesta correcta."
                    )
                claves = string.ascii_uppercase[: len(opciones)]
                alternativas = dict(zip(claves, opciones))
                coincidencias = [
                    clave
                    for clave, opcion in alternativas.items()
                    if opcion.strip() == respuesta_correcta.strip()
                ]
                if len(coincidencias) != 1:
                    raise ValueError(
                        f"El texto correcto de pages[{indice - 1}] debe "
                        "coincidir con exactamente una alternativa."
                    )
                clave_correcta = coincidencias[0]
                paginas_quiz.append(
                    {
                        "tipo": "alternativa",
                        "pregunta": pregunta,
                        "alternativas": alternativas,
                        "retroalimentacion": {
                            clave: (
                                "Correcto. Esta es la respuesta adecuada."
                                if clave == clave_correcta
                                else "Incorrecto. Revisa la pregunta e inténtalo de nuevo."
                            )
                            for clave in claves
                        },
                        "respuesta_correcta": clave_correcta,
                    }
                )
            elif tipo == "develope":
                if len(page) != 4:
                    raise ValueError(
                        f"pages[{indice - 1}] de desarrollo debe tener "
                        "4 elementos."
                    )
                _, pregunta, guia_orientativa, palabras_clave = page
                paginas_quiz.append(
                    {
                        "tipo": "desarrollo",
                        "pregunta": pregunta,
                        "guia_evaluacion": guia_orientativa,
                        "respuesta_sugerida": palabras_clave,
                    }
                )
            else:
                raise ValueError(
                    f"pages[{indice - 1}] debe comenzar con 'alternative' "
                    "o 'develope'."
                )

        datos_quiz = {
            "test_id": f"quiz_{time.time_ns()}",
            "test_titulo": title,
            "paginas": paginas_quiz,
        }
        QuizManager().guardar(datos_quiz)
        return "Quiz creado y guardado correctamente."
    except (ValueError, OSError) as error:
        return f"No se pudo crear el quiz: {error}"
