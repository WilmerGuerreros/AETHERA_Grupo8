"""Reglas de contexto y seccionado de la memoria conversacional."""

import logging
from collections.abc import Callable

from data.memory import MemoryStore
from settings import MAX_MENSAJES_POR_SECCION, MODELO_RESUMEN

log = logging.getLogger(__name__)


class MemoryContext:
    """Mantiene el avance de secciones y compone contexto desde Data."""

    def __init__(
        self,
        store: MemoryStore | None = None,
        modelo: str = MODELO_RESUMEN,
        max_mensajes_por_seccion: int = MAX_MENSAJES_POR_SECCION,
        resumir: Callable[[str, str], str] | None = None,
    ) -> None:
        if (
            not isinstance(max_mensajes_por_seccion, int)
            or isinstance(max_mensajes_por_seccion, bool)
            or max_mensajes_por_seccion < 1
        ):
            raise ValueError("El límite de mensajes debe ser un entero positivo.")
        self.store = store or MemoryStore()
        self.modelo = modelo
        self.max_mensajes_por_seccion = max_mensajes_por_seccion
        self._resumir = resumir
        ultima_seccion, contador = self.store.ultima_seccion()
        if ultima_seccion == 0:
            self.numero_seccion, self.contador_mensajes = 1, 0
        elif contador >= self.max_mensajes_por_seccion:
            self.numero_seccion, self.contador_mensajes = ultima_seccion + 1, 0
        else:
            self.numero_seccion, self.contador_mensajes = ultima_seccion, contador

    def contexto_inicial(self) -> list[dict[str, str]]:
        """Compone el contexto inicial con resumen y conversaciones recientes."""
        mensajes: list[dict[str, str]] = [{"": ""}]
        resumen_anterior = self.store.leer_resumen(self.numero_seccion - 1)
        if resumen_anterior:
            mensajes.append({
                "role": "system",
                "content": f"Memoria de largo plazo recuperada:\n{resumen_anterior}",
            })

        interacciones = self.store.leer_interacciones_recientes(
            self.numero_seccion,
            cantidad=4,
        )
        if interacciones:
            contenido = "MEMORIA RECIENTE RECUPERADA:\n\n"
            for interaccion in interacciones:
                contenido += (
                    f"Usuario: {interaccion['usuario']}\n"
                    f"Aethera: {interaccion['aethera']}\n\n"
                )
            mensajes.append({"role": "system", "content": contenido})
        return mensajes

    def guardar(
        self,
        usuario: str,
        respuesta: str,
        modelo: str | None = None,
    ) -> None:
        """Persiste un turno y resume la sección al alcanzar el límite."""
        self.store.escribir(self.numero_seccion, usuario, respuesta)
        self.contador_mensajes += 1
        log.info(
            "[Memoria] HISTORIAL_%04d -> %d/%d",
            self.numero_seccion,
            self.contador_mensajes,
            self.max_mensajes_por_seccion,
        )
        if self.contador_mensajes >= self.max_mensajes_por_seccion:
            self._cerrar_seccion(modelo or self.modelo)

    def _cerrar_seccion(self, modelo: str) -> None:
        if self._resumir is None:
            raise RuntimeError("No se configuró el generador de resúmenes.")
        contenido_historial = self.store.leer_historial(self.numero_seccion)
        resumen = self._resumir(contenido_historial, modelo)
        self.store.guardar_resumen(self.numero_seccion, resumen)

        indice = self.store.leer_indice()
        if not any(
            seccion["id"] == self.numero_seccion
            for seccion in indice["secciones"]
        ):
            indice["secciones"].append({
                "id": self.numero_seccion,
                "historial": self.store.nombre_historial(self.numero_seccion),
                "resumen": self.store.nombre_resumen(self.numero_seccion),
                "estado": "sellado",
            })
            self.store.guardar_indice(indice)

        self.numero_seccion += 1
        self.contador_mensajes = 0
