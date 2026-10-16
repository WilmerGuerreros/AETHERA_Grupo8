"""Utilidades de la interfaz: extracción de PDF y análisis de Markdown."""

import re
from collections.abc import Iterator

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
MARKDOWN_LIST = re.compile(
    r"^(\s*)([-*+]|\d+[.)])(?:\s+|(?=\*\*|__|`|~~))(.*)$"
)


def analizar_markdown_en_linea(texto: str) -> Iterator[tuple[str, str | None]]:
    """Devuelve fragmentos de texto con su estilo Markdown en línea."""
    for parte in INLINE_MARKDOWN.split(texto):
        if not parte:
            continue
        estilo = None
        valor = parte
        if parte.startswith(("***", "___")) and parte.endswith(parte[:3]):
            valor = parte[3:-3]
            estilo = "bold_italic"
        elif parte.startswith(("**", "__")) and parte.endswith(parte[:2]):
            valor = parte[2:-2]
            estilo = "bold"
        elif parte.startswith("~~") and parte.endswith("~~"):
            valor = parte[2:-2]
            estilo = "strike"
        elif parte.startswith("`") and parte.endswith("`"):
            valor = parte[1:-1]
            estilo = "code"
        elif parte.startswith(("*", "_")) and parte.endswith(parte[0]):
            valor = parte[1:-1]
            estilo = "italic"
        yield valor, estilo


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
