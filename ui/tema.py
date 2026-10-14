"""Tema visual compartido: colores, tipografías y etiquetas de la interfaz."""

import zlib

COLORS = {
    "background": "#080b18",
    "sidebar": "#0c1224",
    "surface": "#11182b",
    "surface_light": "#18223b",
    "border": "#293551",
    "text": "#f5f7ff",
    "muted": "#aab5cf",
    "accent": "#6558f5",
    "accent_light": "#8b83ff",
    "green": "#35d5a0",
    "yellow": "#f6c85f",
    "red": "#ff7885",
    "teal": "#34cbb3",
    "purple_deep": "#37256f",
}

FONT = "Segoe UI"


def humanizar_etiqueta(codigo: object) -> str:
    """Convierte un código de dominio en una etiqueta legible automática.

    La interfaz es agnóstica a los catálogos: no conoce qué categorías, tipos o
    distritos existen. Solo recibe códigos desde Data (a través de Core) y los
    presenta. Si Data agrega un valor nuevo, la interfaz lo muestra igual.
    """
    texto = str(codigo or "").replace("_", " ").strip()
    return texto.title() if texto else ""


def opciones_por_etiqueta(codigos, etiqueta_vacia=None) -> dict:
    """Arma un mapa etiqueta→código a partir de los códigos que da Core.

    ``etiqueta_vacia`` agrega una opción que no filtra (valor ``None``). Es el
    único punto donde la interfaz traduce códigos a texto y lo hace de forma
    automática, sin conocer el catálogo.
    """
    opciones: dict = {}
    if etiqueta_vacia is not None:
        opciones[etiqueta_vacia] = None
    for codigo in sorted(codigos):
        opciones[humanizar_etiqueta(codigo)] = codigo
    return opciones


WEEKDAYS = {
    "Mon-Fri": "Lunes a viernes",
    "Mon-Sat": "Lunes a sábado",
    "Mon-Sun": "Todos los días",
}
WEEKDAY_NAMES = ("LUN", "MAR", "MIÉ", "JUE", "VIE", "SÁB", "DOM")
MONTH_NAMES = (
    "enero",
    "febrero",
    "marzo",
    "abril",
    "mayo",
    "junio",
    "julio",
    "agosto",
    "septiembre",
    "octubre",
    "noviembre",
    "diciembre",
)

EVENT_PALETTE = (
    ("#593039", "#ff94a1", "#42252e"),
    ("#185347", "#71e2c5", "#123e39"),
    ("#283f69", "#9dc3ff", "#1e3151"),
    ("#56426c", "#d0a7ff", "#382a4a"),
    ("#4b476d", "#b9adff", "#302b4a"),
    ("#493b22", "#f6c85f", "#332b1c"),
)


def estilo_evento(codigo: object) -> tuple:
    """Devuelve un color estable para un evento a partir de su código.

    La interfaz no conoce las categorías: elige un color de forma determinista
    según el código que entrega Data. Si se desea un color curado por categoría,
    debe venir del contrato de datos (Data/Core), no de aquí.
    """
    if not codigo:
        return EVENT_PALETTE[0]
    indice = zlib.crc32(str(codigo).encode("utf-8")) % len(EVENT_PALETTE)
    return EVENT_PALETTE[indice]
