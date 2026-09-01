from __future__ import annotations

from .text_utils import display_filename

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import pandas as pd
from docx import Document
from pypdf import PdfReader

SUPPORTED = {".pdf", ".txt", ".md", ".csv", ".xlsx", ".xlsm", ".xls", ".json", ".docx"}


@dataclass
class Chunk:
    text: str
    source: str
    locator: str


def _split_text(text: str, max_chars: int = 1800, overlap: int = 220) -> list[str]:
    clean = "\n".join(line.strip() for line in text.splitlines() if line.strip())
    if len(clean) <= max_chars:
        return [clean] if clean else []
    chunks: list[str] = []
    start = 0
    while start < len(clean):
        end = min(len(clean), start + max_chars)
        chunks.append(clean[start:end])
        if end == len(clean):
            break
        start = max(0, end - overlap)
    return chunks


def _pdf_chunks(path: Path) -> Iterable[Chunk]:
    reader = PdfReader(str(path))
    for i, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        for j, chunk in enumerate(_split_text(text), start=1):
            yield Chunk(chunk, display_filename(path.name), f"page {i}, chunk {j}")


def _docx_chunks(path: Path) -> Iterable[Chunk]:
    doc = Document(path)
    text = "\n".join(p.text for p in doc.paragraphs if p.text.strip())
    for i, chunk in enumerate(_split_text(text), start=1):
        yield Chunk(chunk, display_filename(path.name), f"chunk {i}")


def _text_chunks(path: Path) -> Iterable[Chunk]:
    text = path.read_text(encoding="utf-8", errors="ignore")
    for i, chunk in enumerate(_split_text(text), start=1):
        yield Chunk(chunk, display_filename(path.name), f"chunk {i}")


def _csv_read(path: Path) -> pd.DataFrame:
    last = None
    for enc in ["utf-8-sig", "utf-8", "cp932", "shift_jis"]:
        try:
            return pd.read_csv(path, encoding=enc)
        except Exception as exc:
            last = exc
    raise last or RuntimeError("CSV read failed")


def _df_chunks(df: pd.DataFrame, source: str, locator_prefix: str = "") -> Iterable[Chunk]:
    header = ", ".join(map(str, df.columns))
    for start in range(0, len(df), 35):
        piece = df.iloc[start : start + 35]
        text = f"Columns: {header}\n" + piece.to_csv(index=False)
        prefix = f"{locator_prefix}, " if locator_prefix else ""
        yield Chunk(text, source, f"{prefix}rows {start + 1}-{start + len(piece)}")


def _csv_chunks(path: Path) -> Iterable[Chunk]:
    yield from _df_chunks(_csv_read(path), display_filename(path.name))


def _xlsx_chunks(path: Path) -> Iterable[Chunk]:
    book = pd.ExcelFile(path)
    for sheet in book.sheet_names:
        df = pd.read_excel(path, sheet_name=sheet)
        yield from _df_chunks(df, display_filename(path.name), f"sheet {sheet}")


def _json_chunks(path: Path) -> Iterable[Chunk]:
    text = path.read_text(encoding="utf-8", errors="ignore")
    for i, chunk in enumerate(_split_text(text), start=1):
        yield Chunk(chunk, display_filename(path.name), f"chunk {i}")


def load_chunks(data_dir: Path) -> tuple[list[Chunk], list[str]]:
    chunks: list[Chunk] = []
    warnings: list[str] = []
    if not data_dir.exists():
        return chunks, [f"Data directory does not exist: {data_dir}"]

    for path in sorted(data_dir.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in SUPPORTED:
            continue
        try:
            suffix = path.suffix.lower()
            if suffix == ".pdf":
                chunks.extend(_pdf_chunks(path))
            elif suffix == ".docx":
                chunks.extend(_docx_chunks(path))
            elif suffix in {".txt", ".md"}:
                chunks.extend(_text_chunks(path))
            elif suffix == ".csv":
                chunks.extend(_csv_chunks(path))
            elif suffix in {".xlsx", ".xlsm", ".xls"}:
                chunks.extend(_xlsx_chunks(path))
            elif suffix == ".json":
                chunks.extend(_json_chunks(path))
        except Exception as exc:
            warnings.append(f"{display_filename(path.name)}: {exc}")
    return chunks, warnings
