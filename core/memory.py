"""Fachada de memoria que inyecta el resumen producido por Agent."""

from collections.abc import Callable

from data.memory import MemoryStore
from data.memory_context import MemoryContext
from data.settings import MAX_MENSAJES_POR_SECCION, MODELO_RESUMEN


def _resumir_con_agente(contenido: str, modelo: str) -> str:
    from agent.memory_summary import generar_resumen

    return generar_resumen(contenido, modelo)


class Memoria(MemoryContext):
    """Conecta las reglas de memoria de Data con el generador de Agent."""

    def __init__(
        self,
        store: MemoryStore | None = None,
        modelo: str = MODELO_RESUMEN,
        max_mensajes_por_seccion: int = MAX_MENSAJES_POR_SECCION,
        resumir: Callable[[str, str], str] | None = None,
    ) -> None:
        super().__init__(
            store=store,
            modelo=modelo,
            max_mensajes_por_seccion=max_mensajes_por_seccion,
            resumir=resumir or _resumir_con_agente,
        )


__all__ = ["Memoria"]
