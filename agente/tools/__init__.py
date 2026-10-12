from .tiempo import obtener_fecha_hora
from .web import buscar_en_web
from .calendario_academico import calendario_academico
from .evaluar_carga_academica import evaluar_riesgo_sobrecarga
from .servicios_ayuda import buscar_servicios_ayuda


LISTA_HERRAMIENTAS: dict = {
    "obtener_fecha_hora": obtener_fecha_hora,
    "buscar_en_web": buscar_en_web,
    "calendario_academico": calendario_academico,
    "evaluar_riesgo_sobrecarga": evaluar_riesgo_sobrecarga,
    "buscar_servicios_ayuda": buscar_servicios_ayuda
}
