"""Lectura y escritura de historiales persistentes."""

import json
from datetime import datetime
from pathlib import Path


def leer_archivo_memoria(ruta: Path) -> str:
    """Lee un archivo de memoria codificado en UTF-8."""
    return ruta.read_text(encoding="utf-8")


def contar_conversaciones(archivo: Path) -> int:
    """Cuenta interacciones persistidas en un archivo de historial."""
    if not archivo.exists():
        return 0
    with archivo.open("r", encoding="utf-8") as historial:
        return sum(linea.startswith("Usuario:") for linea in historial)


def ruta_historial(carpeta_historial: Path, numero_seccion: int) -> Path:
    """Devuelve la ruta persistente de una sección de historial."""
    return Path(carpeta_historial) / f"HISTORIAL_{numero_seccion:04d}.txt"


def obtener_ultimo_archivo_historial(
    carpeta_historial: Path,
) -> tuple[Path | None, int]:
    """Encuentra el archivo de historial más reciente y cuenta sus entradas."""
    numero = 1
    while ruta_historial(carpeta_historial, numero).exists():
        numero += 1
    if numero == 1:
        return None, 0
    archivo = ruta_historial(carpeta_historial, numero - 1)
    return archivo, contar_conversaciones(archivo)


def leer_interacciones(archivo: Path) -> list[dict[str, str]]:
    """Lee y deserializa las interacciones de un archivo de historial."""
    if not archivo.exists():
        return []
    interacciones = []
    usuario = None
    respuesta = None

    with archivo.open("r", encoding="utf-8") as historial:
        for linea in historial:
            linea = linea.rstrip("\n")
            if linea.startswith("=" * 10):
                _agregar_interaccion(interacciones, usuario, respuesta)
                usuario = None
                respuesta = None
            elif linea.startswith("Usuario:"):
                usuario = [linea[len("Usuario:"):].strip()]
            elif linea.startswith("Aethera:"):
                respuesta = [linea[len("Aethera:"):].strip()]
            elif respuesta is not None:
                respuesta.append(linea)
            elif usuario is not None:
                usuario.append(linea)

    _agregar_interaccion(interacciones, usuario, respuesta)
    return interacciones


def _agregar_interaccion(interacciones, usuario, respuesta) -> None:
    if usuario is not None and respuesta is not None:
        interacciones.append({
            "usuario": "\n".join(usuario).strip(),
            "aethera": "\n".join(respuesta).strip(),
        })


def leer_interacciones_recientes(
    carpeta_historial: Path,
    numero_seccion: int,
    cantidad: int = 4,
) -> list[dict[str, str]]:
    """Lee las últimas interacciones a través de las secciones disponibles."""
    interacciones = []
    for numero in range(numero_seccion, 0, -1):
        archivo = ruta_historial(carpeta_historial, numero)
        interacciones = leer_interacciones(archivo) + interacciones
        if len(interacciones) >= cantidad:
            break
    return interacciones[-cantidad:]


def escribir_interaccion(
    carpeta_historial: Path,
    numero_seccion: int,
    usuario: str,
    respuesta: str,
) -> Path:
    """Añade una interacción y devuelve la ruta del archivo actualizado."""
    archivo = ruta_historial(carpeta_historial, numero_seccion)
    archivo.parent.mkdir(parents=True, exist_ok=True)
    fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with archivo.open("a", encoding="utf-8") as historial:
        historial.write("\n" + "=" * 60 + "\n")
        historial.write(f"Fecha: {fecha}\n")
        historial.write("=" * 60 + "\n")
        historial.write(f"Usuario: {usuario}\n")
        historial.write(f"Aethera: {respuesta}\n")
    return archivo


def guardar_resumen_memoria(
    carpeta_resumen: Path, numero_seccion: int, contenido: str
) -> Path:
    """Escribe el resumen de una sección en almacenamiento persistente."""
    ruta = Path(carpeta_resumen) / f"RESUMEN_{numero_seccion:04d}.txt"
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(contenido, encoding="utf-8")
    return ruta


def leer_resumen_memoria(
    carpeta_resumen: Path, numero_seccion: int
) -> str | None:
    """Lee el resumen de una sección o devuelve None si no está disponible."""
    ruta = Path(carpeta_resumen) / f"RESUMEN_{numero_seccion:04d}.txt"
    try:
        return ruta.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None


def leer_indice_memoria(carpeta_indice: Path) -> dict:
    """Lee el índice persistente o devuelve su estructura inicial."""
    archivo = Path(carpeta_indice) / "INDICE_MEMORIA.json"
    if not archivo.exists():
        return {"secciones": [], "temas": {}}
    return json.loads(archivo.read_text(encoding="utf-8"))


def guardar_indice_memoria(carpeta_indice: Path, indice: dict) -> Path:
    """Escribe el índice persistente de secciones de memoria."""
    archivo = Path(carpeta_indice) / "INDICE_MEMORIA.json"
    archivo.parent.mkdir(parents=True, exist_ok=True)
    archivo.write_text(
        json.dumps(indice, indent=4, ensure_ascii=False),
        encoding="utf-8",
    )
    return archivo
