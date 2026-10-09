from .tiempo import obtener_fecha_hora
from .web import buscar_en_web
from .calendario_academico import calendario_academico
from .evaluar_carga_academica import evaluar_riesgo_sobrecarga
from .servicios_ayuda import buscar_servicios_ayuda
from .buscar_en_sílabo import buscar_en_silabo
from .consultar_tareas import consultar_tareas
from .planificador import evaluar_conflictos_academicos

LISTA_HERRAMIENTAS: dict = {
    "obtener_fecha_hora": obtener_fecha_hora,
    "buscar_en_web": buscar_en_web,
    "calendario_academico": calendario_academico,
    "evaluar_riesgo_sobrecarga": evaluar_riesgo_sobrecarga,
    "buscar_servicios_ayuda": buscar_servicios_ayuda,
    "buscar_en_silabo": buscar_en_silabo,
    "consultar_tareas": consultar_tareas,
    "evaluar_conflictos_academicos": evaluar_conflictos_academicos
}
