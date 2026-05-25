#!/usr/bin/env python3
"""Check candidate SOTA-of-EDA baselines against local title/DOI/arXiv/baseline IDs."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError as exc:  # pragma: no cover
    raise SystemExit("PyYAML is required: python3 -m pip install pyyaml") from exc


def normalize_title(value: str | None) -> str:
    if not value:
        return ""
    value = value.lower()
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return " ".join(value.split())


def normalize_doi(value: str | None) -> str:
    if not value:
        return ""
    value = value.strip().lower()
    value = re.sub(r"^https?://(dx\.)?doi\.org/", "", value)
    value = re.sub(r"^(doi\s*:?\s*)", "", value)
    return value.strip()


def extract_arxiv(value: str | None) -> str:
    if not value:
        return ""
    value = value.strip()
    modern = r"[0-9]{4}\.[0-9]{4,5}(?:v\d+)?"
    old_style = r"[a-z-]+(?:\.[A-Z]{2})?/[0-9]{7}(?:v\d+)?"
    match = re.search(rf"arxiv\.org/(?:abs|pdf)/({modern}|{old_style})", value, re.I)
    if not match:
        match = re.search(rf"\b({modern}|{old_style})\b", value, re.I)
    if not match:
        return ""
    return re.sub(r"v\d+$", "", match.group(1), flags=re.I)


def topic_id_from_draft(data: Any) -> str:
    if not isinstance(data, dict):
        return ""
    candidate_topic = data.get("candidate_topic") or {}
    if isinstance(candidate_topic, dict):
        proposed_topic = candidate_topic.get("proposed_topic") or {}
        return (
            candidate_topic.get("topic_id")
            or (proposed_topic.get("topic_id") if isinstance(proposed_topic, dict) else "")
            or ""
        )
    return data.get("topic_id") or data.get("topic_id_hint") or ""


def read_yaml(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def iter_dicts(value: Any):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from iter_dicts(child)
    elif isinstance(value, list):
        for item in value:
            yield from iter_dicts(item)


def baseline_records_from_file(path: Path, accepted: bool):
    data = read_yaml(path)
    records = []

    if isinstance(data, dict) and isinstance(data.get("baselines"), list):
        topic_id = data.get("topic_id")
        for baseline in data["baselines"]:
            if isinstance(baseline, dict):
                records.append(record_from_baseline(baseline, path, topic_id, accepted))

    for item in iter_dicts(data):
        if "baseline_id" in item and "publication" in item:
            records.append(record_from_baseline(item, path, data.get("topic_id") or topic_id_from_draft(data), accepted))

    # Deduplicate records discovered through both paths.
    unique = []
    seen = set()
    for record in records:
        key = (record["path"], record.get("baseline_id"), record.get("title"))
        if key not in seen:
            seen.add(key)
            unique.append(record)
    return unique


def record_from_baseline(baseline: dict[str, Any], path: Path, topic_id: str | None, accepted: bool):
    publication = baseline.get("publication") or {}
    links = baseline.get("links") or {}
    arxiv = extract_arxiv(links.get("arxiv_url")) or extract_arxiv(links.get("pdf_url")) or extract_arxiv(links.get("paper_url"))
    title = publication.get("title") or baseline.get("display_name") or ""
    return {
        "path": str(path.resolve()),
        "accepted": accepted,
        "topic_id": topic_id or "",
        "baseline_id": baseline.get("baseline_id") or "",
        "title": title,
        "title_norm": normalize_title(title),
        "doi": normalize_doi(publication.get("doi")),
        "arxiv": arxiv,
    }


def load_records(repo: Path):
    records = []
    for path in sorted((repo / "data" / "topics").glob("*.yaml")):
        records.extend(baseline_records_from_file(path, accepted=True))
    for path in sorted((repo / "data" / "drafts").glob("*.yaml")):
        records.extend(baseline_records_from_file(path, accepted=False))
    return records


def candidate_from_args(args: argparse.Namespace):
    candidate = {
        "source_path": "",
        "baseline_id": args.baseline_id or "",
        "title": args.title or "",
        "title_norm": normalize_title(args.title),
        "doi": normalize_doi(args.doi),
        "arxiv": extract_arxiv(args.arxiv),
    }
    if args.candidate:
        candidate_path = Path(args.candidate).resolve()
        candidate["source_path"] = str(candidate_path)
        data = read_yaml(candidate_path)
        for item in iter_dicts(data):
            if "baseline_id" in item and "publication" in item:
                rec = record_from_baseline(item, candidate_path, topic_id_from_draft(data), accepted=False)
                for key in ("baseline_id", "title", "title_norm", "doi", "arxiv"):
                    candidate[key] = candidate.get(key) or rec.get(key) or ""
                break
    return candidate


def find_matches(candidate: dict[str, str], records: list[dict[str, Any]]):
    matches = []
    for record in records:
        if candidate.get("source_path") and candidate["source_path"] == record.get("path"):
            continue
        reasons = []
        if candidate.get("baseline_id") and candidate["baseline_id"] == record.get("baseline_id"):
            reasons.append("baseline_id")
        if candidate.get("doi") and candidate["doi"] == record.get("doi"):
            reasons.append("doi")
        if candidate.get("arxiv") and candidate["arxiv"] == record.get("arxiv"):
            reasons.append("arxiv")
        if candidate.get("title_norm") and candidate["title_norm"] == record.get("title_norm"):
            reasons.append("normalized_title")
        if reasons:
            matches.append({"reasons": reasons, "record": record})
    return matches


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=".", help="Repository root")
    parser.add_argument("--title", help="Candidate paper title")
    parser.add_argument("--doi", help="Candidate DOI")
    parser.add_argument("--arxiv", help="Candidate arXiv URL or ID")
    parser.add_argument("--baseline-id", help="Candidate baseline_id")
    parser.add_argument("--candidate", help="Candidate draft YAML to inspect")
    parser.add_argument("--json", action="store_true", help="Emit JSON")
    args = parser.parse_args()

    repo = Path(args.repo).resolve()
    records = load_records(repo)
    candidate = candidate_from_args(args)
    matches = find_matches(candidate, records)

    result = {"candidate": candidate, "matches": matches, "record_count": len(records)}
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(f"Loaded {len(records)} existing baseline records.")
        if not any(candidate.values()):
            print("No candidate identifiers provided; nothing to compare.")
        elif not matches:
            print("No title/DOI/arXiv/baseline_id duplicates found.")
        else:
            print(f"Found {len(matches)} possible duplicate(s):")
            for match in matches:
                record = match["record"]
                print(f"- {', '.join(match['reasons'])}: {record['title']} [{record['baseline_id']}] in {record['path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
