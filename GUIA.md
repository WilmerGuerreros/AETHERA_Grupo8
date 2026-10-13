# Guía de módulos — Aethera

## Raíz

- `main.py`: punto de entrada; delega el arranque en `aplicacion.py`.
- `aplicacion.py`: punto de composición; crea el motor, la memoria y el registro de herramientas y los inyecta en la interfaz. Es el único lugar que conoce todas las capas.
- `config.py`: configuración central (modelos de Ollama, opciones de generación y tamaño de las secciones de memoria).
- `app_paths.py`: resuelve los recursos empaquetados y la **raíz única de datos** del usuario (`datos/` en desarrollo, carpeta del SO al empaquetar); además migra los datos de versiones anteriores.
- `config_de_carpetas.py`: calcula las rutas de memoria (`RutasMemoria`) sin tocar el disco.

## Paquete `agente/`

- `agente/LLMEngine.py`: conecta con Ollama y genera respuestas en streaming.
- `agente/prompts.py`: prompt de sistema del agente.
- `agente/agent_session.py`: coordina los turnos y ejecuta las herramientas solicitadas por el modelo.

### `agente/tools/` (adaptadores finos hacia `dominio/`)

- `agente/tools/registro.py`: clase `Herramienta` con los metadatos de cada herramienta (categoría y palabras clave; la descripción se toma del docstring).
- `agente/tools/__init__.py`: declara `REGISTRO_HERRAMIENTAS`, la lista única de herramientas que usa el agente.
- `agente/tools/buscar_eventos.py`: consulta y filtra eventos de los calendarios.
- `agente/tools/crear_evento.py`: crea eventos en el calendario personal.
- `agente/tools/crear_test.py`: valida y guarda quices educativos.
- `agente/tools/evaluar_carga_academica.py`: adaptador de `dominio/carga_academica`.
- `agente/tools/servicios_ayuda.py`: adaptador de `dominio/servicios_ayuda`.
- `agente/tools/web.py`: adaptador de `dominio/web`.

## Paquete `dominio/` (lógica de negocio, sin Tkinter ni Ollama)

- `dominio/calendario/`: lectura y edición de los calendarios académico y personal (`lectura.py` y `escritura.py`).
- `dominio/carga_academica.py`: agrupa evaluaciones por semana e identifica posibles períodos de sobrecarga.
- `dominio/servicios_ayuda.py`: busca servicios de apoyo por categoría y, opcionalmente, por distrito.
- `dominio/web.py`: busca información pública actual en la web.
- `dominio/quices/quiz_manager.py`: validación, persistencia, listado y sesiones de respuesta de los quices.
- `dominio/quices/creacion.py`: construye los datos de un quiz a partir del formato compacto del agente.

## Paquete `memoria/`

- `memoria/historial.py`: guarda conversaciones y agrupa lectura, conteo, inicialización y consulta de historiales a partir de una carpeta explícita.
- `memoria/indice.py`: carga y actualiza el índice de secciones de historial y resúmenes.
- `memoria/resumen.py`: genera y recupera resúmenes de memoria.
- `memoria/servicio.py`: clase `Memoria` con estado explícito; arma el contexto inicial y persiste cada interacción sin variables globales.

## Paquete `ui/`

- `ui/desktop_app.py`: orquesta la ventana de escritorio y sus secciones.
- `ui/dashboard.py`: sección de inicio y resumen académico.
- `ui/carga_academica.py`: sección de análisis de carga académica.
- `ui/servicios.py`: sección de servicios de apoyo.
- `ui/tema.py`: colores, tipografías y etiquetas compartidas (`COLORS`, `FONT`, `EVENT_STYLES`, `SERVICE_*`, `WEEKDAYS`, `MONTH_NAMES`).
- `ui/widgets.py`: widgets reutilizables (`RoundedFrame`, `RoundedButton`, `AnimatedDropdown`) y sus ayudas de dibujo.
- `ui/utilidades.py`: extracción de texto de PDF y análisis de Markdown del chat.
- `ui/calendario/`: lógica (`logica.py`), orquestación (`calendar_view.py`) y componentes (`components/`: encabezado, cuadrícula y diálogos).
- `ui/chat/`: coordinación de la vista (`chat_view.py`), lógica (`logica.py`) y componentes (`components/`: encabezado, historial, entrada y quiz).
- `ui/quiz/`: tarjetas, intentos y evaluación; las alternativas se corrigen localmente y el modelo asigna un porcentaje a las respuestas de desarrollo.

## Datos persistentes

Todos los datos escribibles viven bajo la raíz única que devuelve `app_paths.application_data_directory()`:

- `datos/memoria/` — historial, resúmenes, índice y archivos adjuntos del chat.
- `datos/calendario.ics` — calendario personal editable.
- `datos/quices/` — quices generados en JSON (UTF-8).

En desarrollo la raíz es `datos/` dentro del proyecto; en el ejecutable empaquetado es la carpeta de datos del sistema operativo. `app_paths.migrar_datos_heredados()` mueve automáticamente los datos de versiones anteriores.

## Crear y compartir el ejecutable en Windows

1. Instala Python 3.10 o posterior y Ollama en el equipo de desarrollo.
2. Desde PowerShell, en la carpeta del proyecto, ejecuta: `powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\build_windows.ps1`.
3. El ejecutable se crea en `dist\Aethera.exe`; comparte ese archivo junto con esta guía.

El ejecutable incluye los recursos de calendario y servicios y guarda la memoria del usuario en su carpeta local de datos. Para conversar necesita Ollama instalado y ejecutándose, conexión a Internet y acceso al modelo configurado en `config.py`; el modelo no se incluye en el ejecutable. El paquete de Windows debe construirse en Windows.

Si la aplicación muestra «No module named 'tkinter'», cierra todas las ventanas de Aethera y vuelve a generar el ejecutable con el script anterior; no compartas una compilación anterior. El script configura Tcl/Tk desde la instalación de Python usada para compilar.
