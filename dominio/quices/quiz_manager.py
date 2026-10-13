"""Validación, persistencia y ejecución en memoria de quices educativos."""

import json
import logging
import os
import re
import tempfile
from pathlib import Path
from typing import Any

from app_paths import quizzes_directory


DIRECTORIO_QUICES = quizzes_directory()
_TEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,79}$")
_TEST_KEYS = {"test_id", "test_titulo", "paginas"}
_ALTERNATIVE_PAGE_KEYS = {
    "tipo",
    "pregunta",
    "alternativas",
    "retroalimentacion",
    "respuesta_correcta",
}
_DEVELOPMENT_PAGE_KEYS = {
    "tipo",
    "pregunta",
    "guia_evaluacion",
    "respuesta_sugerida",
}


def _validar_texto(valor: Any, campo: str) -> str:
    if not isinstance(valor, str) or not valor.strip():
        raise ValueError(f"'{campo}' debe ser texto no vacío.")
    return valor.strip()


def validar_test(datos: dict[str, Any] | str) -> dict[str, Any]:
    """Interpreta y valida el esquema acordado para un quiz educativo."""
    if isinstance(datos, str):
        try:
            datos = json.loads(datos)
        except json.JSONDecodeError as error:
            raise ValueError(f"El JSON del quiz no es válido: {error.msg}.") from error

    if not isinstance(datos, dict):
        raise ValueError("El quiz debe ser un objeto JSON.")
    if set(datos) != _TEST_KEYS:
        faltantes = sorted(_TEST_KEYS - set(datos))
        adicionales = sorted(set(datos) - _TEST_KEYS)
        detalle = []
        if faltantes:
            detalle.append(f"faltan claves: {', '.join(faltantes)}")
        if adicionales:
            detalle.append(f"claves no permitidas: {', '.join(adicionales)}")
        raise ValueError(f"El esquema del quiz no es válido ({'; '.join(detalle)}).")

    test_id = _validar_texto(datos["test_id"], "test_id")
    if not _TEST_ID_PATTERN.fullmatch(test_id):
        raise ValueError(
            "'test_id' debe comenzar con una letra o número y contener "
            "solo letras, números, guiones o guiones bajos (máximo 80 caracteres)."
        )

    titulo = _validar_texto(datos["test_titulo"], "test_titulo")
    paginas = datos["paginas"]
    if not isinstance(paginas, list) or not paginas:
        raise ValueError("'paginas' debe ser una lista con al menos una pregunta.")

    paginas_validadas = []
    ids_pagina = set()
    for indice, pagina in enumerate(paginas, start=1):
        campo_pagina = f"paginas[{indice - 1}]"
        if not isinstance(pagina, dict):
            raise ValueError(f"'{campo_pagina}' debe ser un objeto.")

        tipo = pagina.get("tipo")
        if tipo == "alternativa":
            claves_esperadas = _ALTERNATIVE_PAGE_KEYS
        elif tipo == "desarrollo":
            claves_esperadas = _DEVELOPMENT_PAGE_KEYS
        else:
            raise ValueError(
                f"'{campo_pagina}.tipo' debe ser 'alternativa' o 'desarrollo'."
            )
        claves_recibidas = set(pagina)
        if claves_recibidas not in (claves_esperadas, claves_esperadas | {"id"}):
            faltantes = sorted(claves_esperadas - set(pagina))
            adicionales = sorted(claves_recibidas - claves_esperadas - {"id"})
            detalle = []
            if faltantes:
                detalle.append(f"faltan claves: {', '.join(faltantes)}")
            if adicionales:
                detalle.append(f"claves no permitidas: {', '.join(adicionales)}")
            raise ValueError(
                f"El esquema de '{campo_pagina}' no es válido "
                f"({'; '.join(detalle)})."
            )

        page_id = _validar_texto(
            pagina.get("id", f"p{indice}"),
            f"{campo_pagina}.id",
        )
        if page_id in ids_pagina:
            raise ValueError(f"El id '{page_id}' está repetido en 'paginas'.")
        ids_pagina.add(page_id)
        pagina_validada: dict[str, Any] = {
            "id": page_id,
            "tipo": tipo,
            "pregunta": _validar_texto(
                pagina["pregunta"], f"{campo_pagina}.pregunta"
            ),
        }

        if tipo == "alternativa":
            alternativas = pagina["alternativas"]
            retroalimentacion = pagina["retroalimentacion"]
            if not isinstance(alternativas, dict) or len(alternativas) < 2:
                raise ValueError(
                    f"'{campo_pagina}.alternativas' debe tener al menos dos opciones."
                )
            if not all(
                isinstance(clave, str) and re.fullmatch(r"[A-Z]", clave)
                for clave in alternativas
            ):
                raise ValueError(
                    f"Las claves de '{campo_pagina}.alternativas' "
                    "deben ser letras mayúsculas individuales."
                )
            alternativas_validadas = {
                clave: _validar_texto(
                    valor, f"{campo_pagina}.alternativas.{clave}"
                )
                for clave, valor in alternativas.items()
            }
            if not isinstance(retroalimentacion, dict):
                raise ValueError(
                    f"'{campo_pagina}.retroalimentacion' debe ser un objeto."
                )
            if set(retroalimentacion) != set(alternativas):
                raise ValueError(
                    f"'{campo_pagina}.retroalimentacion' debe tener una "
                    "entrada por cada alternativa y ninguna adicional."
                )
            retroalimentacion_validada = {
                clave: _validar_texto(
                    valor, f"{campo_pagina}.retroalimentacion.{clave}"
                )
                for clave, valor in retroalimentacion.items()
            }
            respuesta_correcta = _validar_texto(
                pagina["respuesta_correcta"],
                f"{campo_pagina}.respuesta_correcta",
            )
            if respuesta_correcta not in alternativas_validadas:
                raise ValueError(
                    f"'{campo_pagina}.respuesta_correcta' debe coincidir "
                    "con una clave de alternativas."
                )
            pagina_validada.update(
                {
                    "alternativas": alternativas_validadas,
                    "retroalimentacion": retroalimentacion_validada,
                    "respuesta_correcta": respuesta_correcta,
                }
            )
        else:
            pagina_validada.update(
                {
                    "guia_evaluacion": _validar_texto(
                        pagina["guia_evaluacion"],
                        f"{campo_pagina}.guia_evaluacion",
                    ),
                    "respuesta_sugerida": _validar_texto(
                        pagina["respuesta_sugerida"],
                        f"{campo_pagina}.respuesta_sugerida",
                    ),
                }
            )
        paginas_validadas.append(pagina_validada)

    return {
        "test_id": test_id,
        "test_titulo": titulo,
        "paginas": paginas_validadas,
    }


