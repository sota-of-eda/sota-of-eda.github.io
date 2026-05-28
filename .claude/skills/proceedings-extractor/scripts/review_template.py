#!/usr/bin/env python3
"""Print the minimal proceedings review YAML template for Claude Code."""
from __future__ import annotations

import argparse


def main() -> int:
    parser = argparse.ArgumentParser(description="print a draft-only proceedings review template")
    parser.add_argument("--id", default="", help="batch item id")
    parser.add_argument("--source", default="", help="packet or PDF path")
    args = parser.parse_args()
    print(f"""decision: deferred
item_id: "{args.id}"
source: "{args.source}"
title: ""
authors: []
topic:
  topic_id: ""
  confidence: low
candidate:
  name: ""
  kind: method
  evidence_location: ""
  evidence_text_short: ""
experiment_baselines: []
metadata_requests: []
needs:
  - title_authors_review
  - topic_review
  - experiment_review
notes: ""
""")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
