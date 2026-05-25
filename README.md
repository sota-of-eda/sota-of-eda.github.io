# SOTA of EDA

A static, agent-readable registry for EDA topics and reference baselines. It helps authors, reviewers, and coding agents check whether an experiment discusses baselines that match the paper's claim, benchmark scope, and caveats.

This project is reference guidance, not a leaderboard or universal SOTA declaration.

## Contents

- `data/topics/`: schema-validated topic and baseline registry.
- `data/schema/topic.schema.json`: registry schema.
- `scripts/`: validation and registry bundling utilities.
- `src/`: Vite/React topic explorer.
- `.github/workflows/pages.yml`: GitHub Pages deployment workflow.

## Local Preview

```bash
npm install
npm run build
npm run preview
```

Open the preview URL printed by Vite.

## Registry Semantics

- `review_triggers` and `baselines` are declared on their narrowest matching topic.
- Parent topics may aggregate descendant triggers and baselines in the UI for browsing only.
- A baseline applies only when its `compare_when`, benchmark scope, metrics, reproducibility status, and caveats fit the paper claim.
- If a matching topic has `baselines: []`, report that the registry cannot assert a missing baseline yet; do not invent one.

## Adding Baselines

Baseline cards should include short name, full BibTeX, paper/PDF/arXiv links when available, repository or project links when open-source, benchmark scope, metrics, reproducibility status, and caveats.

Keep wording conditional and evidence-backed. Submit small schema-valid changes.

## Licensing

- Code, scripts, build configuration, and UI source: MIT (`LICENSE`).
- Registry data and documentation: CC-BY-4.0 (`LICENSE-CONTENT`).

Generated registry bundles such as `src/generated/registry.json` are derived from the CC-BY-4.0 registry data.
