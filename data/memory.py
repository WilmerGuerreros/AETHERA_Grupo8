"""Lectura y escritura de historiales persistentes."""

import json
from datetime import datetime
from pathlib import Path

from data.paths import MemoryPaths, memory_paths


class MemoryStore:
    """Repositorio de memoria que encapsula rutas, lectura y escritura.

    La raíz solo se indica para inyectar una ubicación alternativa en pruebas;
    en producción se resuelve con ``memory_paths()``.
    """

    def __init__(self, raiz: Path | str | None = None) -> None:
        self.rutas: MemoryPaths = memory_paths(raiz).ensure()

    def reubicar(self, raiz: Path | str) -> None:
        """Actualiza las rutas cuando se renombra la carpeta del chat."""
        self.rutas = memory_paths(Path(raiz)).ensure()

    # --- historial ---

    def nombre_historial(self, numero_seccion: int) -> str:
        """Nombre del archivo de historial de una sección."""
        return f"HISTORIAL_{numero_seccion:04d}.txt"

    def nombre_resumen(self, numero_seccion: int) -> str:
        """Nombre del archivo de resumen de una sección."""
        return f"RESUMEN_{numero_seccion:04d}.txt"

    def ultima_seccion(self) -> tuple[int, int]:
        """Devuelve (última sección, interacciones) o (0, 0) si no hay ninguna."""
        numero = 1
        while self._ruta_historial(numero).exists():
            numero += 1
        if numero == 1:
            return 0, 0
        ultima = numero - 1
        return ultima, self.contar_conversaciones(ultima)

    def contar_conversaciones(self, numero_seccion: int) -> int:
        """Cuenta interacciones persistidas en una sección de historial."""
        archivo = self._ruta_historial(numero_seccion)
        if not archivo.exists():
            return 0
        with archivo.open("r", encoding="utf-8") as historial:
            return sum(linea.startswith("Usuario:") for linea in historial)

    def leer_historial(self, numero_seccion: int) -> str:
        """Lee el contenido completo de una sección de historial."""
        return self._ruta_historial(numero_seccion).read_text(encoding="utf-8")

    def leer_interacciones(self, numero_seccion: int) -> list[dict[str, str]]:
        """Lee y deserializa las interacciones de una sección de historial."""
        archivo = self._ruta_historial(numero_seccion)
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

    def leer_interacciones_recientes(
        self,
        numero_seccion: int,
        cantidad: int = 4,
    ) -> list[dict[str, str]]:
        """Lee las últimas interacciones a través de las secciones disponibles."""
        interacciones = []
        for numero in range(numero_seccion, 0, -1):
            interacciones = (
                self.leer_interacciones(numero) + interacciones
            )
            if len(interacciones) >= cantidad:
                break
        return interacciones[-cantidad:]

    def escribir(self, numero_seccion: int, usuario: str, respuesta: str) -> None:
        """Añade una interacción a la sección de historial indicada."""
        archivo = self._ruta_historial(numero_seccion)
        archivo.parent.mkdir(parents=True, exist_ok=True)
        fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with archivo.open("a", encoding="utf-8") as historial:
            historial.write("\n" + "=" * 60 + "\n")
            historial.write(f"Fecha: {fecha}\n")
            historial.write("=" * 60 + "\n")
            historial.write(f"Usuario: {usuario}\n")
            historial.write(f"Aethera: {respuesta}\n")

    # --- resumen ---

    def guardar_resumen(self, numero_seccion: int, contenido: str) -> None:
        """Escribe el resumen de una sección en almacenamiento persistente."""
        ruta = self.rutas.resumen / self.nombre_resumen(numero_seccion)
        ruta.parent.mkdir(parents=True, exist_ok=True)
        ruta.write_text(contenido, encoding="utf-8")

    def leer_resumen(self, numero_seccion: int) -> str | None:
        """Lee el resumen de una sección o devuelve None si no está disponible."""
        ruta = self.rutas.resumen / self.nombre_resumen(numero_seccion)
        try:
            return ruta.read_text(encoding="utf-8")
        except FileNotFoundError:
            return None

    # --- índice ---

    def leer_indice(self) -> dict:
        """Lee el índice persistente o devuelve su estructura inicial."""
        archivo = self.rutas.indice / "INDICE_MEMORIA.json"
        if not archivo.exists():
            return {"secciones": [], "temas": {}}
        return json.loads(archivo.read_text(encoding="utf-8"))

    def guardar_indice(self, indice: dict) -> None:
        """Escribe el índice persistente de secciones de memoria."""
        archivo = self.rutas.indice / "INDICE_MEMORIA.json"
        archivo.parent.mkdir(parents=True, exist_ok=True)
        archivo.write_text(
            json.dumps(indice, indent=4, ensure_ascii=False),
            encoding="utf-8",
        )

    # --- helpers internos ---

    def _ruta_historial(self, numero_seccion: int) -> Path:
        return self.rutas.historial / self.nombre_historial(numero_seccion)


def _agregar_interaccion(interacciones, usuario, respuesta) -> None:
    if usuario is not None and respuesta is not None:
        interacciones.append({
            "usuario": "\n".join(usuario).strip(),
            "aethera": "\n".join(respuesta).strip(),
        })
