#!/usr/bin/env python3
"""Script-first triage and gap scan for unified SOTA-of-EDA batches."""
from __future__ import annotations

import argparse
import csv
from pathlib import Path
from proceedings_common import eda_score, kebab, load_index, normalize_title, registry_records, topic_hint, write_yaml
from proceedings_index import index_file


def decide(paper: dict, records: list[dict]) -> dict:
    title = paper.get("title") or ""
    norm = normalize_title(title)
    method = kebab(paper.get("method_hint") or title)
    for rec in records:
        if norm and norm == rec.get("title_norm"):
            return {"decision": "duplicate", "reason": "normalized_title match", "matched_path": rec.get("path")}
        if method and method == rec.get("baseline_id"):
            return {"decision": "duplicate", "reason": "baseline_id-like method match", "matched_path": rec.get("path")}
    text = "\n".join([title, paper.get("abstract_window") or ""] + paper.get("experiment_windows", []) + paper.get("table_windows", []))
    score, eda, non = eda_score(text)
    has_experiment = bool(paper.get("experiment_windows") or paper.get("table_windows"))
    if score >= 3 and has_experiment:
        decision, reason = "candidate", f"eda_terms={eda}; compact experiment/table evidence present"
    elif score <= 0 and non:
        decision, reason = "skip", f"non_eda_terms={non}; weak EDA evidence"
    else:
        decision, reason = "deferred", f"score={score}; eda_terms={eda}; needs compact review"
    return {"decision": decision, "reason": reason, "matched_path": ""}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--repo", type=Path, default=Path("."))
    ap.add_argument("--batch-dir", type=Path, required=True)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    papers = load_index(args.batch_dir)
    index_source = "persisted"
    if not papers:
        files = sorted((args.batch_dir / "extracted").glob("*.txt"))
        if args.limit:
            files = files[: args.limit]
        papers = [index_file(path, 900) for path in files]
        index_source = "on_the_fly"
    elif args.limit:
        papers = papers[: args.limit]
    records = registry_records(args.repo.resolve())
    items = []
    counts: dict[str, int] = {}
    for paper in papers:
        d = decide(paper, records)
        item = {
            "paper_id": paper.get("paper_id"),
            "title": paper.get("title"),
            "method_hint": paper.get("method_hint"),
            "topic_hint": paper.get("topic_hint") or topic_hint(paper.get("title") or ""),
            **d,
            "extracted_text_path": paper.get("extracted_text_path"),
        }
        items.append(item)
        counts[item["decision"]] = counts.get(item["decision"], 0) + 1
    if args.dry_run:
        print(f"index_source={index_source}")
        ordered = ["candidate", "skip", "duplicate", "deferred"]
        print("counts=" + ", ".join(f"{k}:{counts.get(k, 0)}" for k in ordered))
        for decision in ordered:
            examples = [item for item in items if item["decision"] == decision][:3]
            if examples:
                print(f"examples[{decision}]=")
                for item in examples:
                    print(f"- {item['paper_id']} {item['title'][:70] if item['title'] else ''}")
        return 0
    out = args.batch_dir / "triage"
    out.mkdir(parents=True, exist_ok=True)
    write_yaml(out / "triage.yaml", {"summary": {"count": len(items), "decision_counts": counts}, "items": items})
    for decision, filename in [("skip", "skips.tsv"), ("deferred", "deferred.tsv"), ("candidate", "gap_scan.tsv")]:
        with (out / filename).open("w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["decision", "paper_id", "title", "topic_hint", "reason", "extracted_text_path"], delimiter="\t")
            w.writeheader()
            for item in items:
                if item["decision"] == decision:
                    w.writerow({k: item.get(k, "") for k in w.fieldnames})
    print(out / "triage.yaml")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
