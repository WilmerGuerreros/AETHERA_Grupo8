import datetime

def obtener_fecha_hora() -> str:
    """
    Obtiene la fecha y hora actual exacta del sistema en tiempo real. 
    Útil cuando el usuario pregunta qué hora es, qué día es hoy, o necesitas ubicarte temporalmente.
    """
    ahora = datetime.datetime.now()
    
    fecha_formateada = ahora.strftime("%A, %d de %B de %Y, %I:%M %p")
    
    return f"La fecha y hora actual del sistema es: {fecha_formateada}"