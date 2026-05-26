#!/usr/bin/env python3
"""Create a human-reviewable SOTA-of-EDA candidate baseline draft."""
from __future__ import annotations

import argparse
import re
from datetime import datetime, timezone
from pathlib import Path

try:
    import yaml
except ImportError as exc:  # pragma: no cover
    raise SystemExit("PyYAML is required: python3 -m pip install pyyaml") from exc


def kebab(value: str) -> str:
    value = value.lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-") or "candidate-baseline"


def has_proposed_topic_args(args: argparse.Namespace) -> bool:
    return any(
        [
            args.proposed_topic_id,
            args.proposed_parent_id,
            args.proposed_short_name,
            args.proposed_display_name,
            args.proposed_alias,
            args.proposed_description,
            args.proposed_review_trigger,
        ]
    )


def build_candidate_topic(args: argparse.Namespace) -> dict:
    if args.topic_id and has_proposed_topic_args(args):
        raise SystemExit("Use either --topic-id for an existing topic or --proposed-topic-* fields, not both.")

    if has_proposed_topic_args(args):
        topic_id = kebab(args.proposed_topic_id or args.proposed_display_name or args.proposed_short_name or args.title)
        proposed_topic: dict = {
            "topic_id": topic_id,
            **({"parent_id": args.proposed_parent_id} if args.proposed_parent_id else {}),
            "short_name": args.proposed_short_name or topic_id.replace("-", " ").title(),
            "display_name": args.proposed_display_name or args.proposed_short_name or topic_id.replace("-", " ").title(),
            **({"aliases": args.proposed_alias} if args.proposed_alias else {}),
            **({"description": args.proposed_description} if args.proposed_description else {}),
            **({"review_triggers": args.proposed_review_trigger} if args.proposed_review_trigger else {}),
        }
        return {
            "status": "proposed",
            "topic_id": topic_id,
            **({"notes": args.topic_notes} if args.topic_notes else {}),
            "proposed_topic": proposed_topic,
        }

    return {
        "topic_id": args.topic_id,
        "status": "existing" if args.topic_id else "proposed_or_unconfirmed",
        **({"notes": args.topic_notes} if args.topic_notes else {}),
    }


def build_draft(args: argparse.Namespace):
    baseline_id = kebab(args.baseline_id or args.short_name or args.title)
    short_name = args.short_name or baseline_id.replace("-", " ").title()
    display_name = args.display_name or args.title
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    links = {
        key: value
        for key, value in {
            "paper_url": args.paper_url,
            "pdf_url": args.pdf_url,
            "arxiv_url": args.arxiv_url,
            "repo_url": args.repo_url,
            "project_url": args.project_url,
        }.items()
        if value
    }
    publication: dict = {
        "title": args.title,
        "venue": args.venue,
        "year": args.year,
        **({"doi": args.doi} if args.doi else {}),
        **({"bibtex": args.bibtex} if args.bibtex else {}),
    }
    baseline: dict = {
        "baseline_id": baseline_id,
        "short_name": short_name,
        "display_name": display_name,
        "role": args.role,
        "nomination": args.nomination,
        "publication": publication,
        "links": links,
        **({"compare_when": args.compare_when} if args.compare_when else {}),
        **({"benchmark_scope": args.benchmark_scope} if args.benchmark_scope else {}),
        **({"metrics": args.metrics} if args.metrics else {}),
        "reproducibility": args.reproducibility,
        **({"caveats": args.caveats} if args.caveats else {}),
    }
    evidence_notes: dict = {
        "source_urls": args.source_url,
        "confidence": args.confidence,
        **({"sota_assessment": args.sota_assessment} if args.sota_assessment else {}),
        "unresolved_fields": args.unresolved,
    }
    result: dict = {
        "draft_kind": "sota_baseline_candidate",
        "created_at": now,
        "candidate_topic": build_candidate_topic(args),
        "baseline": baseline,
        "evidence_notes": evidence_notes,
    }
    if args.compared_baseline:
        result["compared_baselines_to_review"] = args.compared_baseline
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=".", help="Repository root")
    parser.add_argument("--baseline-id", help="Candidate baseline ID; defaults from title")
    parser.add_argument("--short-name", help="Short method name")
    parser.add_argument("--display-name", help="Display name; defaults to title")
    parser.add_argument("--title", required=True, help="Publication title")
    parser.add_argument("--venue", default="TODO", help="Venue")
    parser.add_argument("--year", type=int, default=datetime.now().year, help="Publication year")
    parser.add_argument("--doi", help="DOI")
    parser.add_argument("--bibtex", help="Verified BibTeX")
    parser.add_argument("--topic-id", help="Existing topic_id if confirmed")
    parser.add_argument("--topic-notes", help="Topic proposal/confirmation notes")
    parser.add_argument("--proposed-topic-id", help="New topic_id to propose")
    parser.add_argument("--proposed-parent-id", help="Parent topic_id for a proposed topic")
    parser.add_argument("--proposed-short-name", help="Short name for a proposed topic")
    parser.add_argument("--proposed-display-name", help="Display name for a proposed topic")
    parser.add_argument("--proposed-alias", action="append", default=[], help="Alias for a proposed topic; repeatable")
    parser.add_argument("--proposed-description", help="Description for a proposed topic")
    parser.add_argument("--proposed-review-trigger", action="append", default=[], help="Review trigger for a proposed topic; repeatable")
    parser.add_argument("--role", default="candidate_recent_baseline", choices=["canonical_baseline", "candidate_recent_baseline", "artifact_baseline", "historical_reference"])
    parser.add_argument("--nomination", default="community", choices=["maintainer", "community", "self_nominated"])
    parser.add_argument("--reproducibility", default="unknown", choices=["reproduced", "artifact_available", "paper_only", "unknown"])
    parser.add_argument("--paper-url")
    parser.add_argument("--pdf-url")
    parser.add_argument("--arxiv-url")
    parser.add_argument("--repo-url")
    parser.add_argument("--project-url")
    parser.add_argument("--compare-when", action="append", default=[])
    parser.add_argument("--benchmark-scope", action="append", default=[])
    parser.add_argument("--metrics", action="append", default=[])
    parser.add_argument("--caveats", action="append", default=[])
    parser.add_argument("--source-url", action="append", default=[])
    parser.add_argument("--compared-baseline", action="append", default=[])
    parser.add_argument("--unresolved", action="append", default=[])
    parser.add_argument("--sota-assessment")
    parser.add_argument("--confidence", default="medium")
    parser.add_argument("--dry-run", action="store_true", help="Print draft instead of writing file")
    args = parser.parse_args()

    draft = build_draft(args)
    output = yaml.safe_dump(draft, sort_keys=False, allow_unicode=False, width=1000)
    if args.dry_run:
        print(output)
        return 0

    repo = Path(args.repo).resolve()
    draft_dir = repo / "data" / "drafts"
    draft_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    path = draft_dir / f"{stamp}-{draft['baseline']['baseline_id']}.yaml"
    path.write_text(output, encoding="utf-8")
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
