#!/usr/bin/env python3
"""Normalize arbitrary inputs into a batch-local source manifest."""
from __future__ import annotations

import argparse
import re
from pathlib import Path
from proceedings_common import extract_arxiv, kebab, write_jsonl, write_yaml

URL_RE = re.compile(r"https?://\S+")
DOI_RE = re.compile(r"10\.\d{4,9}/\S+", re.I)


def item(source_id: str, kind: str, value: str) -> dict:
    p = Path(value)
    url = value if URL_RE.match(value) else ""
    pdf_path = str(p) if p.exists() and p.suffix.lower() == ".pdf" else ""
    title = p.stem if pdf_path else ("" if url else value.strip())
    doi = DOI_RE.search(value)
    return {
        "source_id": source_id,
        "input_kind": kind,
        "input_value": value,
        "title_hint": title,
        "pdf_path": pdf_path,
        "pdf_url": url if url.lower().endswith(".pdf") else "",
        "doi": doi.group(0).rstrip(".,)") if doi else "",
        "arxiv_id": extract_arxiv(value),
        "status": "pdf_available" if (pdf_path or url.lower().endswith(".pdf")) else "resolved",
        "notes": ["offline acquisition; metadata resolution deferred"],
    }


def parse_list(path: Path) -> list[str]:
    values = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip(" -\t")
        if line and not line.startswith("#"):
            values.append(line)
    return values


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--batch-dir", type=Path, required=True)
    ap.add_argument("--query", action="append", default=[])
    ap.add_argument("--list-file", type=Path)
    ap.add_argument("--pdf-dir", type=Path)
    ap.add_argument("--pdf", action="append", default=[])
    ap.add_argument("--url", action="append", default=[])
    ap.add_argument("--offline", action="store_true")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    values: list[tuple[str, str]] = []
    values += [("query", q) for q in args.query]
    values += [("url", u) for u in args.url]
    values += [("pdf", p) for p in args.pdf]
    if args.list_file:
        values += [("list_item", v) for v in parse_list(args.list_file)]
    if args.pdf_dir:
        values += [("pdf_dir_item", str(p)) for p in sorted(args.pdf_dir.glob("*.pdf"))]
        # Some existing batches pass an extracted-text directory here for dry-run
        # acquisition; keep the manifest vocabulary stable.
        values += [("pdf_dir_item", str(p)) for p in sorted(args.pdf_dir.glob("*.txt"))]
    if args.limit:
        values = values[: args.limit]

    rows = [item(f"src-{i:04d}-{kebab(v)[:40]}", kind, v) for i, (kind, v) in enumerate(values, 1)]
    result = {"source_manifest": {"batch_dir": str(args.batch_dir), "offline": args.offline, "count": len(rows)}, "items": rows}
    if args.dry_run:
        print(f"sources={len(rows)}")
        for row in rows[:5]:
            print(f"- {row['source_id']} {row['status']} {row['input_value']}")
        return 0
    out = args.batch_dir / "sources"
    write_yaml(out / "source_manifest.yaml", result)
    write_jsonl(out / "source_manifest.jsonl", rows)
    print(out / "source_manifest.yaml")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
