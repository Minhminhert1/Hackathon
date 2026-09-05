"""
Ad-hoc smoke test for fxvn_parser (no assertions — pass/fail judged by eye).
Runs run_parser.py against the real collected data and prints a few sample
deals so a human can sanity-check the output.

Usage: python scratch\\run_test_parser.py [path-to-jsonl]
"""
import json
import os
import subprocess
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PARSER_DIR = os.path.join(REPO_ROOT, "fxvn_parser")


def main():
    data_path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(REPO_ROOT, "data", "data-2026-09-05.jsonl")
    data_path = os.path.abspath(data_path)

    print(f"Running run_parser.py on: {data_path}")
    result = subprocess.run(
        [sys.executable, "run_parser.py", data_path],
        cwd=PARSER_DIR,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    print("--- stdout ---")
    print(result.stdout)
    if result.returncode != 0:
        print("--- stderr ---")
        print(result.stderr)
        print(f"FAILED: exit code {result.returncode}")
        return

    deals_path = os.path.join(PARSER_DIR, "deals.json")
    with open(deals_path, encoding="utf-8") as f:
        deals = json.load(f)

    print(f"\ndeals.json has {len(deals)} spot deals. First 5 records:")
    for d in deals[:5]:
        print(json.dumps(d, ensure_ascii=False))


if __name__ == "__main__":
    main()
