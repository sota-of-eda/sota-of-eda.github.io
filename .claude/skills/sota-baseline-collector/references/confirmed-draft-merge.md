# Confirmed Draft Merge Guide

Use this only after the user explicitly confirms a draft or provides an edited draft they want promoted into accepted registry data.

## Preconditions

- The draft has no unresolved required fields in `baseline.publication`, `compare_when`, `benchmark_scope`, `metrics`, or `caveats`.
- Topic placement is confirmed as either an existing topic or a proposed topic to create.
- `evidence_notes.sota_assessment` supports whether the paper itself should enter `baselines`.
- Duplicate check has no conflicting accepted record, or the user explicitly asks to update the existing record.

## Data Structure

The validation script (`scripts/validate-registry.mjs`) walks `data/topics/` recursively:
- Files with `topic_id` at the top level are **topics**.
- Files with `baseline_id` at the top level are **baselines**.
- Baselines attach to the topic in the **same directory** (by folder path, not by name).

A draft YAML wraps the baseline inside a `baseline:` key. When merging, you must extract only the `baseline` object and write it as a standalone YAML file with `baseline_id` at the top level. Do not write the draft wrapper (`draft_kind`, `created_at`, `candidate_topic`, `evidence_notes`) into the registry.

## Existing Topic Merge

1. Read `candidate_topic.topic_id`.
2. Locate the topic folder: search `data/topics/` for a folder containing `<topic_id>.yaml`.
3. Extract the `baseline` object from the draft (not the whole draft).
4. Write it as a standalone YAML file: `data/topics/<topic_id>/<baseline_id>.yaml`. The file must have `baseline_id` at the top level, matching the schema in `data/schema/topic.schema.json` under `definitions.baseline`.
5. Keep `compared_baselines_to_review` out of accepted data unless separate drafts are approved.

## Proposed Topic Merge

1. Read `candidate_topic.proposed_topic`.
2. Determine the parent folder from `parent_id`. Create the topic folder at `data/topics/<parent_id>/<topic_id>/` (nested) or `data/topics/<topic_id>/` (root, no parent).
3. Write the topic YAML as `data/topics/<topic_id>/<topic_id>.yaml` using proposed fields: `topic_id`, optional `parent_id`, `short_name`, `display_name`, `aliases`, `description`, `review_triggers`. The `baselines` field is not needed — baselines are separate files in the same folder.
4. Extract the `baseline` object from the draft and write it as `data/topics/<topic_id>/<baseline_id>.yaml` only when the user approved the paper itself as a baseline candidate.
5. Choose `display_order` only if the repo requires it for nearby topics; do not use it as a rank.

## Required Validation

Run these after changing accepted data:

```bash
python3 .agents/skills/sota-baseline-collector/scripts/registry_dedupe.py --repo . --candidate data/drafts/<confirmed-draft>.yaml
npm run validate
```

If validation passes, report the accepted topic file path and remind the user to delete the reviewed draft or batch artifacts after they are no longer needed.
