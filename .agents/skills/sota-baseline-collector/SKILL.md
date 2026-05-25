---
name: sota-baseline-collector
description: Use when collecting candidate SOTA-of-EDA topic or baseline entries from a baseline, method, paper name, or many local PDF files, especially when paper metadata, BibTeX, PDF/project/code links, topic placement, compared baselines, duplicate checks, or human-reviewable registry drafts are needed.
---

# SOTA Baseline Collector

## Core Rules

- Produce drafts for human review first; do not directly edit accepted `data/topics/*.yaml` unless the user explicitly asks after review.
- Never save web PDFs in the repo. Store only PDF URLs. Local PDFs supplied by the user may be read but not copied into the registry.
- Do not bulk-scrape Google Scholar. Search broadly, then verify facts against reliable pages when available: publisher/DOI, arXiv, OpenReview, DBLP, Crossref, OpenAlex, Semantic Scholar, project pages, and GitHub.
- Keep registry semantics strict: declared `baselines` and `review_triggers` are direct to their topic. Parent aggregation is UI-only.
- Attach candidates to the narrowest confirmed topic. If a topic is uncertain or new, propose one and ask the user to confirm before treating it as final.
- If a PDF does not contain the baseline name, and the name cannot be inferred from title/abstract/intro/experiments, ask the user for the baseline name.
- Remind the user to delete reviewed `data/drafts/` and `data/drafts/batches/` files after merging or rejecting them.

Read `references/registry-semantics.md` before producing topic or baseline YAML. Read `references/pdf-reader-subagent.md` before delegating PDF reading. Read `references/confirmed-draft-merge.md` before moving a user-confirmed draft into `data/topics/*.yaml`.

## Workflow A: Baseline Name

1. Search the web for the supplied baseline/method/paper name.
2. Identify the canonical paper title, authors if needed, venue, year, DOI/arXiv, PDF URL, project URL, and code URL.
3. Get BibTeX from a reliable source when possible. If only generated BibTeX is available, mark it as lower confidence in the draft notes.
4. Read the paper abstract/intro/terms/experiment section if available. Determine the closest existing topic from `data/topics/*.yaml`.
5. If no existing topic fits, propose a new topic with parent, display name, aliases, description, and review triggers; ask the user to confirm or revise.
6. Evaluate the paper's compared methods. Treat compared baselines as likely same-or-near-topic SOTA candidates that deserve review, not automatic admission.
7. Evaluate whether the paper itself should be admitted as a candidate baseline for that topic.
8. Run duplicate checks with `scripts/registry_dedupe.py` using title/DOI/arXiv/baseline ID.
9. Write a candidate draft with `scripts/make_candidate_draft.py`, then include unresolved fields and source confidence in the response.

## Workflow B: Heavy Local PDF Batch

1. Create a batch ID such as `20260525-placement-review` and an artifact root under `data/drafts/batches/<batch-id>/`.
2. Extract full text with `scripts/extract_pdf_text.py --max-pages 0 --max-chars 0`, usually into `data/drafts/batches/<batch-id>/extracted/`.
3. Dispatch subagents to read extracted text, not PDF URLs. Use `references/pdf-reader-subagent.md` as the prompt contract.
4. Use adaptive delegation: one PDF per subagent by default; if there are more than 12 PDFs and each extracted text is short/simple, group up to 3 PDFs per subagent; keep long papers or dense experiment tables one PDF per subagent.
5. Require subagents to return structured reading reports only. They must not edit files, run network searches, or make final admission decisions.
6. Save each report as `data/drafts/batches/<batch-id>/reports/<extracted-text-stem>.reader.yaml` when durable review artifacts are useful, reusing the hash-suffixed extracted text stem to avoid collisions.
7. Main agent summarizes reports, asks the user when baseline names or topics are ambiguous, then follows Workflow A for metadata search, dedupe, and candidate draft generation.
8. Keep drafts separate per candidate or per paper when candidates are tightly coupled. Do not save PDF copies.

## Workflow C: Confirmed Draft Merge

Only run this workflow after the user explicitly confirms a draft or edits it into an approved shape.

1. Read `references/confirmed-draft-merge.md`.
2. Re-run duplicate checks on the confirmed draft.
3. If `candidate_topic.status` is `existing`, append the confirmed `baseline` to `data/topics/<topic_id>.yaml`.
4. If `candidate_topic.status` is `proposed`, create or update `data/topics/<proposed_topic.topic_id>.yaml` from `candidate_topic.proposed_topic`, with the confirmed baseline in `baselines` only if the user approved admitting the paper itself.
5. Do not auto-merge `compared_baselines_to_review`; create separate drafts for them instead.
6. Run `npm run validate` after changing accepted data, then remind the user to delete the reviewed draft/batch artifacts.

## Duplicate Check

Use title/DOI/arXiv/baseline ID checks only. Run examples:

```bash
python3 .agents/skills/sota-baseline-collector/scripts/registry_dedupe.py --repo . --title "Paper Title" --doi "10.xxxx/yyyy"
python3 .agents/skills/sota-baseline-collector/scripts/registry_dedupe.py --repo . --candidate data/drafts/example.yaml
```

If duplicates appear, do not create a new accepted baseline. Produce a draft note that recommends updating the existing entry instead.

## Draft Output

Drafts belong under `data/drafts/` and are temporary. A draft should include:

- `candidate_topic`: existing topic ID or structured `proposed_topic` fields.
- `baseline`: schema-compatible baseline snippet.
- `evidence_notes`: source URLs, search terms, confidence, unresolved fields, and whether the paper itself appears to be a SOTA candidate.
- `compared_baselines_to_review`: baselines found in the paper's experiments that may deserve separate collection.
- `human_review`: checklist and explicit reminder to delete the draft after review.

Use `scripts/make_candidate_draft.py` for a skeleton, then fill the draft carefully. Use proposed-topic arguments when no existing topic is confirmed.

## Validation

Before presenting final results, run:

```bash
python3 .agents/skills/sota-baseline-collector/scripts/registry_dedupe.py --repo . --candidate data/drafts/<draft>.yaml
npm run validate
```

Do not claim a draft is ready until the duplicate check and registry validation have completed. `npm run validate` validates accepted registry files; drafts are intentionally outside the accepted schema.
