#!/usr/bin/env python3
"""Create or reuse compact metadata cache for candidate papers."""
from __future__ import annotations

import argparse
from pathlib import Path
from proceedings_common import extract_arxiv, load_triage, normalize_doi, registry_records, topic_hint, write_yaml
from proceedings_index import index_file
from proceedings_triage import decide


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--batch-dir", type=Path, required=True)
    ap.add_argument("--offline", action="store_true")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    items = [x for x in load_triage(args.batch_dir) if x.get("decision") == "candidate"]
    source = "triage"
    if not items:
        files = sorted((args.batch_dir / "extracted").glob("*.txt"))
        scan_limit = max((args.limit or 20) * 3, 20)
        records = registry_records(Path("."))
        items = []
        for path in files[:scan_limit]:
            paper = index_file(path, 900)
            d = decide(paper, records)
            if d["decision"] == "candidate":
                items.append({
                    "paper_id": paper.get("paper_id"),
                    "title": paper.get("title"),
                    "topic_hint": paper.get("topic_hint") or topic_hint(paper.get("title") or ""),
                    "extracted_text_path": paper.get("extracted_text_path"),
                    **d,
                })
        source = "on_the_fly"
    if args.limit:
        items = items[: args.limit]
    rows = []
    for item in items:
        text = " ".join(str(item.get(k, "")) for k in ("title", "extracted_text_path"))
        rows.append({
            "paper_id": item.get("paper_id"),
            "title": item.get("title"),
            "retrieval_status": "offline_unresolved" if args.offline else "not_queried_by_dry_workflow",
            "doi": normalize_doi(text),
            "arxiv_id": extract_arxiv(text),
            "bibtex": "",
            "bibtex_confidence": "medium" if args.offline else "unknown",
            "source_priority": ["doi/crossref", "dblp", "arxiv", "semantic_scholar/openalex", "official_proceedings_pdf"],
            "unresolved_fields": ["formal DOI/BibTeX not resolved in offline mode"] if args.offline else [],
        })
    if args.dry_run:
        print(f"metadata_items={len(rows)} offline={args.offline} source={source}")
        for r in rows[:5]:
            print(f"- {r['paper_id']} {r['retrieval_status']} {r['title'][:70] if r['title'] else ''}")
        return 0
    out = args.batch_dir / "metadata_cache"
    write_yaml(out / "metadata.yaml", {"metadata": rows})
    print(out / "metadata.yaml")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
