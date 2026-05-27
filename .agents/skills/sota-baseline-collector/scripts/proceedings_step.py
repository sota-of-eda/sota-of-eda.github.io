#!/usr/bin/env python3
"""Single-step proceedings queue for SOTA-of-EDA draft collection."""
from __future__ import annotations

import argparse
import csv
import hashlib
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any, Iterable

import yaml

VALID = {"pending", "skip", "duplicate", "deferred", "draft"}
REPORT_FIELDS = [
    "item_id", "source_path", "decision", "title", "authors", "topic", "doi",
    "bibtex_status", "reason", "packet_path", "extract_path", "draft_path",
    "n_experiment_baselines",
]
ITEM_FIELDS = ["item_id", "source_path", "status", "packet_path", "extract_path", "draft_path"]
METADATA_FIELDS = [
    "item_id", "kind", "query", "name", "why", "evidence_location",
    "registry_match", "status",
]
REGISTRY_FIELDS = ["match_key", "baseline_id", "topic_id", "short_name", "display_name", "title", "doi"]
POLLUTION_RE = re.compile(r"\b(1st|2nd|3rd|University|School of|Department|Faculty|@|\.edu|\.com)\b", re.I)
SECTION_RE = re.compile(r"\b(Abstract|Experiment|Experimental|Evaluation|Results|Benchmark|Table|Fig\.?|Figure)\b", re.I)
ROLE_VALUES = {"proposed_method", "benchmark", "tool", "dataset", "unknown"}
EXPERIMENT_ROLE_VALUES = {"compared_method", "tool_flow", "benchmark", "ablation", "metric_reference"}
REQUEST_KIND_VALUES = {"candidate_paper", "experiment_baseline"}


def batch_paths(batch: Path) -> dict[str, Path]:
    return {
        "items": batch / "items.tsv",
        "report": batch / "report.tsv",
        "packets": batch / "packets",
        "extracts": batch / "extracts",
        "drafts": batch / "drafts",
        "metadata_requests": batch / "metadata_requests.tsv",
        "metadata_cache": batch / "metadata_cache.yaml",
        "registry_index": batch / "registry_index.tsv",
    }


def read_tsv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def write_tsv(path: Path, fields: list[str], rows: Iterable[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter="\t", extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in fields})


def norm(value: str) -> str:
    value = re.sub(r"\b(v|version)\s*\d+(?:\.\d+)*\b", " ", value.lower())
    return re.sub(r"[^a-z0-9]+", " ", value).strip()


def item_id(source: str, index: int) -> str:
    stem = re.sub(r"[^a-z0-9]+", "-", Path(source).stem.lower()).strip("-")[:32] or "paper"
    digest = hashlib.sha1(source.encode("utf-8")).hexdigest()[:8]
    return f"{index:04d}-{stem}-{digest}"


def init(args: argparse.Namespace) -> int:
    paths = batch_paths(args.batch)
    if paths["items"].exists() and not args.force:
        raise SystemExit(f"items.tsv exists; use --force to overwrite: {paths['items']}")
    sources = []
    for line in args.pdf_list.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            sources.append(line)
    rows = []
    for i, source in enumerate(sources, 1):
        rows.append({"item_id": item_id(source, i), "source_path": source, "status": "pending"})
    write_tsv(paths["items"], ITEM_FIELDS, rows)
    write_tsv(paths["report"], REPORT_FIELDS, [])
    write_tsv(paths["metadata_requests"], METADATA_FIELDS, [])
    build_registry_index(args.batch)
    print(f"initialized {len(rows)} items in {args.batch}")
    return 0


def next_item(args: argparse.Namespace) -> int:
    for row in read_tsv(batch_paths(args.batch)["items"]):
        if row.get("status") == "pending":
            print(f"{row['item_id']}\t{row['source_path']}")
            return 0
    print("NO_PENDING_ITEMS")
    return 0


