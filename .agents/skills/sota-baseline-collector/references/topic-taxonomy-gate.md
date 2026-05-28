# Topic Taxonomy Gate

Use this only when Codex is reviewing or merging, not while Claude is extracting a paper.

## Existing vs New Topic

1. Search current topics first:
   - `find data/topics -name '*.yaml'`
   - inspect the nearest topic YAML for `description`, `aliases`, and `review_triggers`.
2. Reuse an existing topic when the paper's experiment task fits its review triggers.
3. Propose a new topic when:
   - no existing topic describes the task, or
   - forcing the paper into a parent topic would hide an important EDA subproblem, or
   - multiple papers share the same missing task label.
4. Defer as `topic_review` when only the title suggests a topic and the experiment section is unclear.

## New Topic YAML

Create a topic file only during accepted merge, not during first-pass extraction.

Required shape:

```yaml
topic_id: lower-kebab-id
parent_id: existing-parent-topic
short_name: Short Label
display_name: Clear Human Topic Name
aliases: []
description: One sentence describing the EDA task boundary.
review_triggers:
- paper claims this task or evaluates its task-specific metrics
```

Then place baselines as sibling YAML files under that topic directory.

## Rearrange / Merge Gate

Run `npm run check:siblings` before and after accepted merges.

Current limits are enforced by `scripts/check-sibling-count.mjs`:

- More than 6 direct siblings under one parent: consider aggregation.
- More than 10 direct children under one topic: introduce subcategories.
- Critical overflow means do not keep adding flat topics.

If overflow happens:

1. List the crowded siblings and group them by EDA task, not by venue or model family.
2. Create one or more intermediate topics with clear boundaries.
3. Move existing topic files by changing `parent_id` and directory path together.
4. Move baseline YAML files with their topic directory.
5. Re-run `npm run validate` and `npm run check:siblings`.

Do not silence the gate by placing unrelated topics under a vague parent such as `ml-for-eda` or `dataset-and-tools`.

## EDA Boundary Reminders

- Logic synthesis is front-end Boolean/RTL logic optimization.
- Standard-cell, cell-library, transistor-level, and cell-layout generation belong under layout/cell/analog-layout topics, not logic synthesis.
- Thermal, PDN, EM, reliability, circuit simulation, and multiphysics work are signoff/physical-analysis topics unless the paper is explicitly about placement/routing.
- LLM RTL generation and assertion generation are front-end design/verification automation; keep them separate from HLS unless the paper's task is HLS.
- Dataset/benchmark/tool topics are for reusable evaluation assets or flows, not a fallback for papers with unclear methods.
