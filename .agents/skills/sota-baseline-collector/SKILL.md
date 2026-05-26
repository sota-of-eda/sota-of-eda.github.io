---
name: sota-baseline-collector
description: Use when collecting candidate SOTA-of-EDA topic or baseline entries from a baseline, method, paper name, URL/list, or local PDF batch, especially when metadata, BibTeX, topic placement, duplicate checks, or human-reviewable registry drafts are needed.
---

# SOTA Baseline Collector

## Core Rules

- Produce drafts for human review first; do not directly edit accepted `data/topics/` files unless the user explicitly asks after review.
- Use one unified workflow for every input shape: oral paper/method reference, pasted list, URLs, existing manifest, local PDFs, or a large proceedings directory.
- Normalize inputs first. Resolve canonical title, DOI/arXiv, PDF URL, or local PDF path into a batch-local source manifest before reading evidence.
- Never save web PDFs in the repo. Store PDF URLs. Local user PDFs may be referenced by path; copy them only if the user explicitly asks.
- Do not bulk-scrape Google Scholar. Prefer DOI/Crossref, DBLP, arXiv, Semantic Scholar/OpenAlex, publisher/official proceedings pages, project pages, and GitHub.
- Keep registry semantics strict: declared `baselines` and `review_triggers` are direct to their topic. Parent aggregation is UI-only.
- Attach candidates to the narrowest confirmed topic. If a topic is uncertain or new, propose one and use the Topic Merge/Rearrange Gate before creating or migrating topics.
- Do not load complete PDFs or complete extracted text into conversation context. Scripts must first produce compact title/abstract/experiment/table windows.
- Remind the user to delete reviewed `data/drafts/` and `data/drafts/batches/` files after merging or rejecting them.

Read `references/registry-semantics.md` before producing topic or baseline YAML. Read `references/pdf-reader-subagent.md` before delegating compact evidence reading. Read `references/bibtex-retrieval.md` before retrieving BibTeX or PDF links. Read `references/topic-merge-rearrange.md` before running the Topic Gate or proposing topic aggregates. Read `references/draft-verifier.md` only for single-paper verification or high-risk batch sampling. Read `references/confirmed-draft-merge.md` before moving a user-confirmed draft into `data/topics/`.

## Unified Workflow: Acquire -> Index -> Triage -> Packet -> Metadata -> Topic Gate -> Draft -> Audit

Use this workflow for a single named baseline, a paper title, a URL/list, or hundreds of local PDFs. The only difference is the acquisition input; every later stage is the same script-first, context-light path.

### Status Vocabulary

Use only these statuses in batch docs/reports:

- `resolved`: input was normalized to a manifest item with source path/URL/title hint.
- `pdf_available`: local PDF exists or a verified PDF URL is recorded.
- `screened`: paper was indexed and triaged by scripts.
- `skip`: not an EDA baseline candidate.
- `duplicate`: already represented in accepted registry or active root drafts.
- `candidate`: high-confidence EDA candidate ready for compact review/metadata.
- `deferred`: plausible but insufficient evidence or noisy metadata; do not spend tokens unless gap scanning needs it.
- `drafted`: draft YAML generated for human review.
- `accepted`: merged into `data/topics/` after explicit approval.
- `rearrange_required`: topic fanout/layering must be resolved before topic creation or migration.

### Artifact Layout

Keep durable workflow state under `data/drafts/batches/<batch-id>/`:

```text
sources/         source_manifest.yaml/jsonl, URL/list/PDF discovery results
pdfs/            optional local user-provided PDFs only when explicitly allowed
extracted/       full extracted text; local search only, never pasted wholesale
index/           paper_index.yaml/jsonl, registry snapshot, dedupe index
triage/          triage.yaml, skips.tsv, deferred.tsv, gap_scan.tsv
packets/         compact agent-readable review packets
metadata_cache/  DOI/BibTeX/API/cache artifacts
topic_gate/      fanout report, rearrange packet, topic_remap.yaml
audit/           deterministic batch audit reports
STATUS.md        compact current status
```

### Steps

