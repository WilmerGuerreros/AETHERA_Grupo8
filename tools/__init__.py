from .tiempo import obtener_fecha_hora
from .web import buscar_en_web
from .calendario_academico import consultar_eventos_calendario

LISTA_HERRAMIENTAS: dict = {
    "obtener_fecha_hora": obtener_fecha_hora,
    "buscar_en_web": buscar_en_web,
    "consultar_eventos_calendario": consultar_eventos_calendario
} 