from .tiempo import obtener_fecha_hora
from .web import buscar_en_web
from .calendario_academico import calendario_academico

LISTA_HERRAMIENTAS: dict = {
    "obtener_fecha_hora": obtener_fecha_hora,
    "buscar_en_web": buscar_en_web,
    "calendario_academico": calendario_academico
} 