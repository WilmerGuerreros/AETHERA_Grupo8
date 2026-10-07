import datetime

def obtener_fecha_hora() -> str:
    """
    Obtiene la fecha y hora actual exacta del sistema en tiempo real. 
    úsalo cuando requieras ubicarte temporalmente.
    """
    ahora = datetime.datetime.now()
    
    fecha_formateada = ahora.strftime("%A, %d de %B de %Y, %I:%M %p")
    
    return f"La fecha y hora actual del sistema es: {fecha_formateada}"