def run_pdftotext(path: Path, first_pages_only: bool) -> str:
    if not shutil.which("pdftotext"):
        raise SystemExit("pdftotext not found; install poppler-utils or provide text files")
    cmd = ["pdftotext", "-layout"]
    if first_pages_only:
        cmd += ["-f", "1", "-l", "2"]
    cmd += [str(path), "-"]
    result = subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    return result.stdout.replace("\x01", " ")


def source_text(source: str, first_pages_only: bool) -> str:
    path = Path(source)
    if not path.exists():
        return f"SOURCE_NOT_LOCAL: {source}\nUse the official URL/listing manually; record only verified metadata."
    if path.suffix.lower() == ".pdf":
        return run_pdftotext(path, first_pages_only)
    return path.read_text(errors="ignore", encoding="utf-8")


def compact(text: str, limit: int) -> str:
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    return text if len(text) <= limit else text[: limit - 4].rstrip() + " ..."


def windows(text: str, limit: int = 5) -> list[str]:
    lines = text.splitlines()
    hits = [i for i, line in enumerate(lines) if SECTION_RE.search(line)]
    out = []
    for idx in hits[:limit]:
        start = max(0, idx - 4)
        end = min(len(lines), idx + 12)
        out.append(compact("\n".join(lines[start:end]), 1600))
    return out


def get_item(batch: Path, item: str) -> dict[str, str]:
    for row in read_tsv(batch_paths(batch)["items"]):
        if row.get("item_id") == item:
            return row
    raise SystemExit(f"unknown item_id: {item}")


def packet(args: argparse.Namespace) -> int:
    paths = batch_paths(args.batch)
    row = get_item(args.batch, args.id)
    source = row["source_path"]
    first = source_text(source, first_pages_only=True)
    full = source_text(source, first_pages_only=False)
    out = paths["packets"] / f"{args.id}.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    snippets = windows(full)
    body = [
        f"# Packet {args.id}",
        "", f"Source: `{source}`", "",
        "## Raw First Pages", "", "```text", compact(first, 7000), "```", "",
        "## Abstract / Experiment / Table Windows", "",
    ]
    if snippets:
        for i, snippet in enumerate(snippets, 1):
            body += [f"### Window {i}", "", "```text", snippet, "```", ""]
    else:
        body += ["No section windows found. Use raw first pages only.", ""]
    out.write_text("\n".join(body), encoding="utf-8")
    items = read_tsv(paths["items"])
    for item in items:
        if item.get("item_id") == args.id:
            item["packet_path"] = str(out)
    write_tsv(paths["items"], ITEM_FIELDS, items)
    print(out)
    return 0


def upsert_report(batch: Path, new: dict[str, str]) -> None:
    paths = batch_paths(batch)
    rows = read_tsv(paths["report"])
    replaced = False
    for i, row in enumerate(rows):
        if row.get("item_id") == new["item_id"]:
            rows[i] = {**row, **new}
            replaced = True
            break
    if not replaced:
        rows.append(new)
    write_tsv(paths["report"], REPORT_FIELDS, rows)


