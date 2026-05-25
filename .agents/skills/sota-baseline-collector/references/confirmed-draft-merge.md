# Confirmed Draft Merge Guide

Use this only after the user explicitly confirms a draft or provides an edited draft they want promoted into accepted registry data.

## Preconditions

- The draft has no unresolved required fields in `baseline.publication`, `compare_when`, `benchmark_scope`, `metrics`, or `caveats`.
- Topic placement is confirmed as either an existing topic or a proposed topic to create.
- `evidence_notes.sota_assessment` supports whether the paper itself should enter `baselines`.
- Duplicate check has no conflicting accepted record, or the user explicitly asks to update the existing record.

## Existing Topic Merge

1. Read `candidate_topic.topic_id`.
2. Open `data/topics/<topic_id>.yaml`.
3. Append the confirmed `baseline` object to that topic's `baselines` list.
4. Keep `compared_baselines_to_review` out of accepted data unless separate drafts are approved.

## Proposed Topic Merge

1. Read `candidate_topic.proposed_topic`.
2. Create `data/topics/<proposed_topic.topic_id>.yaml` if it does not exist.
3. Use the proposed topic fields: `topic_id`, optional `parent_id`, `short_name`, `display_name`, `aliases`, `description`, `review_triggers`, and `baselines`.
4. Put the confirmed paper baseline in `baselines` only when the user approved the paper itself as a baseline candidate; otherwise keep `baselines: []`.
5. Choose `display_order` only if the repo requires it for nearby topics; do not use it as a rank.

## Required Validation

Run these after changing accepted data:

```bash
python3 .agents/skills/sota-baseline-collector/scripts/registry_dedupe.py --repo . --candidate data/drafts/<confirmed-draft>.yaml
npm run validate
```

If validation passes, report the accepted topic file path and remind the user to delete the reviewed draft or batch artifacts after they are no longer needed.
