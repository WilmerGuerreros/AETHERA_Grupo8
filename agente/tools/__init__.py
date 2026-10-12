from .tiempo import obtener_fecha_hora
from .web import buscar_en_web
from .buscar_eventos import buscar_eventos
from .evaluar_carga_academica import evaluar_riesgo_sobrecarga
from .servicios_ayuda import buscar_servicios_ayuda
from .crear_evento import crear_evento


LISTA_HERRAMIENTAS: dict = {
    "obtener_fecha_hora": obtener_fecha_hora,
    "buscar_en_web": buscar_en_web,
    "buscar_eventos": buscar_eventos,
    "evaluar_riesgo_sobrecarga": evaluar_riesgo_sobrecarga,
    "buscar_servicios_ayuda": buscar_servicios_ayuda,
    "crear_evento": crear_evento,
}
