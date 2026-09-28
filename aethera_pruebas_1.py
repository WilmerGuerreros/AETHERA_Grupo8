import ollama
import pandas as pd


# =========================
# CARGAR ARCHIVOS
# =========================

d3 = pd.read_csv("D3_academic_trajectory.csv")
d7 = pd.read_csv("D7_calendar.csv")


# =========================
# TOOLS
# =========================

def consultar_carga_academica(student_id: str) -> str:

    datos = d3[d3["student_id"] == student_id]

    if datos.empty:
        return "No se encontró ese estudiante."

    resultado = []

    for _, fila in datos.iterrows():

        resultado.append(
            f"Periodo: {fila['period_id']}\n"
            f"Carga de créditos: {fila['credit_load']}\n"
            f"Evaluaciones: {fila['evaluation_count']}\n"
            f"Promedio: {fila['average_grade']}\n"
            f"Cambio de nota: {fila['grade_change']}\n"
            f"Asistencia: {fila['attendance_rate']}\n"
            f"Alerta académica: {fila['dropout_alert']}\n"
        )

    return "\n".join(resultado)


def consultar_calendario(period_id: str) -> str:

    datos = d7[d7["period_id"] == period_id]

    if datos.empty:
        return "No se encontraron eventos para ese período."

    resultado = []

    for _, fila in datos.iterrows():

        resultado.append(
            f"Evento: {fila['event_type']}\n"
            f"Título: {fila['title']}\n"
            f"Inicio: {fila['start_date']}\n"
            f"Fin: {fila['end_date']}\n"
            f"Intensidad: {fila['evaluation_intensity']}\n"
        )

    return "\n".join(resultado)


# =========================
# DICCIONARIO DE TOOLS
# =========================

herramientas = {
    "consultar_carga_academica": consultar_carga_academica,
    "consultar_calendario": consultar_calendario
}

tools = herramientas.values()


# =========================
# CONVERSACIÓN
# =========================

mensajes = [

    {
        "role": "system",
        "content": """
        Eres Aethera, un agente de acompañamiento académico.

        Ayudas al estudiante a comprender y organizar
        su situación académica.

        Puedes utilizar las herramientas disponibles
        para consultar información académica y calendario.

        No inventes información.
        """
    },

    {
        "role": "user",
        "content": "¿Cuál es la carga académica del estudiante STU_AE_000008?"
    }
]


# =========================
# PRIMERA LLAMADA
# =========================

print("Consultando a Nemotron...")

rpta = ollama.chat(
    model="nemotron-3-super:cloud",
    messages=mensajes,
    tools=list(tools)
)


# =========================
# TOOL CALL
# =========================

if rpta.message.tool_calls:

    mensajes.append(rpta.message)

    for call in rpta.message.tool_calls:

        print("\nLa IA pidió:")
        print(call.function.name)

        funcion = herramientas[call.function.name]

        argumentos = call.function.arguments

        resultado = funcion(**argumentos)

        print("\nResultado de Python:")
        print(resultado)

        mensajes.append({
            "role": "tool",
            "tool_name": call.function.name,
            "content": resultado
        })


    # =========================
    # RESPUESTA FINAL
    # =========================

    rptaf = ollama.chat(
        model="nemotron-3-super:cloud",
        messages=mensajes,
        tools=list(tools)
    )

    print("\n======================")
    print("RESPUESTA DE AETHERA")
    print("======================")

    print(rptaf.message.content)


else:

    print("\nLa IA no pidió ninguna herramienta.")