class QuizSession:
    """Mantiene en memoria las respuestas de un intento de quiz."""

    def __init__(self, quiz: dict[str, Any]):
        self.quiz = validar_test(quiz)
        self._respuestas_desarrollo: dict[str, str] = {}
        self._paginas = {pagina["id"]: pagina for pagina in self.quiz["paginas"]}

    @property
    def respuestas_desarrollo(self) -> dict[str, str]:
        """Devuelve una copia de las respuestas abiertas recibidas hasta ahora."""
        return self._respuestas_desarrollo.copy()

    def responder_alternativa(
        self, pregunta_id: str, respuesta: str
    ) -> dict[str, bool | str]:
        """Evalúa una alternativa y devuelve su corrección y retroalimentación."""
        pagina = self._obtener_pregunta(pregunta_id, "alternativa")
        if not isinstance(respuesta, str):
            raise ValueError("La respuesta debe ser una clave de alternativa.")
        respuesta = respuesta.strip()
        retroalimentacion = pagina["retroalimentacion"]
        if respuesta not in pagina["alternativas"]:
            raise ValueError(
                f"La opción '{respuesta}' no existe para la pregunta '{pregunta_id}'."
            )
        return {
            "correcta": respuesta == pagina["respuesta_correcta"],
            "retroalimentacion": retroalimentacion[respuesta],
        }

    def guardar_respuesta_desarrollo(
        self, pregunta_id: str, respuesta: str
    ) -> None:
        """Guarda o reemplaza la respuesta del alumno a una pregunta abierta."""
        self._obtener_pregunta(pregunta_id, "desarrollo")
        respuesta_validada = _validar_texto(
            respuesta, f"respuesta de la pregunta '{pregunta_id}'"
        )
        self._respuestas_desarrollo[pregunta_id] = respuesta_validada

    def preparar_evaluacion(self) -> str:
        """Consolida el quiz y respuestas abiertas en un JSON para el LLM."""
        respuestas = [
            {
                "pregunta_id": pagina["id"],
                "pregunta": pagina["pregunta"],
                "respuesta_alumno": self._respuestas_desarrollo[pagina["id"]],
                "guia_evaluacion": pagina["guia_evaluacion"],
                "respuesta_sugerida": pagina["respuesta_sugerida"],
            }
            for pagina in self.quiz["paginas"]
            if pagina["tipo"] == "desarrollo"
            and pagina["id"] in self._respuestas_desarrollo
        ]
        return json.dumps(
            {
                "test": self.quiz,
                "respuestas_desarrollo": respuestas,
            },
            ensure_ascii=False,
            indent=2,
        )

    def _obtener_pregunta(self, pregunta_id: str, tipo: str) -> dict[str, Any]:
        if not isinstance(pregunta_id, str) or pregunta_id not in self._paginas:
            raise ValueError(f"No existe una pregunta con id '{pregunta_id}'.")
        pagina = self._paginas[pregunta_id]
        if pagina["tipo"] != tipo:
            raise ValueError(
                f"La pregunta '{pregunta_id}' no es de tipo '{tipo}'."
            )
        return pagina


