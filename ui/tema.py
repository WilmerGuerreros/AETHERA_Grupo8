"""Tema visual compartido: colores, tipografías y etiquetas de la interfaz."""

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
SERVICE_CATEGORIES = {
    "Presión académica": "academic_pressure",
    "Apoyo social": "social_support",
    "Orientación vocacional": "career_concern",
    "Sueño y rutinas": "sleep_and_routine",
    "Orientación sobre servicios": "service_navigation",
}
SERVICE_TYPES = {
    "counseling": "Orientación",
    "peer_support": "Acompañamiento entre pares",
    "career_guidance": "Orientación vocacional",
}
SERVICE_DISTRICTS = {
    "Todos los distritos": None,
    "Distrito Gaia": "DIST_GAIA",
    "Distrito Horizon": "DIST_HORIZON",
    "Distrito Nebula": "DIST_NEBULA",
    "Distrito Quantum": "DIST_QUANTUM",
    "Distrito Vector": "DIST_VECTOR",
}
SERVICE_CHANNELS = {
    "in_person": "Presencial",
    "digital": "En línea",
    "phone": "Teléfono",
}

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

EVENT_STYLES = {
    "evaluation_week": ("#593039", "#ff94a1", "#42252e"),
    "wellbeing_activity": ("#185347", "#71e2c5", "#123e39"),
    "period_start": ("#283f69", "#9dc3ff", "#1e3151"),
    "period_end": ("#56426c", "#d0a7ff", "#382a4a"),
    "university_activity": ("#4b476d", "#b9adff", "#302b4a"),
    "personal": ("#493b22", "#f6c85f", "#332b1c"),
}
