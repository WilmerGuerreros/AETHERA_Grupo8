#!/usr/bin/env python3
"""Genera versiones legibles (.md) de PDF, Word, Excel y PowerPoint.

Uso:
    python tools/preview.py          # solo Markdown
    python tools/preview.py --pdf    # Markdown + PDF (requiere LibreOffice)

Salida:
    previews/<ruta-relativa>.md      (texto legible por ChatGPT/GitHub)
    previews/<ruta-relativa>.pdf     (solo con --pdf)
    previews/README.md               (índice)

No necesita dependencias para docx/xlsx/pptx (usa la stdlib).
Para PDF usa pypdf (pip install pypdf).
"""

import argparse
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "previews"
SKIP_DIRS = {".git", "previews", "node_modules", ".venv", "venv", "__pycache__"}
SUPPORTED = {".pdf", ".docx", ".xlsx", ".pptx"}
MAX_MB = 50

NS_W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
NS_A = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
NS_S = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
NS_R = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
NS_PKG_REL = "{http://schemas.openxmlformats.org/package/2006/relationships}"


def docx_text(path: Path) -> str:
    with zipfile.ZipFile(path) as z:
        root = ET.fromstring(z.read("word/document.xml"))
    lines = []
    for p in root.iter(NS_W + "p"):
        line = "".join(t.text or "" for t in p.iter(NS_W + "t")).strip()
        if line:
            lines.append(line)
    return "\n\n".join(lines)


def xlsx_text(path: Path) -> str:
    with zipfile.ZipFile(path) as z:
        names = set(z.namelist())
        shared = []
        if "xl/sharedStrings.xml" in names:
            sroot = ET.fromstring(z.read("xl/sharedStrings.xml"))
            for si in sroot.iter(NS_S + "si"):
                shared.append("".join(t.text or "" for t in si.iter(NS_S + "t")))

        wb = ET.fromstring(z.read("xl/workbook.xml"))
        rels = {}
        if "xl/_rels/workbook.xml.rels" in names:
            rroot = ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))
            for rel in rroot.iter(NS_PKG_REL + "Relationship"):
                rels[rel.attrib.get("Id")] = rel.attrib.get("Target", "")

        blocks = []
        for sheet in wb.iter(NS_S + "sheet"):
            name = sheet.attrib.get("name", "?")
            target = rels.get(sheet.attrib.get(NS_R + "id", ""), "").lstrip("/")
            if not target.startswith("xl/"):
                target = "xl/" + target
            if target not in names:
                continue

            rows = []
            sroot = ET.fromstring(z.read(target))
            for row in sroot.iter(NS_S + "row"):
                cells = []
                for c in row.iter(NS_S + "c"):
                    ctype = c.attrib.get("t")
                    if ctype == "inlineStr":
                        value = "".join(t.text or "" for t in c.iter(NS_S + "t"))
                    else:
                        v = c.find(NS_S + "v")
                        value = v.text if v is not None and v.text else ""
                        if ctype == "s" and value:
                            try:
                                value = shared[int(value)]
                            except (ValueError, IndexError):
                                pass
                    cells.append(value)
                if any(x.strip() for x in cells):
                    rows.append(cells)
            blocks.append(f"## Hoja: {name}\n\n{markdown_table(rows)}")
        return "\n\n".join(blocks)


def markdown_table(rows):
    if not rows:
        return "_(vacía)_"
    width = max(len(r) for r in rows)
    rows = [r + [""] * (width - len(r)) for r in rows]

    def esc(value):
        return str(value).replace("|", "\\|").replace("\n", " ").strip()

    out = ["| " + " | ".join(esc(c) for c in rows[0]) + " |"]
    out.append("|" + "|".join([" --- "] * width) + "|")
    for row in rows[1:]:
        out.append("| " + " | ".join(esc(c) for c in row) + " |")
    return "\n".join(out)