def load_extract(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    text = re.sub(r"^```(?:yaml|yml)?\s*", "", text.strip())
    text = re.sub(r"\s*```$", "", text.strip())
    data = yaml.safe_load(text) or {}
    if not isinstance(data, dict):
        raise SystemExit(f"extract is not a YAML mapping: {path}")
    return data


def as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def authors_text(value: Any) -> str:
    return "; ".join(str(v).strip() for v in as_list(value) if str(v).strip())


def validate_extract(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    decision = str(data.get("decision", "")).strip()
    if decision not in VALID - {"pending"}:
        errors.append(f"invalid decision: {decision}")
    title = str(data.get("title", "") or "").strip()
    if decision in {"draft", "deferred"} and not title:
        errors.append("title is required for draft/deferred")
    if title and POLLUTION_RE.search(title):
        errors.append(f"polluted title: {title}")
    candidate = data.get("candidate_baseline") or {}
    if candidate and not isinstance(candidate, dict):
        errors.append("candidate_baseline must be a mapping")
    if isinstance(candidate, dict):
        role = str(candidate.get("role", "unknown") or "unknown")
        if role not in ROLE_VALUES:
            errors.append(f"invalid candidate role: {role}")
    for i, baseline in enumerate(as_list(data.get("experiment_baselines")), 1):
        if not isinstance(baseline, dict):
            errors.append(f"experiment_baselines[{i}] must be a mapping")
            continue
        if not str(baseline.get("name", "") or "").strip():
            errors.append(f"experiment_baselines[{i}] missing name")
        if not str(baseline.get("evidence_location", "") or "").strip():
            errors.append(f"experiment_baselines[{i}] missing evidence_location")
        role = str(baseline.get("role", "compared_method") or "compared_method")
        if role not in EXPERIMENT_ROLE_VALUES:
            errors.append(f"experiment_baselines[{i}] invalid role: {role}")
    for i, req in enumerate(as_list(data.get("metadata_requests")), 1):
        if not isinstance(req, dict):
            errors.append(f"metadata_requests[{i}] must be a mapping")
            continue
        kind = str(req.get("kind", "") or "")
        if kind and kind not in REQUEST_KIND_VALUES:
            errors.append(f"metadata_requests[{i}] invalid kind: {kind}")
    return errors


def baseline_index_values(base: dict[str, Any], topic: str) -> dict[str, str]:
    pub = base.get("publication") or {}
    return {
        "baseline_id": str(base.get("baseline_id", "")),
        "topic_id": topic,
        "short_name": str(base.get("short_name", "")),
        "display_name": str(base.get("display_name", "")),
        "title": str(pub.get("title", "")),
        "doi": str(pub.get("doi", "")),
    }


def add_registry_value_rows(rows: list[dict[str, str]], values: dict[str, str]) -> None:
    keys = {norm(values[k]) for k in ["baseline_id", "short_name", "display_name", "title"] if values[k]}
    if values["doi"]:
        keys.add(norm(values["doi"]))
    for key in sorted(k for k in keys if k):
        rows.append({"match_key": key, **values})


def build_registry_rows() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for path in sorted(Path("data/topics").rglob("*.yaml")):
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        except Exception:
            continue
        if not isinstance(data, dict):
            continue
        if data.get("baseline_id"):
            add_registry_value_rows(rows, baseline_index_values(data, path.parent.name))
        topic = str(data.get("topic_id", ""))
        for base in data.get("baselines") or []:
            if isinstance(base, dict):
                add_registry_value_rows(rows, baseline_index_values(base, topic))
    return rows

def build_registry_index(batch: Path) -> list[dict[str, str]]:
    rows = build_registry_rows()
    write_tsv(batch_paths(batch)["registry_index"], REGISTRY_FIELDS, rows)
    return rows


def registry_lookup(batch: Path) -> dict[str, dict[str, str]]:
    path = batch_paths(batch)["registry_index"]
    rows = read_tsv(path) if path.exists() else build_registry_index(batch)
    return {row["match_key"]: row for row in rows if row.get("match_key")}


def match_registry(index: dict[str, dict[str, str]], name: str) -> dict[str, str] | None:
    key = norm(name)
    if not key:
        return None
    if key in index:
        return index[key]
    # Conservative alias: match prefix-stripped version for names like DREAMPlace 4.0.
    base_key = re.sub(r"\s+\d+(?:\s+\d+)*$", "", key).strip()
    return index.get(base_key)


def metadata_rows_from_extract(batch: Path, item_id_value: str, data: dict[str, Any]) -> list[dict[str, str]]:
    index = registry_lookup(batch)
    rows: list[dict[str, str]] = []
    for req in as_list(data.get("metadata_requests")):
        if not isinstance(req, dict):
            continue
        query = str(req.get("query", "") or "").strip()
        if not query:
            continue
        rows.append({
            "item_id": item_id_value,
            "kind": str(req.get("kind", "") or "candidate_paper"),
            "query": query,
            "name": str(req.get("name", "") or ""),
            "why": str(req.get("why", "") or ""),
            "evidence_location": "",
            "registry_match": "",
            "status": "requested",
        })
    for baseline in as_list(data.get("experiment_baselines")):
        if not isinstance(baseline, dict):
            continue
        name = str(baseline.get("name", "") or "").strip()
        if not name:
            continue
        match = match_registry(index, name)
        query = str(baseline.get("search_query_hint", "") or name).strip()
        if match:
            continue
        rows.append({
            "item_id": item_id_value,
            "kind": "experiment_baseline",
            "query": query,
            "name": name,
            "why": "unmatched experiment baseline needs metadata follow-up",
            "evidence_location": str(baseline.get("evidence_location", "") or ""),
            "registry_match": "",
            "status": "unresolved",
        })
    return rows


def rewrite_item(batch: Path, item_id_value: str, updates: dict[str, str]) -> None:
    items = read_tsv(batch_paths(batch)["items"])
    for item in items:
        if item.get("item_id") == item_id_value:
            item.update(updates)
    write_tsv(batch_paths(batch)["items"], ITEM_FIELDS, items)


def record(args: argparse.Namespace) -> int:
    if args.decision not in VALID - {"pending"}:
        raise SystemExit(f"invalid decision: {args.decision}")
    row = get_item(args.batch, args.id)
    packet_path = row.get("packet_path") or str(batch_paths(args.batch)["packets"] / f"{args.id}.md")
    if args.decision in {"draft", "deferred"} and not args.title:
        raise SystemExit("--title is required for draft/deferred")
    if args.decision == "draft" and (not args.topic or not args.reason):
        raise SystemExit("--topic and --reason are required for draft")
    if args.title and POLLUTION_RE.search(args.title):
        raise SystemExit("title looks polluted; record as deferred with a clean reason")
    report = {
        "item_id": args.id,
        "source_path": row["source_path"],
        "decision": args.decision,
        "title": args.title or "",
        "authors": args.authors or "",
        "topic": args.topic or "",
        "doi": args.doi or "",
        "bibtex_status": args.bibtex_status or "missing",
        "reason": args.reason or "",
        "packet_path": packet_path,
        "extract_path": row.get("extract_path", ""),
        "n_experiment_baselines": "0",
    }
    upsert_report(args.batch, report)
    rewrite_item(args.batch, args.id, {"status": args.decision})
    print(f"recorded {args.id}: {args.decision}")
    return 0


def attach_extract(args: argparse.Namespace) -> int:
    paths = batch_paths(args.batch)
    row = get_item(args.batch, args.id)
    data = load_extract(args.extract)
    errors = validate_extract(data)
    if errors:
        raise SystemExit("invalid extract:\n" + "\n".join(f"- {e}" for e in errors))
    out = paths["extracts"] / f"{args.id}.yaml"
    out.parent.mkdir(parents=True, exist_ok=True)
    if out.exists() and out.resolve() != args.extract.resolve() and not args.force:
        raise SystemExit(f"extract exists; use --force to overwrite: {out}")
    if out.resolve() != args.extract.resolve():
        shutil.copyfile(args.extract, out)
    exp_count = len(as_list(data.get("experiment_baselines")))
    decision = str(data.get("decision", "deferred") or "deferred")
    topic = str(data.get("topic_hint", "") or "")
    report = {
        "item_id": args.id,
        "source_path": row["source_path"],
        "decision": decision,
        "title": str(data.get("title", "") or ""),
        "authors": authors_text(data.get("authors")),
        "topic": topic,
        "doi": str(data.get("doi", "") or ""),
        "bibtex_status": "missing",
        "reason": str(data.get("reason", "") or ""),
        "packet_path": row.get("packet_path") or str(paths["packets"] / f"{args.id}.md"),
        "extract_path": str(out),
        "n_experiment_baselines": str(exp_count),
    }
    upsert_report(args.batch, report)
    rewrite_item(args.batch, args.id, {"status": decision, "extract_path": str(out)})
    existing = [r for r in read_tsv(paths["metadata_requests"]) if r.get("item_id") != args.id]
    write_tsv(paths["metadata_requests"], METADATA_FIELDS, existing + metadata_rows_from_extract(args.batch, args.id, data))
    print(out)
    return 0


def slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")[:80] or "candidate"


def enrich_experiment_baselines(batch: Path, baselines: list[Any]) -> list[dict[str, str]]:
    index = registry_lookup(batch)
    out = []
    for baseline in baselines:
        if not isinstance(baseline, dict):
            continue
        name = str(baseline.get("name", "") or "").strip()
        match = match_registry(index, name)
        item = {
            "name": name,
            "role": str(baseline.get("role", "compared_method") or "compared_method"),
            "evidence_location": str(baseline.get("evidence_location", "") or ""),
            "evidence_text_short": str(baseline.get("evidence_text_short", "") or ""),
            "benchmark_context": str(baseline.get("benchmark_context", "") or ""),
            "metric_context": str(baseline.get("metric_context", "") or ""),
            "search_query_hint": str(baseline.get("search_query_hint", "") or ""),
            "verification_status": "matched_existing" if match else "needs_followup",
            "matched_registry": f"{match['topic_id']}/{match['baseline_id']}" if match else "",
        }
        out.append(item)
    return out


def draft(args: argparse.Namespace) -> int:
    paths = batch_paths(args.batch)
    rows = {row["item_id"]: row for row in read_tsv(paths["report"])}
    row = rows.get(args.id)
    if not row:
        raise SystemExit(f"no report row for {args.id}")
    if row.get("decision") != "draft":
        raise SystemExit(f"item is not marked draft: {row.get('decision')}")
    if not row.get("title") or not row.get("topic"):
        raise SystemExit("draft rows need title and topic")
    if not row.get("extract_path"):
        raise SystemExit("draft rows need extract_path; run attach-extract")
    extract = load_extract(Path(row["extract_path"]))
    candidate = extract.get("candidate_baseline") or {}
    if not isinstance(candidate, dict):
        candidate = {}
    authors = [str(a).strip() for a in as_list(extract.get("authors")) if str(a).strip()]
    content = {
        "draft_kind": "proceedings_candidate",
        "item_id": args.id,
        "source_path": row["source_path"],
        "candidate_topic": {"topic_id": row["topic"]},
        "candidate_baseline": {
            "baseline_id": slug(str(candidate.get("name") or row["title"])),
            "title": row["title"],
            "authors": authors,
            "role": str(candidate.get("role", "unknown") or "unknown"),
            "doi": row.get("doi", ""),
            "bibtex_status": row.get("bibtex_status", "missing"),
        },
        "experiment_baselines": enrich_experiment_baselines(args.batch, as_list(extract.get("experiment_baselines"))),
        "metadata_requests": metadata_rows_from_extract(args.batch, args.id, extract),
        "evidence_notes": {
            "packet": row.get("packet_path", ""),
            "extract": row.get("extract_path", ""),
            "reason": row.get("reason", ""),
            "merge_note": "Draft only. Codex or human must verify BibTeX, topic, metadata, and duplicate status before accepted merge.",
        },
    }
    out = paths["drafts"] / f"{args.id}.yaml"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(yaml.safe_dump(content, sort_keys=False, allow_unicode=False), encoding="utf-8")
    report_rows = read_tsv(paths["report"])
    for item in report_rows:
        if item.get("item_id") == args.id:
            item["draft_path"] = str(out)
    write_tsv(paths["report"], REPORT_FIELDS, report_rows)
    rewrite_item(args.batch, args.id, {"draft_path": str(out)})
    print(out)
    return 0


def audit(args: argparse.Namespace) -> int:
    paths = batch_paths(args.batch)
    build_registry_index(args.batch)
    items = read_tsv(paths["items"])
    reports = read_tsv(paths["report"])
    errors: list[str] = []
    seen_titles: dict[str, str] = {}
    seen_dois: dict[str, str] = {}
    report_by_id = {row.get("item_id"): row for row in reports}
    for item in items:
        status = item.get("status", "")
        if status not in VALID:
            errors.append(f"{item.get('item_id')}: invalid status {status}")
        if status != "pending" and item.get("item_id") not in report_by_id:
            errors.append(f"{item.get('item_id')}: missing report row")
    for row in reports:
        item = row.get("item_id", "")
        title = row.get("title", "")
        if title and POLLUTION_RE.search(title):
            errors.append(f"{item}: polluted title: {title}")
        key = norm(title)
        if key:
            if key in seen_titles:
                errors.append(f"{item}: duplicate report title with {seen_titles[key]}")
            seen_titles[key] = item
        doi = row.get("doi", "").lower().strip()
        if doi:
            if doi in seen_dois:
                errors.append(f"{item}: duplicate report DOI with {seen_dois[doi]}")
            seen_dois[doi] = item
        if row.get("decision") == "draft" and not row.get("extract_path"):
            errors.append(f"{item}: draft decision but missing extract_path")
        if row.get("extract_path") and not Path(row["extract_path"]).exists():
            errors.append(f"{item}: extract_path does not exist")
        if row.get("decision") == "draft" and not row.get("draft_path"):
            errors.append(f"{item}: draft decision but missing draft_path; run draft")
        if row.get("decision") == "draft" and row.get("draft_path") and not Path(row["draft_path"]).exists():
            errors.append(f"{item}: draft_path does not exist")
        if row.get("extract_path") and Path(row["extract_path"]).exists():
            data = load_extract(Path(row["extract_path"]))
            for err in validate_extract(data):
                errors.append(f"{item}: {err}")
            for baseline in as_list(data.get("experiment_baselines")):
                if isinstance(baseline, dict):
                    if not match_registry(registry_lookup(args.batch), str(baseline.get("name", "") or "")) and not str(baseline.get("search_query_hint", "") or ""):
                        errors.append(f"{item}: unmatched experiment baseline lacks search_query_hint: {baseline.get('name', '')}")
    print(f"items={len(items)} reports={len(reports)} errors={len(errors)}")
    for err in errors:
        print(f"ERROR: {err}")
    return 1 if errors else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("init")
    p.add_argument("--batch", type=Path, required=True)
    p.add_argument("--pdf-list", type=Path, required=True)
    p.add_argument("--force", action="store_true")
    p.set_defaults(func=init)
    p = sub.add_parser("next")
    p.add_argument("--batch", type=Path, required=True)
    p.set_defaults(func=next_item)
    p = sub.add_parser("packet")
    p.add_argument("--batch", type=Path, required=True)
    p.add_argument("--id", required=True)
    p.set_defaults(func=packet)
    p = sub.add_parser("record")
    p.add_argument("--batch", type=Path, required=True)
    p.add_argument("--id", required=True)
    p.add_argument("--decision", required=True)
    p.add_argument("--title", default="")
    p.add_argument("--authors", default="")
    p.add_argument("--topic", default="")
    p.add_argument("--doi", default="")
    p.add_argument("--bibtex-status", default="missing", choices=["verified", "provisional", "missing"])
    p.add_argument("--reason", default="")
    p.set_defaults(func=record)
    p = sub.add_parser("attach-extract")
    p.add_argument("--batch", type=Path, required=True)
    p.add_argument("--id", required=True)
    p.add_argument("--extract", type=Path, required=True)
    p.add_argument("--force", action="store_true")
    p.set_defaults(func=attach_extract)
    p = sub.add_parser("draft")
    p.add_argument("--batch", type=Path, required=True)
    p.add_argument("--id", required=True)
    p.set_defaults(func=draft)
    p = sub.add_parser("audit")
    p.add_argument("--batch", type=Path, required=True)
    p.set_defaults(func=audit)
    args = parser.parse_args()
    args.batch.mkdir(parents=True, exist_ok=True)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
