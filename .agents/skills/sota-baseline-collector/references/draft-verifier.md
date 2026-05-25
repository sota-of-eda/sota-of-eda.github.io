# Draft Verification Subagent Contract

Use this prompt shape when delegating draft verification for SOTA-of-EDA baseline collection.

## Role

Verify a candidate SOTA-of-EDA draft YAML for completeness, consistency, and potential issues. Summarize findings for human review. Do not edit files or make merge decisions.

## Input To Provide

- Draft YAML content or file path (required)
- List of existing topic_ids and display_names from `data/topics/` (scan nested folders for topic YAMLs)
- Optional: BibTeX retrieval report if available
- Optional: PDF reader report if available

## Checks To Perform

### 1. Field Completeness

- `publication.bibtex`: present and not a TODO placeholder?
- `publication.venue`: present and not "TODO"?
- `compare_when`: non-empty and no TODO strings?
- `benchmark_scope`: non-empty and no TODO strings?
- `metrics`: non-empty and no TODO strings?
- `caveats`: non-empty and no TODO strings?
- `evidence_notes.sota_assessment`: present and not TODO?
- Any remaining TODO/placeholder strings anywhere in the draft?

### 2. Metadata Consistency

- `baseline_id` matches kebab-case pattern?
- `publication.year` is reasonable (1980-2100)?
- `publication.venue` matches known EDA venues? (DAC, ICCAD, ISPD, DATE, ASPDAC, ISLPED, TCAD, TODAES, Microelectronics Journal, arXiv, ISEDA, etc.)
- DOI format is valid if present?
- `arxiv_url` contains a valid arXiv ID if present?
- All links (`paper_url`, `pdf_url`, `arxiv_url`, `repo_url`, `project_url`) are valid URLs?

### 3. Topic Placement

- If `candidate_topic.status` is "existing": does `topic_id` exist in the provided topic list?
- If `candidate_topic.status` is "proposed": are all required `proposed_topic` fields present (`topic_id`, `short_name`, `display_name`, `description`, `review_triggers`)?
- Is the topic placement justified by `compare_when` and `benchmark_scope` fields?

### 4. SOTA Assessment Quality

- Does `sota_assessment` contain concrete evidence (numbers, benchmark names, comparison targets)?
- Or is it vague/hedging? Flag as warning if so.

### 5. Duplicate Risk

- Are there any `compared_baselines_to_review` entries that might already exist in the registry?
- Does `baseline_id` conflict with any existing baseline?

## Required Output

Return YAML only:

```yaml
verification:
  draft_path: ""
  status: "ready|needs_work|critical_issues"
  checks:
    - category: "completeness|consistency|topic|assessment|duplicates"
      severity: "error|warning|info"
      field: ""
      message: ""
  summary: ""
  human_action_items: []
```

## Severity Definitions

- **error**: Blocks merge. Missing required data or contradictory info.
- **warning**: Should be addressed before merge but not strictly blocking.
- **info**: Observation for human awareness; no action required.
