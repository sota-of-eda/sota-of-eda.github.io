---
name: proceedings-extractor
description: Use when extracting one SOTA-of-EDA proceedings packet or PDF into minimal draft-only YAML for a higher-level Codex reviewer.
---

# Proceedings Extractor

Read one packet/PDF. Fill the template. Return YAML only.

Template:

```bash
python3 .claude/skills/proceedings-extractor/scripts/review_template.py --id <item_id> --source <packet-or-pdf>
```

Rules:

- Do not write registry files.
- Do not invent DOI/BibTeX, metrics, benchmarks, or comparisons.
- If title/authors are polluted by affiliations, emails, session labels, or OCR fragments, use `decision: deferred`.
- `experiment_baselines` must come only from Experiment/Evaluation/Results/Table/Figure evidence.
- Do not use Abstract, Introduction, Background, or Related Work as experiment-baseline evidence.
- Do not output final registry fields like `compare_when`, `benchmark_scope`, `metrics`, `bibtex`, or `caveats`.
- Unknown fields stay empty and should appear in `needs`.
