"""Herramienta del agente para crear eventos en el calendario personal."""

from dominio.calendario import crear_evento as _crear_evento


def crear_evento(
    titulo: str,
    fecha_inicio: str,
    fecha_fin: str = "",
    descripcion: str = "",
    hora_inicio: str = "",
    hora_fin: str = "",
) -> dict:
    """Crea un evento en el calendario personal del usuario.

    Args:
        titulo: Nombre breve del evento.
        fecha_inicio: Primer día del evento en formato YYYY-MM-DD.
        fecha_fin: Último día inclusivo en formato YYYY-MM-DD; si se omite,
            el evento dura un día.
        descripcion: Detalles opcionales del evento.
        hora_inicio: Hora local de inicio en formato HH:MM. Si se omite, el
            evento dura el día completo.
        hora_fin: Hora local de fin en formato HH:MM; debe acompañar a
            hora_inicio.

    Returns:
        Confirmación con los datos guardados o un diccionario con 'error'.
    """
    return _crear_evento(
        titulo,
        fecha_inicio,
        fecha_fin,
        descripcion,
        hora_inicio,
        hora_fin,
    )