def pptx_text(path: Path) -> str:
    with zipfile.ZipFile(path) as z:
        slides = [n for n in z.namelist() if re.fullmatch(r"ppt/slides/slide\d+\.xml", n)]
        slides.sort(key=lambda n: int(re.search(r"(\d+)\.xml$", n).group(1)))
        blocks = []
        for n in slides:
            root = ET.fromstring(z.read(n))
            num = int(re.search(r"(\d+)\.xml$", n).group(1))
            parts = []
            for p in root.iter(NS_A + "p"):
                line = "".join(t.text or "" for t in p.iter(NS_A + "t")).strip()
                if line:
                    parts.append(line)
            blocks.append(f"## Diapositiva {num}\n\n" + ("\n\n".join(parts) or "_(sin texto)_"))
        return "\n\n".join(blocks)


def pdf_text(path: Path) -> str:
    try:
        from pypdf import PdfReader
    except ImportError:
        return "_(pypdf no instalado: no se pudo extraer el texto)_"
    reader = PdfReader(str(path))
    blocks = []
    for i, page in enumerate(reader.pages, start=1):
        text = (page.extract_text() or "").strip()
        if not text:
            text = "_(sin texto extraíble: página escaneada o basada en imagen)_"
        blocks.append(f"## Página {i}\n\n{text}")
    return "\n\n".join(blocks)


EXTRACTORS = {".docx": docx_text, ".xlsx": xlsx_text, ".pptx": pptx_text, ".pdf": pdf_text}


def iter_sources():
    for path in ROOT.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in SUPPORTED:
            continue
        if any(part in SKIP_DIRS for part in path.relative_to(ROOT).parts):
            continue
        yield path


def make_markdown(src: Path, out_md: Path, pdf: bool) -> None:
    rel_path = src.relative_to(ROOT)
    rel = rel_path.as_posix()
    size_mb = src.stat().st_size / (1024 * 1024)
    if size_mb > MAX_MB:
        body = f"_(archivo demasiado grande: {size_mb:.1f} MB)_"
    else:
        try:
            body = EXTRACTORS[src.suffix.lower()](src)
        except Exception as exc:  # noqa: BLE001
            body = f"_(error extrayendo texto: {type(exc).__name__}: {exc})_"

    header = [
        f"# {src.name}",
        "",
        f"> Generado automáticamente desde [`{rel}`]({'../' * (len(rel_path.parent.parts) + 1)}{rel}). No editar a mano.",
    ]
    if pdf:
        pdf_name = src.with_suffix(".pdf").name
        header.append(f"> [Versión PDF]({pdf_name})")
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text("\n".join(header) + "\n\n" + body + "\n", encoding="utf-8")


def convert_pdf(src: Path, out_pdf: Path) -> None:
    out_pdf.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["soffice", "--headless", "--convert-to", "pdf", "--outdir", str(out_pdf.parent), str(src)],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=180,
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pdf", action="store_true", help="también convierte a PDF con LibreOffice")
    args = parser.parse_args()

    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)

    created = []
    for src in sorted(iter_sources()):
        rel = src.relative_to(ROOT)
        out_md = OUT / rel.parent / (rel.name + ".md")
        make_markdown(src, out_md, args.pdf)
        if args.pdf and src.suffix.lower() != ".pdf":
            try:
                convert_pdf(src, OUT / rel.parent / (rel.stem + ".pdf"))
            except Exception as exc:  # noqa: BLE001
                print(f"aviso: no se pudo convertir {rel}: {exc}", file=sys.stderr)
                out_md.write_text(
                    out_md.read_text(encoding="utf-8").replace(
                        f"> [Versión PDF]({rel.stem}.pdf)", "> _(PDF no generado)_"
                    ),
                    encoding="utf-8",
                )
        created.append(rel.as_posix())

    index = ["# Previews legibles", "", "Generado automáticamente. No editar a mano.", ""]
    if created:
        index += [f"- [`{p}`]({p}.md)" for p in created]
    else:
        index.append("_(sin archivos compatibles)_")
    (OUT / "README.md").write_text("\n".join(index) + "\n", encoding="utf-8")
    print(f"OK: {len(created)} archivo(s) -> {OUT}")
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    raise SystemExit(main())
