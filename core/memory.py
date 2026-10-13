"""Coordinación de contexto, secciones y resúmenes de memoria."""

import logging
from collections.abc import Callable
from pathlib import Path

from config import MAX_MENSAJES_POR_SECCION, MODELO_RESUMEN
from data.memory import (
    escribir_interaccion,
    guardar_indice_memoria,
    guardar_resumen_memoria,
    leer_archivo_memoria,
    leer_indice_memoria,
    leer_interacciones_recientes,
    leer_resumen_memoria,
    obtener_ultimo_archivo_historial,
)
from data.paths import MemoryPaths, memory_paths

log = logging.getLogger(__name__)


class Memoria:
    """Mantiene el estado de memoria y coordina Agent con Data."""

    def __init__(
        self,
        rutas: MemoryPaths | None = None,
        modelo: str = MODELO_RESUMEN,
        max_mensajes_por_seccion: int = MAX_MENSAJES_POR_SECCION,
        resumir: Callable[[str, str], str] | None = None,
    ):
        self.rutas = (rutas or memory_paths()).ensure()
        self.modelo = modelo
        self.max_mensajes_por_seccion = max_mensajes_por_seccion
        self._resumir = resumir
        archivo, contador = obtener_ultimo_archivo_historial(self.rutas.historial)
        if archivo is None:
            self.numero_seccion, self.contador_mensajes = 1, 0
        else:
            numero_seccion = int(archivo.stem.split("_")[1])
            if contador >= self.max_mensajes_por_seccion:
                self.numero_seccion, self.contador_mensajes = numero_seccion + 1, 0
            else:
                self.numero_seccion, self.contador_mensajes = numero_seccion, contador

    def contexto_inicial(self) -> list[dict[str, str]]:
        """Compone el contexto inicial con resumen y conversaciones recientes."""
        mensajes: list[dict[str, str]] = [{"": ""}]
        resumen_anterior = leer_resumen_memoria(
            self.rutas.resumen,
            self.numero_seccion - 1,
        )
        if resumen_anterior:
            mensajes.append({
                "role": "system",
                "content": f"Memoria de largo plazo recuperada:\n{resumen_anterior}",
            })

        interacciones = leer_interacciones_recientes(
            self.rutas.historial,
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
        archivo = escribir_interaccion(
            self.rutas.historial,
            self.numero_seccion,
            usuario,
            respuesta,
        )
        self.contador_mensajes += 1
        log.info(
            "[Memoria] HISTORIAL_%04d -> %d/%d",
            self.numero_seccion,
            self.contador_mensajes,
            self.max_mensajes_por_seccion,
        )
        if self.contador_mensajes >= self.max_mensajes_por_seccion:
            self._cerrar_seccion(archivo, modelo or self.modelo)

    def _cerrar_seccion(self, archivo: Path, modelo: str) -> None:
        contenido_historial = leer_archivo_memoria(archivo)
        if self._resumir is None:
            from agent.memory_summary import generar_resumen

            resumen = generar_resumen(contenido_historial, modelo)
        else:
            resumen = self._resumir(contenido_historial, modelo)
        archivo_resumen = guardar_resumen_memoria(
            self.rutas.resumen,
            self.numero_seccion,
            resumen,
        )

        indice = leer_indice_memoria(self.rutas.indice)
        if not any(
            seccion["id"] == self.numero_seccion
            for seccion in indice["secciones"]
        ):
            indice["secciones"].append({
                "id": self.numero_seccion,
                "historial": archivo.name,
                "resumen": archivo_resumen.name,
                "estado": "sellado",
            })
            guardar_indice_memoria(self.rutas.indice, indice)

        self.numero_seccion += 1
        self.contador_mensajes = 0
