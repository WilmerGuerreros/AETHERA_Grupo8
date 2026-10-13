"""Utilidades de la interfaz: extracción de PDF y análisis de Markdown."""

import re

from pypdf import PdfReader

INLINE_MARKDOWN = re.compile(
    r"(\*\*\*.+?\*\*\*|___.+?___|\*\*.+?\*\*|__.+?__|"
    r"(?<!\*)\*(?!\*).+?(?<!\*)\*(?!\*)|"
    r"(?<!_)_(?!_).+?(?<!_)_(?!_)|`[^`\n]+`|~~.+?~~)"
)
EMOJI_CHAR = re.compile(
    r"(?:"
    r"[#*0-9]\uFE0F?\u20E3"
    r"|[\U0001F1E6-\U0001F1FF]{2}"
    r"|[\U0001F000-\U0001FAFF\u2600-\u27BF]"
    r"(?:\uFE0F|\uFE0E)?"
    r"(?:[\U0001F3FB-\U0001F3FF])?"
    r"(?:\u200D[\U0001F000-\U0001FAFF\u2600-\u27BF](?:\uFE0F)?"
    r"(?:[\U0001F3FB-\U0001F3FF])?)*"
    r")"
)
MARKDOWN_TABLE_SEPARATOR = re.compile(r":?-{3,}:?")


def _markdown_table_cells(line):
    stripped = line.strip()
    if "|" not in stripped:
        return None
    if stripped.startswith("|"):
        stripped = stripped[1:]
    if stripped.endswith("|"):
        stripped = stripped[:-1]
    return [cell.strip().replace(r"\|", "|") for cell in re.split(r"(?<!\\)\|", stripped)]


def _is_markdown_table_separator(line):
    cells = _markdown_table_cells(line)
    return bool(cells) and all(MARKDOWN_TABLE_SEPARATOR.fullmatch(cell) for cell in cells)


def extraer_texto_pdf(ruta):
    reader = PdfReader(ruta)
    if reader.is_encrypted:
        raise ValueError("El PDF está protegido con contraseña.")
    paginas = [pagina.extract_text() or "" for pagina in reader.pages]
    texto = "\n\n".join(pagina.strip() for pagina in paginas if pagina.strip())
    if not texto:
        raise ValueError(
            "El PDF no contiene texto legible. "
            "Los documentos escaneados requieren reconocimiento OCR."
        )
    return texto