class QuizManager:
    """Valida, guarda, lista y carga quizzes desde disco."""

    def __init__(self, directorio: Path | str = DIRECTORIO_QUICES):
        self.directorio = Path(directorio)

    def guardar(self, datos: dict[str, Any] | str) -> dict[str, str]:
        """Guarda un quiz UTF-8 en el directorio configurado, sin sobrescribir."""
        quiz = validar_test(datos)
        ruta_destino = self.directorio / f"{quiz['test_id']}.json"
        temporal = None
        try:
            self.directorio.mkdir(parents=True, exist_ok=True)
            contenido = json.dumps(quiz, ensure_ascii=False, indent=2) + "\n"
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                newline="",
                dir=self.directorio,
                prefix=f".{quiz['test_id']}.",
                suffix=".tmp",
                delete=False,
            ) as archivo:
                temporal = archivo.name
                archivo.write(contenido)
                archivo.flush()
                os.fsync(archivo.fileno())
            os.link(temporal, ruta_destino)
        except FileExistsError as error:
            raise FileExistsError(
                f"Ya existe un quiz con el id '{quiz['test_id']}'. No se sobrescribió."
            ) from error
        except OSError:
            logging.exception("No se pudo guardar el quiz.")
            raise
        finally:
            if temporal and os.path.exists(temporal):
                try:
                    os.unlink(temporal)
                except OSError:
                    logging.exception("No se pudo limpiar el archivo temporal del quiz.")

        return {"test_id": quiz["test_id"], "ruta": str(ruta_destino)}

    def listar(self) -> list[dict[str, Any]]:
        """Lee y valida todos los quizzes JSON de la carpeta de almacenamiento."""
        if not self.directorio.exists():
            return []
        quizzes = []
        for ruta in sorted(self.directorio.glob("*.json")):
            try:
                with ruta.open("r", encoding="utf-8") as archivo:
                    quizzes.append(validar_test(json.load(archivo)))
            except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
                raise ValueError(f"No se pudo cargar el quiz '{ruta.name}': {error}") from error
        return quizzes

    def cargar(self, test_id: str) -> dict[str, Any]:
        """Carga un quiz guardado por identificador y valida sus datos."""
        if not isinstance(test_id, str) or not _TEST_ID_PATTERN.fullmatch(test_id):
            raise ValueError("El identificador del quiz no tiene un formato válido.")
        ruta = self.directorio / f"{test_id}.json"
        try:
            with ruta.open("r", encoding="utf-8") as archivo:
                quiz = validar_test(json.load(archivo))
        except FileNotFoundError as error:
            raise FileNotFoundError(f"No existe el quiz '{test_id}'.") from error
        except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
            raise ValueError(f"No se pudo cargar el quiz '{test_id}': {error}") from error
        if quiz["test_id"] != test_id:
            raise ValueError(
                f"El id del archivo '{ruta.name}' no coincide con el contenido del quiz."
            )
        return quiz

    def iniciar(self, test_id: str) -> QuizSession:
        """Carga un quiz y crea una sesión local de respuestas."""
        return QuizSession(self.cargar(test_id))


def guardar_test(datos: dict[str, Any] | str) -> dict[str, str]:
    """Función compatible para guardar un quiz en los datos persistentes del usuario."""
    return QuizManager().guardar(datos)


def listar_tests() -> list[dict[str, Any]]:
    """Devuelve los quizzes guardados en los datos persistentes del usuario."""
    return QuizManager().listar()
