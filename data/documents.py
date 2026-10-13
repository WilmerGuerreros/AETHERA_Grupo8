"""Lectura de documentos adjuntos por el usuario."""

from pypdf import PdfReader


def extraer_texto_pdf(ruta: str) -> str:
    """Lee y extrae texto de un PDF local."""
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
