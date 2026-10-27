from __future__ import annotations
from pathlib import Path
from io import BytesIO
from html import escape
import re, unicodedata
import fitz
from fontTools.ttLib import TTFont
ROOT = Path(__file__).resolve().parent
PAGE_RECT = fitz.Rect(0,0,612,792)
QUOTE_TRANSLATION = str.maketrans({0x201c:'\"',0x201d:'\"',0x201e:'\"',0x2018:"'",0x2019:"'",0x201a:"'"})
def normalize_article_text(text: str) -> str:
    return unicodedata.normalize("NFC", text).translate(QUOTE_TRANSLATION)

def complete_font(path: Path) -> bool:
    if not path.is_file():
        return False
    with TTFont(path) as font:
        cmap = font.getBestCmap() or {}
        if not all(ord(c) in cmap for c in "அகஙசஞடணதநபமயரலவழளறன"):
            return False
        if "glyf" in font:
            empty = sum(font["glyf"][g].numberOfContours == 0 for g in font.getGlyphOrder())
            if empty > len(font.getGlyphOrder()) // 4:
                return False
    return True

def validate_text(text: str, path: Path) -> None:
    with TTFont(path) as font:
        cmap = font.getBestCmap() or {}
        missing = sorted({c for c in text if not c.isspace() and ord(c) not in cmap})
    if missing:
        raise ValueError(f"{path.name} does not support: {' '.join(missing)}. "
                         "Supply a complete compatible font; no silent substitution is performed.")

def clean_blocks(raw: list[dict]) -> list[dict]:
    if not isinstance(raw, list):
        raise ValueError("The editor must return structured content.")
    blocks = []
    for source_index, item in enumerate(raw):
        kind = item.get("type", "body")
        if kind not in {"heading", "subheading", "body", "bullet", "number"}:
            raise ValueError("Unsupported editor block type.")
        runs = item.get("runs") or [{"text": item.get("text", ""), "bold": False}]
        runs = [{"text": normalize_article_text(str(r.get("text", ""))),
                 "bold": bool(r.get("bold", False)),
                 **({"color":str(r["color"]).lower()} if r.get("color") else {})} for r in runs]
        for run in runs:
            if run.get("color") and not re.fullmatch(r"#[0-9a-f]{6}",run["color"]):
                raise ValueError("Choose a valid text color.")
        text = "".join(r["text"] for r in runs)
        if text.strip():
            alignment = item.get("align", "justify" if kind == "body" else "left")
            if alignment not in {"left", "center", "right", "justify"}:
                alignment = "left"
            style = {}
            if item.get("align_explicit"):style["align_explicit"]=True
            if item.get("font_size") not in (None, ""):
                size = float(item["font_size"])
                if not 8 <= size <= 96:
                    raise ValueError("Font size must be between 8 and 96 points.")
                style["font_size"] = size
            if item.get("color"):
                color = str(item["color"]).lower()
                if not re.fullmatch(r"#[0-9a-f]{6}",color):
                    raise ValueError("Choose a valid text color.")
                style["color"] = color
            blocks.append({"type": kind, "runs": runs, "text": text, "align": alignment, **style,
                           "source_index": source_index,
                           "number": max(1, int(item.get("number", 1)))})
    if not blocks:
        raise ValueError("Please enter article content.")
    return blocks

def ensure_bold_font(body: Path) -> None:
    target, stamp = ROOT / "asset/body-bold.ttf", ROOT / "asset/body-bold.source"
    identity = f"{body}:{body.stat().st_mtime_ns}"
    if target.exists() and stamp.exists() and stamp.read_text() == identity:
        return
    target.parent.mkdir(exist_ok=True)
    with TTFont(body) as font:
        for record in font["name"].names:
            if record.nameID in (1, 3, 4, 6):
                record.string = "MagazineBold".encode(record.getEncoding())
        font.save(target)
    stamp.write_text(identity)

def embolden_overlay(document: fitz.Document) -> None:
    # Dedicated font resource lets us synthesize bold without switching glyphs.
    for page in document:
        bold = {f[4] for f in page.get_fonts() if "MagazineBold" in f[3]}
        for xref in page.get_contents():
            stream = document.xref_stream(xref)
            def replace(match):
                mode = b" 0.45 w 2 Tr" if match.group(1).decode("ascii") in bold else b" 0 Tr"
                return match.group(0) + mode
            stream = re.sub(rb"/([A-Za-z0-9_-]+)\s+[0-9.]+\s+Tf", replace, stream)
            document.update_stream(xref, stream)

def story_document(story: fitz.Story) -> fitz.Document:
    buffer = BytesIO()
    writer = fitz.DocumentWriter(buffer)
    device = writer.begin_page(PAGE_RECT)
    story.draw(device)
    writer.end_page(); writer.close()
    overlay = fitz.open(stream=buffer.getvalue(), filetype="pdf")
    embolden_overlay(overlay)
    return overlay

def draw_story(page: fitz.Page, story: fitz.Story) -> None:
    with story_document(story) as overlay:
        page.show_pdf_page(PAGE_RECT, overlay, 0)
