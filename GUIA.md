# Guía de módulos — Aethera

## Raíz

- `main.py`: punto de entrada; delega el arranque en `aplicacion.py`.
- `aplicacion.py`: punto de composición; crea el motor, la memoria y el registro de herramientas y los inyecta en la interfaz. Es el único lugar que conoce todas las capas.
- `config.py`: configuración central (modelos de Ollama, opciones de generación y tamaño de las secciones de memoria).

## Paquete `data/`

- `data/paths.py`: rutas de recursos y datos persistentes.
- `data/chat_sessions.py`: índice y transcripciones de cada conversación independiente.
- `data/memory.py`: lectura y escritura de historiales, resúmenes e índice de memoria.
- `data/calendar.py`: lectura y escritura del calendario personal.
- `data/quizzes.py`: lectura y escritura de quizzes e intentos JSON.
- `data/documents.py`: extracción de texto de documentos PDF.
- `data/resources.py`: lectura de CSV, JSON y texto de recursos de referencia.
- `data/services.py`: catálogo de categorías y lectura/filtrado del mapa de servicios (D6); lanza excepciones explícitas si la categoría, el distrito o un servicio no existen.
- `data/resources/`: calendarios de referencia, servicios y otros datos de solo lectura.

## Paquete `core/`

- `core/conversation.py`: coordina los turnos conversacionales y ofrece el historial actual a Core al solicitar la evaluación final de un quiz.
- `core/workload.py`: agrupación semanal y cálculo del riesgo de sobrecarga.
- `core/calendar.py`: validación, filtrado, creación y eliminación de eventos.
- `core/quizzes/`: paquete con la construcción, validación y corrección de quizzes e intentos. Se divide en `schema` (esquema), `session` (intento en memoria), `scoring` (puntajes), `store` (persistencia en Data) y `evaluation` (cierre con Agent); la fachada `__init__.py` expone el contrato estable.
- `core/memory.py`: coordinación del contexto, las secciones y los resúmenes; usa Agent para resumir y Data para persistir.
- `core/chat_manager.py`: crea y restaura conversaciones con modelo y prompt compartidos, y memoria aislada por chat.
- `core/documents.py`: delega en Data la lectura de documentos adjuntos.
- `core/services.py`: delega en Data la búsqueda de servicios por categoría y distrito y reenvía su resultado o error; no conoce el catálogo ni el recurso.
- `core/web_search.py`: búsqueda de información pública en la web.

## Paquete `agent/`

- `agent/llm.py`: acceso al cliente Ollama.
- `agent/prompts.py`: prompts estáticos separados de la lógica de ejecución.
- `agent/session.py`: ciclo conversacional y llamadas a herramientas, sin dependencias de UI.
- `agent/quiz_evaluation.py`: envía las preguntas de desarrollo y el historial al LLM, valida los porcentajes asignados y genera la retroalimentación final.
- `agent/memory_summary.py`: generación de texto de resumen con el LLM; el almacenamiento permanece en Data.

### `agent/tools/` (adaptadores finos hacia `core/`)

- `agent/tools/registro.py`: metadatos de herramientas.
- `agent/tools/__init__.py`: registro único de herramientas invocables.
- `agent/tools/buscar_eventos.py`: adaptador a la consulta de calendario.
- `agent/tools/crear_evento.py`: adaptador a creación de eventos personales.
- `agent/tools/crear_quiz.py`: adaptador a construcción y almacenamiento de quices; las preguntas de alternativas incluyen una explicación de la respuesta correcta para la retroalimentación.
- `agent/tools/evaluar_carga_academica.py`: adaptador a `core/workload`.
- `agent/tools/servicios_ayuda.py`: adaptador a `core/services`.
- `agent/tools/web.py`: adaptador a `core/web_search`.

## Paquete `ui/`

- `ui/desktop_app.py`: orquesta la ventana de escritorio y sus secciones.
- `ui/tk_env.py`: configuración de las bibliotecas Tcl/Tk para la ventana de escritorio.
- `ui/dashboard.py`: sección de inicio y resumen académico.
- `ui/carga_academica.py`: sección de análisis de carga académica.
- `ui/servicios.py`: sección de servicios de apoyo.
- `ui/tema.py`: colores, tipografías y etiquetas compartidas (`COLORS`, `FONT`, `EVENT_STYLES`, `SERVICE_*`, `WEEKDAYS`, `MONTH_NAMES`).
- `ui/widgets.py`: widgets reutilizables (`RoundedFrame`, `RoundedButton`, `AnimatedDropdown`) y sus ayudas de dibujo.
- `ui/utilidades.py`: análisis de Markdown para presentar mensajes del chat.
- `ui/calendario/`: orquestación (`calendar_view.py`) y componentes (`components/`: encabezado, cuadrícula y diálogos); las reglas están en `core/calendar.py`.
- `ui/chat/`: coordinación de la vista (`chat_view.py`), lógica (`logica.py`) y componentes (`components/`: encabezado, historial, entrada y quiz).
- `ui/quiz/`: presentación de quizzes e intentos; las selecciones y evaluaciones se delegan a Core mediante eventos.

## Datos persistentes

Todos los datos escribibles viven bajo la raíz única que devuelve `data.paths.application_data_directory()`:

- `CHATS DE AETHERA AI/chat_<id>/` — transcripción `CONVERSACION.json` y carpeta `MEMORIA/` con `HISTORIAL/`, `RESUMEN/`, `INDICE/` y `ARCHIVOS ADJUNTOS/`; cada chat mantiene su propia memoria.
- `CHATS DE AETHERA AI/CHATS.json` — lista de chats y títulos.
- `data/calendario.ics` — calendario personal editable.
- `data/quices/` — quices generados en JSON (UTF-8). El campo `avance` guarda el índice y las respuestas como una lista de objetos con `pregunta_id` y `respuesta`; al finalizar, `resultado_final` guarda `porcentaje_total` y `retroalimentacion` (un elemento por pregunta con `pregunta_id`, `tipo`, `correcta`, `porcentaje` y `retroalimentacion`).

En desarrollo la raíz es `data/` dentro del proyecto; en el ejecutable empaquetado es la carpeta de datos del sistema operativo.

## Crear y compartir el ejecutable en Windows

1. Instala Python 3.10 o posterior y Ollama en el equipo de desarrollo.
2. Desde PowerShell, en la carpeta del proyecto, ejecuta: `powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\build_windows.ps1`.
3. El ejecutable se crea en `dist\Aethera.exe`; comparte ese archivo junto con esta guía.

El ejecutable incluye los recursos de calendario y servicios y guarda la memoria del usuario en su carpeta local de datos. Para conversar necesita Ollama instalado y ejecutándose, conexión a Internet y acceso al modelo configurado en `config.py`; el modelo no se incluye en el ejecutable. El paquete de Windows debe construirse en Windows.

Si la aplicación muestra «No module named 'tkinter'», cierra todas las ventanas de Aethera y vuelve a generar el ejecutable con el script anterior; no compartas una compilación anterior. El script configura Tcl/Tk desde la instalación de Python usada para compilar.
