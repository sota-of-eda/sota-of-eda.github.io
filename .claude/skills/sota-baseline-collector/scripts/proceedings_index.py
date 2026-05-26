#!/usr/bin/env python3
"""Create compact paper indexes from extracted text."""
from __future__ import annotations

import argparse
import re
from pathlib import Path
from proceedings_common import SECTION_PATTERNS, WINDOW_PATTERNS, compact_text, infer_method, topic_hint, write_jsonl, write_yaml


def first_nonempty(lines: list[str]) -> str:
    skip = re.compile(
        r"^(?:date|ieee|copyright|\d+\s*$|\s*$|20\d\d\s+Design,\s+Automation\s*&\s*Test\s+in\s+Europe)",
        re.I,
    )
    cleaned = [line.strip().replace("\x01", " ") for line in lines[:100]]
    for i, s in enumerate(cleaned):
        if len(s) <= 12 or skip.match(s):
            continue
        title = s
        # DATE/IEEE extraction often wraps titles over two centered lines.
        for nxt in cleaned[i + 1 : i + 3]:
            low = nxt.lower()
            if (
                len(nxt) > 4
                and not skip.match(nxt)
                and not low.startswith("abstract")
                and not re.search(r"\b(university|institute|department|school|college|author|@)\b", low)
                and not re.search(r"\d\s*,|\b[A-Z][a-z]+\s+[A-Z][a-z]+", nxt)
            ):
                title += " " + nxt
                break
        return title
    return ""


def window(lines: list[str], idx: int, radius: int, max_chars: int) -> str:
    start = max(0, idx - radius)
    end = min(len(lines), idx + radius + 1)
    return compact_text("\n".join(lines[start:end]), max_chars)


def section_hits(lines: list[str]) -> dict[str, int]:
    hits = {}
    for i, line in enumerate(lines, 1):
        for name, pat in SECTION_PATTERNS.items():
            if name not in hits and pat.search(line):
                hits[name] = i
    return hits


def abstract_window(lines: list[str], hits: dict[str, int], max_chars: int) -> str:
    idx = hits.get("abstract", 1) - 1
    return window(lines, max(0, idx), 10, max_chars)


def collect_windows(lines: list[str], kind: str, max_chars: int, limit: int = 3) -> list[str]:
    pat = WINDOW_PATTERNS[kind]
    out = []
    seen = set()
    for i, line in enumerate(lines):
        if pat.search(line):
            w = window(lines, i, 4, max_chars)
            key = w[:80]
            if key not in seen:
                out.append(w)
                seen.add(key)
        if len(out) >= limit:
            break
    return out


def index_file(path: Path, max_chars: int) -> dict:
    text = path.read_text(encoding="utf-8", errors="ignore")
    lines = text.splitlines()
    title = first_nonempty(lines)
    method, acronym = infer_method(title)
    hits = section_hits(lines)
    combined = "\n".join([title, abstract_window(lines, hits, max_chars)] + collect_windows(lines, "experiment", max_chars, 2))
    return {
        "paper_id": path.stem,
        "extracted_text_path": str(path),
        "pdf_path": "",
        "pdf_url": "",
        "title": title,
        "title_confidence": "medium" if title else "low",
        "method_hint": method,
        "acronym_hint": acronym,
        "topic_hint": topic_hint(combined),
        "abstract_window": abstract_window(lines, hits, max_chars),
        "experiment_windows": collect_windows(lines, "experiment", max_chars),
        "table_windows": collect_windows(lines, "table", max_chars),
        "section_hits": hits,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--batch-dir", type=Path, required=True)
    ap.add_argument("--extracted-dir", type=Path)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--max-window-chars", type=int, default=900)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()
    extracted = args.extracted_dir or args.batch_dir / "extracted"
    files = sorted(extracted.glob("*.txt"))
    if args.limit:
        files = files[: args.limit]
    papers = [index_file(p, args.max_window_chars) for p in files]
    if args.dry_run:
        print(f"indexed={len(papers)}")
        for p in papers[:3]:
            size = sum(len(str(p.get(k, ""))) for k in ("abstract_window", "experiment_windows", "table_windows"))
            print(f"- {p['paper_id']} title={p['title'][:80]!r} compact_chars={size}")
        return 0
    out = args.batch_dir / "index"
    write_yaml(out / "paper_index.yaml", {"papers": papers})
    write_jsonl(out / "paper_index.jsonl", papers)
    print(out / "paper_index.yaml")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
