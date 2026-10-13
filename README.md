# Aethera

Agente de acompañamiento académico que ayuda a estudiantes a organizar su carga de
estudio y a reducir el estrés de las evaluaciones. Combina un agente conversacional
(Ollama) con una interfaz de escritorio (Tkinter), un calendario académico/personal,
análisis de carga académica, búsqueda de servicios de apoyo y generación de quices.

## Requisitos

- Python 3.10 o posterior.
- [Ollama](https://ollama.com/) instalado y en ejecución, con acceso al modelo configurado.
- Conexión a Internet para la búsqueda web.

Instala las dependencias:

```bash
python -m venv .venv
.venv/bin/pip install -r requirements.txt
```

## Ejecutar

```bash
.venv/bin/python main.py
```

## Pruebas

```bash
.venv/bin/python -m unittest discover -s tests -p 'test_*.py'
```

## Configuración

Los valores que suelen ajustarse están en `config.py`:

- `MODELO`: modelo principal de conversación.
- `MODELO_RESUMEN`: modelo usado para resumir la memoria.
- `OPCIONES_LLM`: opciones de generación (temperatura, contexto, etc.).
- `MAX_MENSAJES_POR_SECCION`: interacciones antes de resumir una sección de memoria.

## Datos del usuario

Los datos escribibles (historial de chat, calendario personal y quices) viven bajo una
raíz única: `data/` durante el desarrollo y la carpeta de datos del sistema operativo
en el ejecutable empaquetado. `app_paths.migrar_datos_heredados()` reubica los datos de
versiones anteriores al arrancar.

## Estructura

- `agent/`: cliente LLM, prompts estáticos, sesión conversacional y herramientas finas.
- `core/`: reglas de calendario, carga académica, quizzes, memoria, servicios y búsqueda web.
- `data/`: persistencia de memoria, documentos, calendario y quizzes; también contiene los recursos
  de solo lectura en `data/resources/`.
- `ui/`: interfaz de escritorio (tema, widgets, utilidades y secciones).
- `tests/`: pruebas automatizadas.

`main.py` solo inicia la aplicación; la composición de las dependencias vive en
`aplicacion.py`. La UI delega reglas a Core; Core coordina Agent y Data, y Data
concentra las operaciones persistentes.

Para el detalle módulo a módulo consulta [GUIA.md](GUIA.md).

## Empaquetar para Windows

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\build_windows.ps1
```

El ejecutable se genera en `dist\Aethera.exe`.
