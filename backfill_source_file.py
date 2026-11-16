#!/usr/bin/env python3
"""Backfill source_file metadata on existing beliefs.

Scans all beliefs, finds ones missing source_file metadata,
extracts the source file path from their entry's # File: header,
and stores it via reasons set-metadata.

Usage:
    cd ~/git/nexus-expert
    python ~/git/code-expert/backfill_source_file.py [--dry-run]
"""

import json
import subprocess
import sys
from pathlib import Path


def extract_source_file(entry_path: str) -> str | None:
    p = Path(entry_path)
    if not p.is_file():
        return None
    try:
        for line in p.read_text().splitlines()[:5]:
            if line.startswith("# File: "):
                return line[8:].strip()
    except OSError:
        pass
    return None


def main():
    dry_run = "--dry-run" in sys.argv

    network_path = Path("network.json")
    if not network_path.exists():
        subprocess.run(["reasons", "export"], capture_output=True, text=True)
    if not network_path.exists():
        print("No network.json found. Run: reasons export")
        sys.exit(1)

    network = json.loads(network_path.read_text())
    nodes = network.get("nodes", {})

    already_set = 0
    backfilled = 0
    no_entry = 0
    no_file_header = 0

    for nid, node in sorted(nodes.items()):
        existing = (node.get("metadata") or {}).get("source_file")
        if existing:
            already_set += 1
            continue

        source = node.get("source", "")
        if not source:
            no_entry += 1
            continue

        src_file = extract_source_file(source)
        if not src_file:
            no_file_header += 1
            continue

        if dry_run:
            print(f"  would set {nid} → {src_file}")
        else:
            r = subprocess.run(
                ["reasons", "set-metadata", nid, "source_file", src_file],
                capture_output=True, text=True,
            )
            if r.returncode == 0:
                backfilled += 1
            else:
                print(f"  FAIL {nid}: {r.stderr.strip()}")

        backfilled += 1 if dry_run else 0

    print(f"\nResults:")
    print(f"  Already set:     {already_set}")
    print(f"  Backfilled:      {backfilled}")
    print(f"  No entry path:   {no_entry}")
    print(f"  No # File header:{no_file_header}")
    print(f"  Total:           {len(nodes)}")


if __name__ == "__main__":
    main()
