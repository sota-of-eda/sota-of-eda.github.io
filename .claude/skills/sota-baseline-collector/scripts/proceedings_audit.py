#!/usr/bin/env python3
"""Deterministic batch audit for unified SOTA-of-EDA workflow."""
from __future__ import annotations

import argparse
import re
from pathlib import Path
from proceedings_common import iter_dicts, load_triage, normalize_doi, normalize_title, read_yaml, registry_records, write_yaml

TODO_RE = re.compile(r"\b(TODO|TBD|PLACEHOLDER)\b", re.I)
DOI_RE = re.compile(r"^10\.\d{4,9}/\S+$", re.I)


def audit_draft(path: Path, records: list[dict]) -> list[dict]:
    findings = []
    try:
        data = read_yaml(path)
    except Exception as exc:
        return [{"severity": "error", "path": str(path), "message": f"YAML parse failed: {exc}"}]
    text = path.read_text(encoding="utf-8")
    if TODO_RE.search(text):
        findings.append({"severity": "error", "path": str(path), "message": "TODO/TBD/placeholder text present"})
    for item in iter_dicts(data):
        if isinstance(item, dict) and "baseline_id" in item and "publication" in item:
            pub = item.get("publication") or {}
            for field in ["baseline_id", "short_name", "display_name", "compare_when", "benchmark_scope", "metrics", "caveats"]:
                if not item.get(field):
                    findings.append({"severity": "error", "path": str(path), "field": field, "message": "missing required baseline field"})
            if not pub.get("bibtex"):
                findings.append({"severity": "error", "path": str(path), "field": "publication.bibtex", "message": "missing BibTeX"})
            doi = normalize_doi(pub.get("doi"))
            if doi and not DOI_RE.match(doi):
                findings.append({"severity": "warning", "path": str(path), "field": "publication.doi", "message": f"suspicious DOI {doi}"})
            norm = normalize_title(pub.get("title"))
            for rec in records:
                if rec.get("accepted") and norm and norm == rec.get("title_norm"):
                    findings.append({"severity": "error", "path": str(path), "message": f"accepted-registry duplicate title: {rec.get('path')}"})
    return findings


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--repo", type=Path, default=Path("."))
    ap.add_argument("--batch-dir", type=Path, required=True)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    records = registry_records(args.repo.resolve())
    findings = []
    drafts = sorted((args.repo / "data" / "drafts").glob("*.yaml"))
    for draft in drafts:
        findings.extend(audit_draft(draft, records))
    triage = load_triage(args.batch_dir)
    if not triage:
        findings.append({"severity": "warning", "path": str(args.batch_dir), "message": "no triage.yaml found; run proceedings_triage.py first"})
    errors = sum(1 for f in findings if f["severity"] == "error")
    warnings = sum(1 for f in findings if f["severity"] == "warning")
    result = {"status": "audit_passed" if errors == 0 else "audit_failed", "errors": errors, "warnings": warnings, "drafts_checked": len(drafts), "triage_items": len(triage), "findings": findings}
    if args.dry_run:
        print(f"status={result['status']} errors={errors} warnings={warnings} drafts={len(drafts)} triage_items={len(triage)}")
        for f in findings[:10]:
            print(f"- {f['severity']} {f.get('path','')}: {f.get('message','')}")
        return 0 if errors == 0 else 1
    out = args.batch_dir / "audit"
    write_yaml(out / "batch_audit.yaml", result)
    md = ["# Batch Audit", "", f"status: `{result['status']}`", f"errors: {errors}", f"warnings: {warnings}", ""]
    for f in findings[:50]:
        md.append(f"- {f['severity']}: `{f.get('path','')}` {f.get('message','')}")
    (out / "batch_audit.md").write_text("\n".join(md), encoding="utf-8")
    print(out / "batch_audit.yaml")
    return 0 if errors == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
