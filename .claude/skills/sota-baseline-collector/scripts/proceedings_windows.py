#!/usr/bin/env python3
"""Generate compact review packets from triage and paper index."""
from __future__ import annotations

import argparse
from pathlib import Path
from proceedings_common import compact_text, load_index, load_triage, registry_records, topic_hint, write_yaml
from proceedings_index import index_file
from proceedings_triage import decide


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--batch-dir", type=Path, required=True)
    ap.add_argument("--decision", default="candidate")
    ap.add_argument("--include-deferred", action="store_true")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--max-chars-per-paper", type=int, default=2600)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    paper_list = load_index(args.batch_dir)
    if not paper_list:
        files = sorted((args.batch_dir / "extracted").glob("*.txt"))
        scan_limit = args.limit or 20
        paper_list = [index_file(path, 900) for path in files[:scan_limit]]
    papers = {p.get("paper_id"): p for p in paper_list}
    triage = load_triage(args.batch_dir)
    if not triage:
        records = registry_records(Path("."))
        triage = []
        for p in paper_list:
            d = decide(p, records)
            triage.append({
                "paper_id": p.get("paper_id"),
                "title": p.get("title"),
                "method_hint": p.get("method_hint"),
                "topic_hint": p.get("topic_hint") or topic_hint(p.get("title") or ""),
                "extracted_text_path": p.get("extracted_text_path"),
                **d,
            })
    decisions = {args.decision}
    if args.include_deferred:
        decisions.add("deferred")
    selected = [t for t in triage if t.get("decision") in decisions]
    if args.limit:
        selected = selected[: args.limit]
    packets = []
    for t in selected:
        p = papers.get(t.get("paper_id"), {})
        body = {
            "paper_id": t.get("paper_id"),
            "title": t.get("title") or p.get("title"),
            "method_hint": t.get("method_hint") or p.get("method_hint"),
            "topic_hint": t.get("topic_hint") or p.get("topic_hint"),
            "decision": t.get("decision"),
            "dedupe_status": t.get("reason"),
            "metadata_status": "unresolved_before_metadata_step",
            "extracted_text_path": p.get("extracted_text_path") or t.get("extracted_text_path"),
            "abstract_window": p.get("abstract_window", ""),
            "experiment_windows": p.get("experiment_windows", [])[:3],
            "table_windows": p.get("table_windows", [])[:3],
        }
        # Size guard: trim verbose windows, never fall back to full text.
        as_text = str(body)
        if len(as_text) > args.max_chars_per_paper:
            body["abstract_window"] = compact_text(body["abstract_window"], 600)
            body["experiment_windows"] = [compact_text(x, 500) for x in body["experiment_windows"][:2]]
            body["table_windows"] = [compact_text(x, 400) for x in body["table_windows"][:1]]
        packets.append(body)
    if args.dry_run:
        print(f"packets={len(packets)}")
        for p in packets[:5]:
            print(f"- {p['paper_id']} {p['decision']} {p['title'][:80] if p['title'] else ''}")
        return 0
    out = args.batch_dir / "packets"
    write_yaml(out / "review_packets.yaml", {"packets": packets})
    print(out / "review_packets.yaml")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
