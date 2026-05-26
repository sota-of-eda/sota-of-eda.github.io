#!/usr/bin/env python3
"""Detect whether current-batch topic proposals worsen topic fanout."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from pathlib import Path
from proceedings_common import load_triage, read_yaml, write_yaml

MAX_SIBLINGS = 6
MAX_CHILDREN = 10
AGGREGATES = ["signoff-analysis", "front-end-design-automation", "emerging-technology-eda", "package-pcb-design", "manufacturing-reliability", "analog-circuit-design-automation"]


def load_topics(repo: Path) -> dict[str, dict]:
    topics = {}
    for p in sorted((repo / "data" / "topics").rglob("*.yaml")):
        try:
            d = read_yaml(p)
        except Exception:
            continue
        if isinstance(d, dict) and d.get("topic_id"):
            topics[d["topic_id"]] = {**d, "path": str(p)}
    return topics


def proposals(batch_dir: Path) -> list[dict]:
    out = []
    for item in load_triage(batch_dir):
        topic = item.get("topic_hint")
        if item.get("decision") in {"candidate", "deferred"} and topic and topic not in {"unclassified", ""}:
            out.append({"topic_id": topic, "parent_id": "", "paper_id": item.get("paper_id"), "title": item.get("title")})
    # Also inspect root drafts if any exist; useful for post-triage use.
    for p in sorted(Path("data/drafts").glob("*.yaml")):
        try:
            d = read_yaml(p)
        except Exception:
            continue
        ct = d.get("candidate_topic") or {}
        if isinstance(ct, dict) and ct.get("status") == "proposed":
            pt = ct.get("proposed_topic") or {}
            out.append({"topic_id": pt.get("topic_id") or ct.get("topic_id"), "parent_id": pt.get("parent_id") or "", "paper_id": p.stem, "title": (d.get("baseline") or {}).get("publication", {}).get("title")})
    return [x for x in out if x.get("topic_id")]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--repo", type=Path, default=Path("."))
    ap.add_argument("--batch-dir", type=Path, required=True)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    topics = load_topics(args.repo.resolve())
    props = proposals(args.batch_dir)
    existing_ids = set(topics)
    children = defaultdict(list)
    for t in topics.values():
        if t.get("parent_id"):
            children[t["parent_id"]].append(t["topic_id"])
    new_topics = [p for p in props if p["topic_id"] not in existing_ids]
    by_parent = defaultdict(list)
    for p in new_topics:
        by_parent[p.get("parent_id") or "unclassified_parent"].append(p["topic_id"])
    overloaded = []
    for parent, additions in by_parent.items():
        current = children.get(parent, [])
        after = len(set(current) | set(additions))
        if after > MAX_SIBLINGS or after > MAX_CHILDREN or (len(current) > MAX_SIBLINGS and additions):
            overloaded.append({"parent_id": parent, "current_children": current, "proposed_additions": sorted(set(additions)), "after_count": after})
    status = "rearrange_required" if overloaded else "allow"
    counts = Counter(p["topic_id"] for p in props)
    report = {"status": status, "proposals": len(props), "new_topic_proposals": len(new_topics), "overloaded_parents": overloaded, "topic_counts": dict(counts)}
    remap = [{"old_topic_hint": o["proposed_additions"][0], "action": "group_under_aggregate", "final_topic_id": AGGREGATES[0], "new_parent_id": o["parent_id"], "reason": "current batch would worsen sibling/child fanout"} for o in overloaded if o.get("proposed_additions")]
    if args.dry_run:
        print(f"status={status} proposals={len(props)} new_topics={len(new_topics)} overloaded={len(overloaded)}")
        for o in overloaded[:5]:
            print(f"- {o['parent_id']} after={o['after_count']} additions={','.join(o['proposed_additions'][:6])}")
        return 0
    out = args.batch_dir / "topic_gate"
    write_yaml(out / "topic_gate_report.yaml", report)
    write_yaml(out / "topic_remap.yaml", {"remaps": remap})
    packet = ["# Topic Rearrangement Packet", "", f"status: `{status}`", ""]
    for o in overloaded:
        packet += [f"## Parent `{o['parent_id']}`", f"Current: {', '.join(o['current_children']) or '(none)' }", f"Additions: {', '.join(o['proposed_additions'])}", f"Suggested aggregates: {', '.join(AGGREGATES)}", ""]
    (out / "topic_rearrange_packet.md").write_text("\n".join(packet), encoding="utf-8")
    print(out / "topic_gate_report.yaml")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
