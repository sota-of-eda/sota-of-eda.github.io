---
name: sota-baseline-collector
description: Use when processing SOTA-of-EDA baseline candidates from paper titles, URLs, official proceedings, local PDFs, or Claude extracts, especially when drafts, topic creation, topic merge/rearrange, and experiment-baseline evidence must stay reviewable before registry merge.
---

# SOTA Baseline Collector

Keep this workflow small. Codex coordinates; Claude Code reads papers and fills one minimal template; Codex reviews before merge.

## Rules

- Never write `data/topics/` unless the user explicitly asks to merge.
- Process one PDF/packet at a time; avoid venue-wide giant prompts.
- For hard PDF reading or YAML editing, call Claude Code directly and give it the template script.
- First-pass YAML is only a review note, not registry data.
- Do not invent DOI, BibTeX, metrics, benchmarks, or comparisons.
- Experiment baselines must be from Experiment/Evaluation/Results/Table/Figure evidence only.
- Do not output registry-shaped empty stubs such as empty `compare_when`, `benchmark_scope`, or `metrics`.
- Cell/standard-cell/transistor-level work belongs to layout/cell topics, not logic synthesis.
- New topics are allowed only after checking existing `data/topics/**/<topic>.yaml`; otherwise defer as `topic_review`.
- Before merging accepted YAML, run the topic gate: existing-topic fit, new-topic need, and sibling/child fanout.

## Minimal Loop

```bash
python3 .agents/skills/sota-baseline-collector/scripts/proceedings_step.py init --batch <batch-dir> --pdf-list <paths.txt>
python3 scripts/proceedings_orchestrator.py run-one --batch <batch-dir>
python3 scripts/proceedings_orchestrator.py audit --batch <batch-dir>
```

Repeat `run-one` until there are no `pending` rows, then stop. Do not merge by default.

## Claude Code Handoff

For each difficult item:

```bash
python3 .agents/skills/sota-baseline-collector/scripts/proceedings_step.py packet --batch <batch-dir> --id <item_id>
python3 .claude/skills/proceedings-extractor/scripts/review_template.py --id <item_id> --source <packet-or-pdf>
```

Tell Claude Code: read only this packet/PDF, fill the template, return YAML only. Unknown fields stay empty and must be listed under `needs`.

## Codex Review

Codex accepts a YAML for the next step only if it has clean title/authors, a concrete candidate method/tool/benchmark, a plausible existing `topic_id`, and useful experiment evidence or an explicit `needs: experiment_review` item.

Defer outputs with polluted titles, uncertain topics, related-work-only comparisons, generic baselines, or mostly-empty scaffolding.

## Topic Gate

Use this only after extraction/formalization, never inside Claude's paper-reading prompt.

- Prefer an existing topic when it accurately describes the comparison task.
- Propose a new topic when at least two papers need the same missing task label, or one paper is clearly outside every existing topic.
- If a parent would exceed sibling/child limits, stop adding flat siblings; aggregate related siblings under an intermediate topic, then reclassify.
- Load `references/topic-taxonomy-gate.md` when adding topics, moving topic parents, or resolving `npm run check:siblings`.

## Checks

```bash
python3 scripts/proceedings_orchestrator.py audit --batch <batch-dir>
python3 -m py_compile .agents/skills/sota-baseline-collector/scripts/proceedings_step.py scripts/proceedings_orchestrator.py .claude/skills/proceedings-extractor/scripts/review_template.py
npm run validate
npm run check:siblings
git diff --check
```
