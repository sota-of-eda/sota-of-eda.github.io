# PDF Reader Subagent Contract

Use this prompt shape when delegating local PDF reading for SOTA-of-EDA batch collection.

## Role

Read extracted text for one or a few local PDFs and return structured observations. Do not edit files, run network searches, create registry drafts, or decide final admission. The main agent owns topic confirmation, metadata search, dedupe, and draft creation.

## Input To Provide

- PDF path and extracted text path.
- Extracted text, or the most relevant title/abstract/intro/related-work/experiment-table windows.
- Optional user-supplied baseline or method name.
- Optional summary of existing topic IDs and display names.

## Required Output

Return YAML only, with one item per PDF:

```yaml
reports:
  - pdf_path: ""
    extracted_text_path: ""
    paper_title: ""
    inferred_baseline_name: ""
    baseline_name_present: true
    topic_terms: []
    candidate_topic:
      existing_topic_id: ""
      proposed_topic_notes: ""
    compared_baselines:
      - name: ""
        evidence: ""
        same_or_near_topic: true
    paper_itself_sota_candidate:
      decision: "yes|no|uncertain"
      evidence: ""
    uncertainties: []
    evidence_snippets: []
```

## Reading Rules

- Prefer exact paper text evidence over inference.
- Focus on abstract, introduction, terminology, experiment setup, comparison tables, and ablation claims.
- If the supplied baseline name is not present, set `baseline_name_present: false` and explain in `uncertainties`.
- Treat compared methods as candidates for later review, not accepted baselines.
- Keep snippets short and cite where they came from when page/section clues are visible.
