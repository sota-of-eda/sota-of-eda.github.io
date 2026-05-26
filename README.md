# SOTA of EDA

**An awesome EDA benchmark collection and baseline registry for Electronic Design Automation (EDA) / VLSI CAD research.**

Also discoverable as: *awesome EDA*, *EDA SOTA table*, *EDA benchmark registry*, *VLSI CAD baseline reference*, *EDA paper comparison*.

Indexes **106+ topics** and **267+ baselines** across placement, routing, timing, logic synthesis, high-level synthesis, circuit verification, analog layout, mask optimization, testing, and more.

This registry helps authors, reviewers, and AI agents check whether an experiment discusses reference baselines that match the paper's claim, benchmark scope, and caveats. Designed for AI-assisted SOTA comparison — **verify entries before citing**.

Site: https://sota-of-eda.github.io/ &middot; Data: [/registry.json](https://sota-of-eda.github.io/registry.json) &middot; Feed: [/atom.xml](https://sota-of-eda.github.io/atom.xml)

## Contribute

Use the `/sota-baseline-collector` skill to automate baseline entry. Or edit `data/topics/*.yaml` directly — see `data/schema/topic.schema.json` for the schema. Run `npm run validate` before committing.

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
  title   = {SOTA of EDA: An Agent-Assisted Baseline and Benchmark Registry for EDA Research},
  year    = {2026},
  url     = {https://sota-of-eda.github.io/}
}
```
