"""
Busca y filtra los servicios de apoyo estudiantil
según la problemática del alumno y su estado emocional.

Args:
    topico (str): Elige estrictamente el área del problema: 
        'academic_pressure' (estrés por notas/entregas), 
        'career_concern' (dudas sobre el futuro/carrera), 
        'work_study_balance' (falta de tiempo trabajo-estudio), 
        'social_support' (soledad, problemas familiares o de integración).
    sentimiento (str): Elige el estado emocional predominante del estudiante:
        'strained' (muy estresado/agobiado), 
        'mixed' (ansioso pero comunicativo), 
        'hopeful' (motivado a mejorar pero necesita guía).

Returns:
    list[dict]: Lista de servicios recomendados con sus canales de atención y horarios.
"""