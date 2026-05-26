#!/usr/bin/env python3
"""Shared helpers for SOTA-of-EDA unified batch scripts."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Iterable

try:
    import yaml
except ImportError as exc:
    raise SystemExit("PyYAML is required: python3 -m pip install pyyaml") from exc

EDA_TERMS = {
    "eda", "design automation", "synthesis", "placement", "routing", "timing", "sta",
    "verification", "formal", "rtl", "verilog", "hls", "logic", "layout", "drc", "lvs",
    "netlist", "parasitic", "extraction", "power", "ir drop", "pdn", "thermal", "em",
    "lithography", "mask", "opc", "ilt", "testing", "dft", "fault", "floorplan",
    "analog", "circuit simulation", "spice", "cell", "standard cell", "fpga", "mapping",
    "technology mapping", "clock tree", "cts", "assertion", "testbench", "router", "placer",
}
NON_EDA_TERMS = {
    "accelerator", "inference", "training", "llm inference", "gemm", "sensor", "battery",
    "solar", "wearable", "robot", "autonomous", "gpu kernel", "device material",
}
SECTION_PATTERNS = {
    "abstract": re.compile(r"^\s*(?:abstract|summary)\b", re.I),
    "introduction": re.compile(r"^\s*(?:\d+\s*)?(?:introduction|intro)\b", re.I),
    "evaluation": re.compile(r"^\s*(?:\d+(?:\.\d+)*\s*)?(?:evaluation|experimental evaluation|experiments?|results?|case studies?)\b", re.I),
    "conclusion": re.compile(r"^\s*(?:\d+(?:\.\d+)*\s*)?(?:conclusion|conclusions)\b", re.I),
}
WINDOW_PATTERNS = {
    "experiment": re.compile(r"\b(experiment|evaluation|result|benchmark|baseline|comparison|compare|speedup|runtime|quality|qor)\b", re.I),
    "table": re.compile(r"\b(table|fig\.?|figure)\s*\d+", re.I),
}


def read_yaml(path: Path) -> Any:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def write_yaml(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=False, width=1000), encoding="utf-8")


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=True, sort_keys=True) + "\n")


def compact_text(value: str, max_chars: int) -> str:
    value = value.replace("\x01", " ")
    value = re.sub(r"[ \t]+", " ", value)
    value = re.sub(r"\n{3,}", "\n\n", value).strip()
    if len(value) <= max_chars:
        return value
    return value[: max_chars - 3].rstrip() + "..."


def normalize_title(value: str | None) -> str:
    if not value:
        return ""
    value = value.lower().replace("\x01", " ")
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return " ".join(value.split())


def kebab(value: str | None) -> str:
    return re.sub(r"\s+", "-", normalize_title(value)).strip("-") or "candidate"


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
    modern = r"[0-9]{4}\.[0-9]{4,5}(?:v\d+)?"
    old_style = r"[a-z-]+(?:\.[A-Z]{2})?/[0-9]{7}(?:v\d+)?"
    match = re.search(rf"arxiv\.org/(?:abs|pdf)/({modern}|{old_style})", value, re.I)
    if not match:
        match = re.search(rf"\b({modern}|{old_style})\b", value, re.I)
    return re.sub(r"v\d+$", "", match.group(1), flags=re.I) if match else ""


def iter_dicts(value: Any):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from iter_dicts(child)
    elif isinstance(value, list):
        for item in value:
            yield from iter_dicts(item)


def record_from_baseline(baseline: dict[str, Any], path: Path, accepted: bool) -> dict[str, Any]:
    pub = baseline.get("publication") or {}
    links = baseline.get("links") or {}
    title = pub.get("title") or baseline.get("display_name") or ""
    arxiv = extract_arxiv(links.get("arxiv_url")) or extract_arxiv(links.get("paper_url")) or extract_arxiv(links.get("pdf_url"))
    return {
        "path": str(path),
        "accepted": accepted,
        "baseline_id": baseline.get("baseline_id") or "",
        "title": title,
        "title_norm": normalize_title(title),
        "doi": normalize_doi(pub.get("doi")),
        "arxiv": arxiv,
    }


def registry_records(repo: Path, include_root_drafts: bool = True) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for path in sorted((repo / "data" / "topics").rglob("*.yaml")):
        try:
            data = read_yaml(path)
        except Exception:
            continue
        for item in iter_dicts(data):
            if isinstance(item, dict) and "baseline_id" in item and "publication" in item:
                records.append(record_from_baseline(item, path, accepted=True))
    if include_root_drafts:
        for path in sorted((repo / "data" / "drafts").glob("*.yaml")):
            try:
                data = read_yaml(path)
            except Exception:
                continue
            for item in iter_dicts(data):
                if isinstance(item, dict) and "baseline_id" in item and "publication" in item:
                    records.append(record_from_baseline(item, path, accepted=False))
    return records


def load_index(batch_dir: Path) -> list[dict[str, Any]]:
    path = batch_dir / "index" / "paper_index.yaml"
    if not path.exists():
        return []
    data = read_yaml(path)
    return data.get("papers", []) if isinstance(data, dict) else (data or [])


def load_triage(batch_dir: Path) -> list[dict[str, Any]]:
    path = batch_dir / "triage" / "triage.yaml"
    if not path.exists():
        return []
    data = read_yaml(path)
    return data.get("items", []) if isinstance(data, dict) else (data or [])


def infer_method(title: str) -> tuple[str, str]:
    title = title.strip(" :-\n\t")
    acronym = ""
    if ":" in title:
        left = title.split(":", 1)[0].strip()
        if 2 <= len(left) <= 32 and len(left.split()) <= 4:
            acronym = left
    if not acronym:
        match = re.search(r"\b([A-Z][A-Za-z0-9-]{2,18})\b", title)
        if match:
            acronym = match.group(1)
    method = acronym or (title.split()[0] if title.split() else "")
    return method, acronym


def topic_hint(text: str) -> str:
    t = text.lower()
    checks = [
        ("routing", ["routing", "router", "wirelength"]),
        ("placement", ["placement", "placer", "floorplan"]),
        ("timing", ["timing", "sta", "delay"]),
        ("logic-synthesis", ["logic synthesis", "technology mapping", "boolean", "aig"]),
        ("circuit-verification", ["verification", "formal", "assertion", "glitch", "security"]),
        ("testing", ["test pattern", "fault", "dft", "diagnosis"]),
        ("analog-layout-synthesis", ["analog", "transistor", "cell layout", "layout generation"]),
        ("high-level-synthesis", ["hls", "high-level synthesis"]),
        ("mask-optimization", ["lithography", "mask", "opc", "ilt", "hotspot"]),
        ("dataset-and-tools", ["benchmark", "dataset", "open-source", "tool"]),
    ]
    for topic, needles in checks:
        if any(n in t for n in needles):
            return topic
    return "unclassified"


def eda_score(text: str) -> tuple[int, list[str], list[str]]:
    t = text.lower()
    eda = sorted({term for term in EDA_TERMS if term in t})
    non = sorted({term for term in NON_EDA_TERMS if term in t})
    return len(eda) * 2 - len(non), eda[:8], non[:8]
