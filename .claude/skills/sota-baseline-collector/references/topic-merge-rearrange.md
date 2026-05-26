# Topic Merge/Rearrange Gate

Use this reference whenever a candidate batch proposes new topics, remaps topics, or adds many siblings under one parent. The goal is to protect the orbit/bubble UI from overlap while preserving EDA semantics.

## Gate Purpose

This is a real gate, not a generic warning. It blocks only when the current batch would worsen topic fanout by creating or moving topics. Ordinary baseline additions to existing topics should not be blocked by historical overflow.

## Hard Limits

- Max siblings under one parent: 6.
- Max direct children of one topic: 10.

`npm run check:siblings` is a global taxonomy audit. Treat its pre-existing findings as context unless the current batch adds to the overloaded parent.

## Inputs

Use compact artifacts only:

- Proposed topic IDs, parent IDs, and display names from candidate drafts or `topic_remap.yaml`.
- Existing topic tree from `data/topics/**/*.yaml`.
- Optional batch triage/topic hints from `packets/` or `topic_gate/`.

Do not re-read papers to run this gate. If a topic placement is semantically unclear, read the compact packet or ask the user.

## Gate Status

- `allow`: current batch does not worsen sibling/child fanout.
- `rearrange_required`: current batch would exceed limits or add to an already-overloaded parent.
- `manual_decision_required`: EDA semantics are ambiguous enough that an automatic aggregate would be risky.

## Required Procedure

1. Count current siblings and direct children for each proposed `parent_id`.
2. Add only current-batch proposed topics/remaps to the count.
3. If the resulting count exceeds limits, stop topic creation/migration and emit `rearrange_required`.
4. Build a compact rearrange packet: overloaded parent, current relevant children, proposed additions, suggested aggregate topics, and remapping table.
5. Re-run the gate after remapping before any accepted-data merge.

## Rearrangement Heuristics

Group by EDA semantics, not by conference, year, or paper count. Prefer small aggregate topics that explain the task boundary.

Common aggregates to consider:

- `signoff-analysis`: timing, power, IR-drop, EM, thermal, aging, glitch, and multiphysics signoff-like analysis.
- `front-end-design-automation`: RTL/spec generation, assertion/testbench generation, high-level design automation, and design-space exploration when not purely HLS.
- `emerging-technology-eda`: quantum, photonic, superconducting, flexible electronics, and other non-CMOS design automation.
- `package-pcb-design`: package routing, PCB library generation, interposer/chiplet packaging tasks.
- `manufacturing-reliability`: lithography, CMP, OPC/ILT, DFM, yield, aging, and reliability tasks.
- `analog-cell-design-automation`: analog synthesis, transistor-level placement, standard-cell generation/layout, cell migration.

## EDA Boundary Rules

- Logic synthesis means front-end Boolean/RTL/gate optimization, technology mapping, AIG/MIG/LUT/TLN transformations, or logic-level approximate synthesis.
- Cell generation, transistor-level placement, standard-cell layout, and cell migration are cell/layout-centric. Put them under analog/cell/layout-oriented topics, not logic synthesis.
- Circuit simulation, waveform/timing simulation, power/IR/EM/thermal signoff, and aging/glitch analysis are analysis/signoff topics, not verification solely because they inspect circuits.
- FPGA architecture exploration and PCB component-library generation are tool/dataset/design-automation topics only when the paper evaluates an automation method, not merely a product architecture.
- Quantum/photonic/superconducting synthesis/routing/placement should stay under emerging-technology EDA unless the task is explicitly conventional CMOS EDA.

## Minimal Report Format

For minimal-token operation, report only:

```yaml
topic_gate:
  status: allow|rearrange_required|manual_decision_required
  overloaded_parent: ""
  reason: ""
  proposed_aggregates: []
  remap:
    - old_topic_hint: ""
      action: keep|move|merge|create_aggregate
      final_topic_id: ""
      new_parent_id: ""
      reason: ""
```