1. **Acquire**: run `scripts/proceedings_acquire.py` or manually create the same manifest. For a name/title, resolve canonical metadata and PDF URL if available. For a list, create one manifest item per entry. For local PDFs, record paths. For proceedings directories, build a manifest without pasting file contents.
2. **Extract**: use `scripts/extract_pdf_text.py` for local PDFs. Store extracted text under `extracted/`; do not put full text in prompts.
3. **Index**: run `scripts/proceedings_index.py` to create compact title, abstract, section offsets, experiment windows, and table windows.
4. **Triage**: run `scripts/proceedings_triage.py` to classify `candidate`, `skip`, `duplicate`, or `deferred` and produce gap-scan lists.
5. **Packet**: run `scripts/proceedings_windows.py` for `candidate` and selected `deferred` items only. Agents may read these compact packets, not full papers.
6. **Metadata**: run `scripts/proceedings_metadata.py` to resolve DOI/BibTeX/PDF/repo evidence. If formal metadata is unavailable, use explicit medium-confidence proceedings metadata and record unresolved fields; never invent DOI/BibTeX.
7. **Topic Gate**: run `scripts/proceedings_topic_gate.py` before creating or migrating proposed topics. If it returns `rearrange_required`, stop topic creation and present the compact remap packet.
8. **Draft**: create human-reviewable drafts under `data/drafts/` only after candidate review. Do not auto-merge compared baselines.
9. **Audit**: run `scripts/proceedings_audit.py` for deterministic batch checks. This replaces individual verifier loops for large/batch work.
10. **Status**: update `STATUS.md` with counts and blockers only. Do not narrate every paper.

### Slimming Rules

- Do not re-read full proceedings PDFs or full extracted text in agent context.
- Do not dispatch verifier subagents by individual paper or draft.
- Do not create gates that fail because of historical repository state; a gate blocks only when the current batch worsens a concrete problem.
- Prefer high-precision first pass plus deterministic gap scan over exhaustive uncertain-paper reading.
- Use agent judgment only for compact packets, topic ambiguity, metadata conflicts, or a small high-risk audit sample.

## Duplicate Check

Use title/DOI/arXiv/baseline ID checks only. Run examples:

```bash
python3 .agents/skills/sota-baseline-collector/scripts/registry_dedupe.py --repo . --title "Paper Title" --doi "10.xxxx/yyyy"
python3 .agents/skills/sota-baseline-collector/scripts/registry_dedupe.py --repo . --candidate data/drafts/example.yaml
```

If duplicates appear, do not create a new accepted baseline. Produce a draft note that recommends updating the existing entry instead.

## Draft Output

Drafts belong under `data/drafts/` and are temporary. A draft should include only real data fields, no fake TODO placeholders:

- `candidate_topic`: existing topic ID or structured `proposed_topic` fields.
- `baseline`: schema-compatible baseline snippet with verified or explicitly unresolved metadata.
- `evidence_notes`: source URLs, confidence, unresolved fields, and SOTA assessment.
- `compared_baselines_to_review`: baselines found in experiments that may deserve separate collection.

Use `scripts/make_candidate_draft.py` for a skeleton containing only real data fields, then fill remaining fields from metadata and compact evidence packets. For batch work, run `scripts/proceedings_audit.py` instead of individual verifier loops.

## Topic Merge/Rearrange Gate

The orbit cloud layout has hard limits to prevent visual overlap:

- **Max siblings per parent**: 6.
- **Max direct children per topic**: 10.

Run `scripts/proceedings_topic_gate.py` before creating/migrating proposed topics. This is a real gate: it blocks only when the current batch would create new topics or remaps that worsen fanout. Historical overflow is reported as context, not as a fake failure for ordinary baseline additions.

Gate statuses:

- `allow`: no current-batch fanout risk; proceed.
- `rearrange_required`: stop topic creation/migration and present `topic_rearrange_packet.md`.
- `manual_decision_required`: EDA semantic grouping is ambiguous; ask for a human topic decision.

Rearrangement workflow:

1. Count target parents, direct children, and siblings for every proposed parent.
2. If the batch worsens fanout, stop migration and list overloaded parent plus candidate additions.
3. Cluster nearby siblings by EDA meaning, not by paper venue/year.
4. Propose intermediate aggregate topics, then remap affected draft topics under those aggregates.
5. Re-run the topic gate and only then migrate drafts into `data/topics/`.

Default EDA boundary rules:

- Logic synthesis is front-end Boolean/RTL/gate optimization.
- Cell generation, transistor-level placement, and standard-cell layout are cell/layout-centric and belong under analog/layout-oriented topics, not logic synthesis.
- Common aggregates include signoff analysis, front-end RTL automation, emerging-technology EDA, package/PCB physical design, manufacturing/reliability, and analog/cell design automation.

If the user asks for minimal-token operation, report only the overloaded parent, proposed aggregate topics, and remapping table.

## Validation

Before presenting final batch results, run:

```bash
python3 -m py_compile .agents/skills/sota-baseline-collector/scripts/*.py
python3 .agents/skills/sota-baseline-collector/scripts/proceedings_audit.py --repo . --batch-dir data/drafts/batches/<batch-id> --dry-run
python3 .agents/skills/sota-baseline-collector/scripts/proceedings_topic_gate.py --repo . --batch-dir data/drafts/batches/<batch-id> --dry-run
npm run validate
npm run check:siblings
```

`npm run check:siblings` is a global taxonomy warning/audit. It is not by itself a batch failure unless the current batch worsens fanout. `npm run validate` validates accepted registry files; drafts are intentionally outside the accepted schema.
