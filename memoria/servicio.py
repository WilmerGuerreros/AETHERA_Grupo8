"""Servicio de memoria con estado explícito (historial, resumen e índice)."""

import logging
from typing import Callable, Optional

from config import MAX_MENSAJES_POR_SECCION, MODELO_RESUMEN
from config_de_carpetas import RutasMemoria, rutas_memoria

from .historial import (
    escribir_interaccion,
    inicializar_memoria,
    obtener_ultimas_interacciones,
)
from .indice import actualizar_indice
from .resumen import generar_resumen, obtener_ultimo_resumen

log = logging.getLogger(__name__)


class Memoria:
    """Coordina la memoria persistente del usuario sin estado global."""

    def __init__(
        self,
        rutas: Optional[RutasMemoria] = None,
        modelo: str = MODELO_RESUMEN,
        max_mensajes_por_seccion: int = MAX_MENSAJES_POR_SECCION,
        resumir: Optional[Callable] = None,
    ):
        self.rutas = (rutas or rutas_memoria()).ensure()
        self.modelo = modelo
        self.max_mensajes_por_seccion = max_mensajes_por_seccion
        self._resumir = resumir
        self.numero_seccion, self.contador_mensajes = inicializar_memoria(
            self.rutas.historial,
            self.max_mensajes_por_seccion,
        )

    def contexto_inicial(self) -> list[dict]:
        """Devuelve los mensajes iniciales del agente con la memoria recuperada."""
        mensajes: list[dict] = [{"": ""}]

        resumen_anterior = obtener_ultimo_resumen(
            self.numero_seccion, self.rutas.resumen
        )
        if resumen_anterior:
            mensajes.append({
                "role": "system",
                "content": f"Memoria de largo plazo recuperada:\n{resumen_anterior}",
            })

        ultimas_interacciones = obtener_ultimas_interacciones(
            self.rutas.historial, self.numero_seccion, cantidad=4
        )
        if ultimas_interacciones:
            contexto_reciente = "MEMORIA RECIENTE RECUPERADA:\n\n"
            for interaccion in ultimas_interacciones:
                contexto_reciente += (
                    f"Usuario: {interaccion['usuario']}\n"
                    f"Aethera: {interaccion['aethera']}\n\n"
                )
            mensajes.append({"role": "system", "content": contexto_reciente})

        return mensajes

    def guardar(self, usuario, respuesta, modelo: Optional[str] = None) -> None:
        """Persiste una interacción y cierra la sección cuando se llena."""
        archivo = escribir_interaccion(
            self.rutas.historial, self.numero_seccion, usuario, respuesta
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

    def _cerrar_seccion(self, archivo, modelo: str) -> None:
        if self._resumir is not None:
            archivo_resumen = self._resumir(archivo, self.numero_seccion, modelo)
        else:
            archivo_resumen = generar_resumen(
                archivo, self.numero_seccion, self.rutas.resumen, modelo
            )
        actualizar_indice(
            self.numero_seccion, archivo, archivo_resumen, self.rutas.indice
        )
        self.numero_seccion += 1
        self.contador_mensajes = 0
