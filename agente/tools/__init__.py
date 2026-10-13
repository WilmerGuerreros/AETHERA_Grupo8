"""Registro de las herramientas que puede invocar el agente."""

from .buscar_eventos import buscar_eventos
from .crear_evento import crear_evento
from .crear_test import crear_test
from .evaluar_carga_academica import evaluar_riesgo_sobrecarga
from .registro import Herramienta
from .servicios_ayuda import buscar_servicios_ayuda
from .web import buscar_en_web


REGISTRO_HERRAMIENTAS: dict[str, Herramienta] = {
    "buscar_en_web": Herramienta(
        nombre="buscar_en_web",
        funcion=buscar_en_web,
        categoria="informacion",
        palabras_clave=("web", "internet", "noticias", "actualidad", "buscar", "público"),
    ),
    "buscar_eventos": Herramienta(
        nombre="buscar_eventos",
        funcion=buscar_eventos,
        categoria="calendario",
        palabras_clave=("evento", "examen", "clase", "calendario", "fecha", "horario"),
    ),
    "evaluar_riesgo_sobrecarga": Herramienta(
        nombre="evaluar_riesgo_sobrecarga",
        funcion=evaluar_riesgo_sobrecarga,
        categoria="bienestar",
        palabras_clave=(
            "estrés",
            "sobrecarga",
            "carga académica",
            "semanas",
            "evaluaciones",
        ),
    ),
    "buscar_servicios_ayuda": Herramienta(
        nombre="buscar_servicios_ayuda",
        funcion=buscar_servicios_ayuda,
        categoria="bienestar",
        palabras_clave=(
            "apoyo",
            "servicios",
            "bienestar",
            "orientación",
            "distrito",
            "derivación",
        ),
    ),
    "crear_evento": Herramienta(
        nombre="crear_evento",
        funcion=crear_evento,
        categoria="calendario",
        palabras_clave=("crear", "agendar", "recordatorio", "evento", "calendario"),
    ),
    "crear_test": Herramienta(
        nombre="crear_test",
        funcion=crear_test,
        categoria="quices",
        palabras_clave=("quiz", "test", "práctica", "preguntas", "evaluación"),
    ),
}
