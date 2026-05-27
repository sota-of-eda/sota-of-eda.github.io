---
name: sota-baseline-collector
description: Use when processing SOTA-of-EDA baseline candidates from paper titles, URLs, official proceedings, local PDFs, or Claude extracts, especially when drafts and experiment-baseline evidence must stay reviewable before registry merge.
---

# SOTA Baseline Collector

Goal: Codex is the conversational entrypoint and reviewer/orchestrator. The user tells Codex what proceedings/list/PDF paths to process; Codex then uses scripts and Claude internally, one source path at a time, without polluting accepted `data/topics/`.

## Hard Rules

- Do not write `data/topics/` unless the user explicitly asks to merge confirmed drafts.
- Work on one full source path at a time; never classify a whole proceedings batch in one prompt.
- Claude reads only `packets/<id>.md` and returns YAML; Codex verifies topic, metadata, duplicates, and merge readiness.
- Never invent BibTeX. DOI/DBLP/arXiv/publisher BibTeX is `verified`; official-PDF/listing-only metadata is `provisional` and stays draft-only by default.
- Experiment baselines must come from Experiment/Evaluation/Results/Table/Figure evidence, not related work.
- Fast-match experiment baselines against the accepted registry before treating them as new follow-up candidates.
- If title contains authors, affiliations, emails, session labels, or truncated fragments, mark `deferred` instead of guessing.
- Standard-cell, cell layout, transistor-level placement/routing, and cell-library work are layout/cell topics, not logic synthesis.

## Required Loop

User-facing flow: receive a proceedings/list/PDF request, create or reuse a batch, then call the commands below internally while reporting only concise progress and blockers.

Use one batch directory, e.g. `data/drafts/batches/<batch-id>/`.

```bash
python3 .agents/skills/sota-baseline-collector/scripts/proceedings_step.py init --batch <batch-dir> --pdf-list <paths.txt>
python3 scripts/proceedings_orchestrator.py run-one --batch <batch-dir>
python3 scripts/proceedings_orchestrator.py audit --batch <batch-dir>
```

Manual fallback for one item:

```bash
python3 .agents/skills/sota-baseline-collector/scripts/proceedings_step.py next --batch <batch-dir>
python3 .agents/skills/sota-baseline-collector/scripts/proceedings_step.py packet --batch <batch-dir> --id <item_id>
# Run Claude or manually create extracts/<item_id>.yaml from the packet.
python3 .agents/skills/sota-baseline-collector/scripts/proceedings_step.py attach-extract --batch <batch-dir> --id <item_id> --extract <extract.yaml>
python3 .agents/skills/sota-baseline-collector/scripts/proceedings_step.py draft --batch <batch-dir> --id <item_id>
python3 .agents/skills/sota-baseline-collector/scripts/proceedings_step.py audit --batch <batch-dir>
```

## Claude Extract Contract

Claude's `.claude/skills/proceedings-extractor` skill should output only:

- `decision`: `skip`, `duplicate`, `deferred`, or `draft`.
- clean `title`, `authors`, `topic_hint`, and `reason`.
- `candidate_baseline`: the paper's own method/tool/benchmark.
- `experiment_baselines`: methods/tools/benchmarks/ablations explicitly used in experiments.
- `metadata_requests`: query hints only; Claude does not verify DOI/BibTeX.

## Outputs

- `items.tsv`: queue; one source path per row.
- `packets/<id>.md`: raw first page plus compact abstract/experiment/table snippets.
- `extracts/<id>.yaml`: Claude/manual extraction; still untrusted.
- `registry_index.tsv`: generated accepted-baseline index for quick duplicate checks.
- `metadata_requests.tsv`: unresolved metadata and unmatched experiment baselines for Codex follow-up.
- `report.tsv`: main review surface for Codex/human.
- `drafts/<id>.yaml`: reviewable draft only; never accepted data.

## Decisions

- `skip`: not a concrete EDA/VLSI-CAD method, dataset, tool, or benchmark.
- `duplicate`: same normalized title, DOI, arXiv, or accepted-baseline match already represents the item.
- `deferred`: plausible EDA, but title/authors/topic/metadata/evidence is not clean enough.
- `draft`: clean candidate with packet evidence, topic hint, experiment-baseline evidence, and metadata requests if needed.

## Final Checks

```bash
python3 scripts/proceedings_orchestrator.py audit --batch <batch-dir>
python3 -m py_compile .agents/skills/sota-baseline-collector/scripts/proceedings_step.py
python3 -m py_compile scripts/proceedings_orchestrator.py
npm run validate
git diff --check
```

Report counts from `report.tsv`; do not claim venue completion unless every row is non-pending and Codex/human review has accepted the relevant drafts.
