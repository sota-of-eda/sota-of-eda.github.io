# SOTA of EDA

**An awesome EDA benchmark collection and baseline registry for Electronic Design Automation (EDA) / VLSI CAD research.**

Indexes **122 topics** and **500 baselines** across placement, routing, timing, logic synthesis, high-level synthesis, circuit verification, analog layout, mask optimization, testing, and more.

This registry helps authors, reviewers, and AI agents check whether an experiment discusses reference baselines that match the paper's claim, benchmark scope, and caveats. Designed for AI-assisted SOTA comparison — **verify entries before citing**.

Site: https://sota-of-eda.github.io/ &middot; Data: [/registry.json](https://sota-of-eda.github.io/registry.json) &middot; Feed: [/atom.xml](https://sota-of-eda.github.io/atom.xml)

## Contribute

Use the `/sota-baseline-collector` workflow to create reviewable drafts before editing accepted registry data. Or edit `data/topics/*.yaml` directly — see `data/schema/topic.schema.json` for the schema. Run `npm run validate` before committing.

For proceedings or PDF batches, start from Codex and describe the sources to process, for example:

```text
Use /sota-baseline-collector to process these ICCAD 2025 PDFs into draft baseline entries.
```

The workflow's distinctive setup is **Codex (GPT-5.5) driving Claude code (mimo v2.5pro)**: Codex orchestrates the batch, verifies topics/metadata/duplicates, and calls Claude only for one-paper packet extraction. Drafts stay under `data/drafts/batches/<batch-id>/` until explicitly accepted for merge.

## Local Preview

```bash
npm install
npm run build
npm run preview
```

## License

Code: MIT. Data: CC-BY-4.0.

## Citation

```
@misc{sotaofeda2026,
  title   = {An Automatic Agent Workflow for SOTA Collection in EDA Research},
  year    = {2026},
  url     = {https://sota-of-eda.github.io/}
}
```
