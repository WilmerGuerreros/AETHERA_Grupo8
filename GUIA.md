# Guía de módulos — Aethera

## Raíz

- `main.py`: punto de entrada; delega el arranque en `aplicacion.py`.
- `aplicacion.py`: punto de composición; crea el motor, la memoria y el registro de herramientas y los inyecta en la interfaz. Es el único lugar que conoce todas las capas.
- `config.py`: configuración central (modelos de Ollama, opciones de generación y tamaño de las secciones de memoria).
- `app_paths.py`: conserva la configuración de Tcl/Tk; las rutas y la migración de datos están en `data/paths.py`.

## Paquete `data/`

- `data/paths.py`: rutas de recursos y datos persistentes, además de la migración de datos anteriores.
- `data/memory.py`: lectura y escritura de historiales, resúmenes e índice de memoria.
- `data/calendar.py`: lectura y escritura del calendario personal.
- `data/quizzes.py`: lectura y escritura de quizzes e intentos JSON.
- `data/documents.py`: extracción de texto de documentos PDF.
- `data/resources.py`: lectura de CSV, JSON y texto de recursos de referencia.
- `data/resources/`: calendarios de referencia, servicios y otros datos de solo lectura.

## Paquete `core/`

- `core/workload.py`: agrupación semanal y cálculo del riesgo de sobrecarga.
- `core/calendar.py`: validación, filtrado, creación y eliminación de eventos.
- `core/quizzes.py`: construcción, validación y corrección de quizzes e intentos; usa Data para persistirlos.
- `core/memory.py`: coordinación del contexto, las secciones y los resúmenes; usa Agent para resumir y Data para persistir.
- `core/documents.py`: delega en Data la lectura de documentos adjuntos.
- `core/services.py`: selección de servicios por categoría y distrito.
- `core/web_search.py`: búsqueda de información pública en la web.

## Paquete `agent/`

- `agent/llm.py`: acceso al cliente Ollama.
- `agent/prompts.py`: prompts estáticos separados de la lógica de ejecución.
- `agent/session.py`: ciclo conversacional y llamadas a herramientas, sin dependencias de UI.
- `agent/quiz_evaluation.py`: petición al LLM y validación de evaluaciones de respuestas abiertas.
- `agent/memory_summary.py`: generación de texto de resumen con el LLM; el almacenamiento permanece en Data.

### `agent/tools/` (adaptadores finos hacia `core/`)

- `agent/tools/registro.py`: metadatos de herramientas.
- `agent/tools/__init__.py`: registro único de herramientas invocables.
- `agent/tools/buscar_eventos.py`: adaptador a la consulta de calendario.
- `agent/tools/crear_evento.py`: adaptador a creación de eventos personales.
- `agent/tools/crear_quiz.py`: adaptador a construcción y almacenamiento de quices.
- `agent/tools/evaluar_carga_academica.py`: adaptador a `core/workload`.
- `agent/tools/servicios_ayuda.py`: adaptador a `core/services`.
- `agent/tools/web.py`: adaptador a `core/web_search`.

## Paquete `ui/`

- `ui/desktop_app.py`: orquesta la ventana de escritorio y sus secciones.
- `ui/dashboard.py`: sección de inicio y resumen académico.
- `ui/carga_academica.py`: sección de análisis de carga académica.
- `ui/servicios.py`: sección de servicios de apoyo.
- `ui/tema.py`: colores, tipografías y etiquetas compartidas (`COLORS`, `FONT`, `EVENT_STYLES`, `SERVICE_*`, `WEEKDAYS`, `MONTH_NAMES`).
- `ui/widgets.py`: widgets reutilizables (`RoundedFrame`, `RoundedButton`, `AnimatedDropdown`) y sus ayudas de dibujo.
- `ui/utilidades.py`: análisis de Markdown para presentar mensajes del chat.
- `ui/calendario/`: orquestación (`calendar_view.py`) y componentes (`components/`: encabezado, cuadrícula y diálogos); las reglas están en `core/calendar.py`.
- `ui/chat/`: coordinación de la vista (`chat_view.py`), lógica (`logica.py`) y componentes (`components/`: encabezado, historial, entrada y quiz).
- `ui/quiz/`: presentación de quizzes e intentos; las reglas y la evaluación se delegan a Core.

## Datos persistentes

Todos los datos escribibles viven bajo la raíz única que devuelve `app_paths.application_data_directory()`:

- `data/memoria/` — historial, resúmenes, índice y archivos adjuntos del chat.
- `data/calendario.ics` — calendario personal editable.
- `data/quices/` — quices generados en JSON (UTF-8).

En desarrollo la raíz es `data/` dentro del proyecto; en el ejecutable empaquetado es la carpeta de datos del sistema operativo. `data.paths.migrar_datos_heredados()` mueve automáticamente los datos de versiones anteriores.

## Crear y compartir el ejecutable en Windows

1. Instala Python 3.10 o posterior y Ollama en el equipo de desarrollo.
2. Desde PowerShell, en la carpeta del proyecto, ejecuta: `powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\build_windows.ps1`.
3. El ejecutable se crea en `dist\Aethera.exe`; comparte ese archivo junto con esta guía.

El ejecutable incluye los recursos de calendario y servicios y guarda la memoria del usuario en su carpeta local de datos. Para conversar necesita Ollama instalado y ejecutándose, conexión a Internet y acceso al modelo configurado en `config.py`; el modelo no se incluye en el ejecutable. El paquete de Windows debe construirse en Windows.

Si la aplicación muestra «No module named 'tkinter'», cierra todas las ventanas de Aethera y vuelve a generar el ejecutable con el script anterior; no compartas una compilación anterior. El script configura Tcl/Tk desde la instalación de Python usada para compilar.
