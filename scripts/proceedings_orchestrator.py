#!/usr/bin/env python3
"""Outer controller for Codex/Claude proceedings extraction."""
from __future__ import annotations

import argparse
import shutil
import subprocess
from pathlib import Path

import yaml

STEP = Path(".agents/skills/sota-baseline-collector/scripts/proceedings_step.py")
CLAUDE_SKILL = Path(".claude/skills/proceedings-extractor/SKILL.md")
TEMPLATE = Path(".claude/skills/proceedings-extractor/scripts/review_template.py")


def clean_prompt_text(text: str) -> str:
    return text.replace("\x00", " ").replace("\x01", " ")


def run(cmd: list[str], *, capture: bool = False) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, check=True, text=True, stdout=subprocess.PIPE if capture else None)


def step(args: list[str], *, capture: bool = False) -> subprocess.CompletedProcess[str]:
    return run(["python3", str(STEP), *args], capture=capture)


def next_item(batch: Path) -> tuple[str, str] | None:
    result = step(["next", "--batch", str(batch)], capture=True)
    line = result.stdout.strip().splitlines()[-1]
    if line == "NO_PENDING_ITEMS":
        return None
    item_id, source = line.split("\t", 1)
    return item_id, source


def packet(batch: Path, item_id: str) -> Path:
    result = step(["packet", "--batch", str(batch), "--id", item_id], capture=True)
    return Path(result.stdout.strip().splitlines()[-1])


def claude_prompt(packet_path: Path) -> str:
    packet_text = clean_prompt_text(packet_path.read_text(encoding="utf-8"))
    skill_text = clean_prompt_text(CLAUDE_SKILL.read_text(encoding="utf-8")) if CLAUDE_SKILL.exists() else ""
    template_text = clean_prompt_text(run(["python3", str(TEMPLATE), "--id", packet_path.stem, "--source", str(packet_path)], capture=True).stdout)
    return clean_prompt_text(f"""Return YAML only. Fill this template; keep unknown fields empty and list them under needs.
Do not include markdown fences or commentary. Use double-quoted strings for free text.
Experiment baselines must come only from Experiment/Evaluation/Results/Table/Figure evidence.

Extractor rules:
```markdown
{skill_text}
```

Template:
```yaml
{template_text}
```

Packet path: {packet_path}

Packet:
```markdown
{packet_text}
```
""")


def yaml_text(text: str) -> str:
    text = clean_prompt_text(text).strip()
    if "\ndecision:" in text and not text.startswith("decision:"):
        text = "decision:" + text.split("\ndecision:", 1)[1]
    lines = [line for line in text.splitlines() if not line.strip().startswith("```")]
    text = "\n".join(lines).strip()
    if "\ndecision:" in text and not text.startswith("decision:"):
        text = "decision:" + text.split("\ndecision:", 1)[1]
    return text


def run_claude(args: argparse.Namespace) -> int:
    if not shutil.which("claude"):
        raise SystemExit("claude CLI not found; packet is ready for manual extraction")
    batch = args.batch
    packet_path = batch / "packets" / f"{args.id}.md"
    if not packet_path.exists():
        packet_path = packet(batch, args.id)
    out = batch / "extracts" / f"{args.id}.yaml"
    out.parent.mkdir(parents=True, exist_ok=True)
    if out.exists() and not args.force:
        raise SystemExit(f"extract exists; use --force to overwrite: {out}")
    cmd = ["claude", "--print", "--tools", "", "--permission-mode", "dontAsk"]
    if args.model:
        cmd += ["--model", args.model]
    cmd.append(claude_prompt(packet_path))
    result = run(cmd, capture=True)
    text = yaml_text(result.stdout)
    # Fail early if Claude did not follow YAML-only output.
    yaml.safe_load(text)
    out.write_text(text + "\n", encoding="utf-8")
    print(out)
    return 0


def attach_extract(args: argparse.Namespace) -> int:
    cmd = [
        "attach-extract", "--batch", str(args.batch), "--id", args.id,
        "--extract", str(args.extract),
    ]
    if args.force:
        cmd.append("--force")
    step(cmd)
    return 0


def run_one(args: argparse.Namespace) -> int:
    item = next_item(args.batch)
    if item is None:
        print("NO_PENDING_ITEMS")
        return 0
    item_id, source = item
    print(f"processing {item_id}\t{source}")
    packet(args.batch, item_id)
    rc = run_claude(argparse.Namespace(batch=args.batch, id=item_id, force=args.force, model=args.model))
    if rc:
        return rc
    extract = args.batch / "extracts" / f"{item_id}.yaml"
    step(["attach-extract", "--batch", str(args.batch), "--id", item_id, "--extract", str(extract), "--force"])
    data = yaml.safe_load(yaml_text(extract.read_text(encoding="utf-8"))) or {}
    if data.get("decision") == "draft":
        step(["draft", "--batch", str(args.batch), "--id", item_id])
    step(["audit", "--batch", str(args.batch)])
    return 0


def audit(args: argparse.Namespace) -> int:
    return step(["audit", "--batch", str(args.batch)]).returncode


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("run-one")
    p.add_argument("--batch", type=Path, required=True)
    p.add_argument("--force", action="store_true")
    p.add_argument("--model", default="")
    p.set_defaults(func=run_one)
    p = sub.add_parser("run-claude")
    p.add_argument("--batch", type=Path, required=True)
    p.add_argument("--id", required=True)
    p.add_argument("--force", action="store_true")
    p.add_argument("--model", default="")
    p.set_defaults(func=run_claude)
    p = sub.add_parser("attach-extract")
    p.add_argument("--batch", type=Path, required=True)
    p.add_argument("--id", required=True)
    p.add_argument("--extract", type=Path, required=True)
    p.add_argument("--force", action="store_true")
    p.set_defaults(func=attach_extract)
    p = sub.add_parser("audit")
    p.add_argument("--batch", type=Path, required=True)
    p.set_defaults(func=audit)
    args = parser.parse_args()
    args.batch.mkdir(parents=True, exist_ok=True)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
