"""Punto de composición de Aethera.

Es el único lugar que conoce todas las capas: crea el motor de lenguaje, la
memoria y el registro de herramientas, y los inyecta en la interfaz de
escritorio. Aquí es donde se agregarán dependencias nuevas (por ejemplo, un
proveedor de embeddings) sin tocar las capas internas.
"""

from agente.LLMEngine import LLMEngine
from agente.prompts import SYSTEM_PROMPT
from agente.tools import REGISTRO_HERRAMIENTAS
from app_paths import migrar_datos_heredados
from config import MODELO, OPCIONES_LLM
from config_de_carpetas import rutas_memoria
from memoria.servicio import Memoria


def iniciar_aplicacion() -> None:
    """Ensambla las dependencias y abre la interfaz de escritorio."""
    migrar_datos_heredados()

    motor = LLMEngine(MODELO, dict(OPCIONES_LLM))
    memoria = Memoria(rutas_memoria(), modelo=motor.modelo)

    historial = memoria.contexto_inicial()
    historial[0] = {"role": "system", "content": SYSTEM_PROMPT}

    from ui.desktop_app import iniciar_app_escritorio

    iniciar_app_escritorio(
        motor,
        historial,
        REGISTRO_HERRAMIENTAS,
        memoria.guardar,
    )
