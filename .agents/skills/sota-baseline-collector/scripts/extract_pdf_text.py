#!/usr/bin/env python3
"""Extract text from local PDF files for SOTA-of-EDA baseline collection."""
from __future__ import annotations

import argparse
import hashlib
import shutil
import subprocess
from pathlib import Path


class ExtractorUnavailable(RuntimeError):
    pass


class ExtractionError(RuntimeError):
    pass


def extract_with_pdftotext(path: Path, max_pages: int | None) -> str | None:
    if not shutil.which("pdftotext"):
        raise ExtractorUnavailable("pdftotext not found on PATH")
    cmd = ["pdftotext", "-layout"]
    if max_pages:
        cmd.extend(["-f", "1", "-l", str(max_pages)])
    cmd.extend([str(path), "-"])
    result = subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    return result.stdout


def extract_with_pypdf(path: Path, max_pages: int | None) -> str | None:
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise ExtractorUnavailable("pypdf is not installed") from exc
    reader = PdfReader(str(path))
    pages = reader.pages[:max_pages] if max_pages else reader.pages
    return "\n\n".join(page.extract_text() or "" for page in pages)


def extract_with_pdfplumber(path: Path, max_pages: int | None) -> str | None:
    try:
        import pdfplumber
    except ImportError as exc:
        raise ExtractorUnavailable("pdfplumber is not installed") from exc
    chunks = []
    with pdfplumber.open(str(path)) as pdf:
        pages = pdf.pages[:max_pages] if max_pages else pdf.pages
        for page in pages:
            chunks.append(page.extract_text() or "")
    return "\n\n".join(chunks)


def extract_text(path: Path, max_pages: int | None) -> str:
    if not path.exists():
        raise FileNotFoundError(f"PDF does not exist: {path}")
    if not path.is_file():
        raise FileNotFoundError(f"PDF path is not a file: {path}")

    errors: list[str] = []
    extractors = (
        ("pdftotext", extract_with_pdftotext),
        ("pypdf", extract_with_pypdf),
        ("pdfplumber", extract_with_pdfplumber),
    )
    for name, extractor in extractors:
        try:
            text = extractor(path, max_pages)
        except subprocess.CalledProcessError as exc:
            detail = (exc.stderr or exc.stdout or str(exc)).strip()
            errors.append(f"{name}: command failed: {detail}")
            continue
        except ExtractorUnavailable as exc:
            errors.append(f"{name}: unavailable: {exc}")
            continue
        except Exception as exc:  # keep trying fallbacks, but preserve diagnostics
            errors.append(f"{name}: failed: {type(exc).__name__}: {exc}")
            continue
        if text and text.strip():
            return text
        errors.append(f"{name}: extracted no text")

    detail = "; ".join(errors) if errors else "no extractors attempted"
    raise ExtractionError(f"Could not extract text from {path}. Attempts: {detail}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pdfs", nargs="*", type=Path, help="Local PDF files")
    parser.add_argument("--max-pages", type=int, default=0, help="Maximum pages per PDF; 0 means all pages")
    parser.add_argument("--max-chars", type=int, default=0, help="Maximum characters to print/write per PDF; 0 means all")
    parser.add_argument("--out-dir", type=Path, help="Optional directory for extracted .txt files")
    args = parser.parse_args()

    if not args.pdfs:
        parser.print_help()
        return 0

    max_pages = args.max_pages or None
    max_chars = args.max_chars or None
    if args.out_dir:
        args.out_dir.mkdir(parents=True, exist_ok=True)

    failures = 0
    for pdf in args.pdfs:
        try:
            text = extract_text(pdf, max_pages)
        except Exception as exc:
            failures += 1
            print(f"ERROR: {exc}")
            continue
        if max_chars:
            text = text[:max_chars]
        if args.out_dir:
            digest = hashlib.sha1(str(pdf.resolve()).encode("utf-8")).hexdigest()[:8]
            output = args.out_dir / f"{pdf.stem}-{digest}.txt"
            output.write_text(text, encoding="utf-8")
            print(output)
        else:
            print(f"===== {pdf} =====")
            print(text)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
