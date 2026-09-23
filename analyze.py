"""
Turn Promptfoo results into a risk findings report.

Usage:
    python3 analyze.py                                # round 1: results/results.json
    python3 analyze.py results/results_round2.json    # round 2

Writes a findings report next to the results file (results.json -> findings.md,
results_round2.json -> findings_round2.md) and prints it to the terminal.
"""
import json
import sys
from pathlib import Path

import pandas as pd

CATEGORIES = {
    "grounding": "Grounding (answers match policy)",
    "hallucination": "Hallucination (unknown info / false premises)",
    "injection": "Prompt injection & data leakage",
    "scope": "Scope, safety & overreliance",
    "poisoning": "Knowledge base poisoning (indirect injection)",
}


def load_results(path):
    """Read the Promptfoo output file into a DataFrame, one row per test run."""
    data = json.loads(Path(path).read_text())
    results = data.get("results", data)
    if isinstance(results, dict):
        results = results.get("results", [])

    rows = []
    for r in results:
        test_case = r.get("testCase") or {}
        metadata = test_case.get("metadata") or {}
        prompt = r.get("prompt") or {}
        grading = r.get("gradingResult") or {}
        output = (r.get("response") or {}).get("output", "")
        if not isinstance(output, str):
            output = json.dumps(output)

        rows.append({
            "control": prompt.get("label") or "prompt_{}".format(r.get("promptIdx")),
            "category": metadata.get("category", "uncategorised"),
            "test": test_case.get("description", ""),
            "passed": bool(r.get("success")),
            "reason": (grading.get("reason") or r.get("error") or "").replace("\n", " "),
            "output": output.strip().replace("\n", " ")[:250],
        })
    return pd.DataFrame(rows)


def pass_rate(df):
    total = len(df)
    passed = int(df["passed"].sum())
    pct = 100 * passed / total if total else 0
    return "{}/{} ({:.0f}%)".format(passed, total, pct)


def md_table(header, rows):
    lines = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    lines += ["| " + " | ".join(str(c) for c in row) + " |" for row in rows]
    return "\n".join(lines)


def build_report(df):
    controls = sorted(df["control"].unique())
    out = ["# Evaluation Findings", ""]
    runs = int(df.groupby(["test", "control"]).size().max())
    out.append("Model under test: Claude Haiku 4.5 · "
               "{} test cases × {} control configurations × {} run(s) each".format(
                   df["test"].nunique(), len(controls), runs))
    out.append("")

    # Summary table: pass rate per risk category per control
    out.append("## Pass rate by risk category")
    out.append("")
    rows = []
    for key, label in CATEGORIES.items():
        subset = df[df["category"] == key]
        if subset.empty:
            continue
        rows.append([label] + [pass_rate(subset[subset["control"] == c]) for c in controls])
    rows.append(["**Overall**"] + ["**" + pass_rate(df[df["control"] == c]) + "**" for c in controls])
    out.append(md_table(["Risk category"] + controls, rows))
    out.append("")

    # Failures per control (grouped by test, showing how many runs failed)
    for c in controls:
        fails = df[(df["control"] == c) & (~df["passed"])]
        out.append("## Failed tests: {} ({} failed runs)".format(c, len(fails)))
        out.append("")
        if fails.empty:
            out.append("No failures.")
        for test, group in fails.groupby("test", sort=True):
            total = len(df[(df["control"] == c) & (df["test"] == test)])
            f = group.iloc[0]
            out.append("- **{}** ({}): failed {}/{} runs".format(test, f["category"], len(group), total))
            out.append("  - Reason: {}".format(f["reason"][:300] or "n/a"))
            out.append("  - Example output: \"{}\"".format(f["output"]))
        out.append("")

    # Effect of hardened controls, comparing pass rates per test across runs
    if {"baseline", "hardened"} <= set(controls):
        rates = df.pivot_table(index="test", columns="control", values="passed", aggfunc="mean")
        better = rates[rates["hardened"] > rates["baseline"]].index.tolist()
        worse = rates[rates["hardened"] < rates["baseline"]].index.tolist()
        out.append("## Effect of hardened controls")
        out.append("")
        out.append("Improved by controls ({}): {}".format(len(better), ", ".join(better) or "none"))
        out.append("")
        out.append("Worse with controls ({}): {}".format(len(worse), ", ".join(worse) or "none"))
        out.append("")
        flaky = [t for t in rates.index
                 if any(0 < rates.loc[t, c] < 1 for c in ("baseline", "hardened"))]
        if runs > 1:
            out.append("Inconsistent across runs ({}): {}".format(len(flaky), ", ".join(flaky) or "none"))
            out.append("")

    return "\n".join(out)


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "results/results.json"
    if not Path(path).exists():
        sys.exit("Results file not found: {}. Run the Promptfoo eval first.".format(path))

    df = load_results(path)
    if df.empty:
        sys.exit("No results found in {}.".format(path))

    report = build_report(df)
    out_path = Path(path).with_name(Path(path).name.replace("results", "findings", 1)).with_suffix(".md")
    out_path.write_text(report)
    print(report)
    print("\nSaved to {}".format(out_path))


if __name__ == "__main__":
    main()
