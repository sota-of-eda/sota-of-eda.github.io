# Registry Semantics

Use this reference when preparing SOTA-of-EDA candidate drafts.

## Topic Model

- Each topic has its own folder under `data/topics/`, nested inside its parent's folder.
- Topic YAML lives at `data/topics/<topic_id>/<topic_id>.yaml` (root topics) or `data/topics/<parent_id>/<topic_id>/<topic_id>.yaml` (nested topics).
- Child topic folders are nested inside parent topic folders, mirroring the `parent_id` tree.
- Baselines are separate YAML files in the same folder as their topic: `data/topics/<topic_id>/<baseline_id>.yaml`.
- `topic_id` must match the filename and folder name; it is an internal stable key.
- `parent_id` defines the topic tree and determines the folder nesting.
- `display_order` is UI ordering only; it is not a rank or importance score.
- `review_triggers` are declared in the topic YAML.
- Parent topics may aggregate descendants in the UI, but aggregation does not broaden applicability.

## Baseline Placement

Attach a baseline to the narrowest topic justified by the paper's claim, benchmark scope, and caveats.

Prefer existing topics before proposing a new one. To propose a new topic, include:

- `topic_id` in lowercase kebab-case.
- `parent_id` if it fits under an existing topic.
- `short_name`, `display_name`, `aliases`, `description`.
- `review_triggers` based on claim language in the paper intro/abstract/experiments.
- `baselines: []` until an accepted baseline is merged.

## Baseline Fields

Accepted baseline snippets must match `data/schema/topic.schema.json`:

- `baseline_id`, `short_name`, `display_name`.
- `role`: `canonical_baseline`, `candidate_recent_baseline`, `artifact_baseline`, or `historical_reference`.
- `nomination`: usually `community` unless the user says otherwise.
- `publication`: `title`, `venue`, `year`, optional `doi`, and full `bibtex`.
- `links`: optional `paper_url`, `pdf_url`, `arxiv_url`, `repo_url`, `project_url`.
- `compare_when`, `benchmark_scope`, `metrics`, `reproducibility`, `caveats`.

## SOTA Assessment

A paper's compared methods are not automatically accepted, but they are strong candidates for same-or-near-topic baseline review. Evaluate:

- Whether the compared method is in the same task setting or only adjacent.
- Whether benchmarks and metrics overlap.
- Whether the method is canonical, recent, artifact-backed, or only historical context.
- Whether the new paper itself should be added as a candidate recent baseline.
- What caveats limit applicability.

## Draft Discipline

Drafts in `data/drafts/` are not accepted registry entries. They are review artifacts and should be deleted after the human accepts, merges, or rejects them.
