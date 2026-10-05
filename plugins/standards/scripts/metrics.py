#!/usr/bin/env python3
"""Measure function length, cyclomatic complexity and parameter counts against the CPLX-01 budget.

Uses the `lizard` analyzer (pip install lizard), which supports C#, Java, Kotlin, JavaScript,
TypeScript, Python, Go, C/C++, Swift, Ruby, PHP, Scala, Rust and more.

Usage:
    python metrics.py PATH [--out FILE] [--compare BASELINE] [--exclude GLOB ...] [--top N]

Exit codes: 0 success, 1 ratchet violation (with --compare), 2 lizard not installed, 3 bad path.
"""
import argparse
import json
import os
import sys
from datetime import datetime, timezone

DEFAULT_EXCLUDES = [
    "*/.git/*", "*/node_modules/*", "*/bin/*", "*/obj/*", "*/dist/*", "*/build/*", "*/out/*",
    "*/vendor/*", "*/packages/*", "*/Migrations/*", "*/migrations/*", "*/generated/*",
    "*/Generated/*", "*.min.js", "*.Designer.cs", "*.designer.cs", "*.g.cs", "*.g.i.cs",
]
BUDGET = {"length": 30, "ccn": 10, "params": 4, "file_nloc": 300}
# Languages where "new" is a reserved word, so a function named "new" is a parser artifact
# (lizard reads object initializers such as `new() { ... }` as functions).
NEW_IS_RESERVED = (".cs", ".java")


def is_real_function(filename, fn):
    if fn.name == "*global*":
        return False
    short_name = fn.name.split("::")[-1].split(".")[-1]
    return not (short_name == "new" and filename.lower().endswith(NEW_IS_RESERVED))


def percentile(values, pct):
    if not values:
        return 0
    ordered = sorted(values)
    return ordered[round(pct / 100 * (len(ordered) - 1))]


def relative(path):
    return os.path.relpath(path).replace(os.sep, "/")


def analyze(path, excludes):
    try:
        import lizard
    except ImportError:
        print("The 'lizard' package is not installed. Install it with: pip install lizard", file=sys.stderr)
        sys.exit(2)
    functions, files = [], []
    for info in lizard.analyze([path], exclude_pattern=excludes):
        files.append({"file": relative(info.filename), "nloc": info.nloc})
        for fn in info.function_list:
            if not is_real_function(info.filename, fn):
                continue
            functions.append({
                "file": relative(info.filename), "line": fn.start_line, "name": fn.name,
                "length": fn.length, "nloc": fn.nloc,
                "ccn": fn.cyclomatic_complexity, "params": fn.parameter_count,
            })
    return functions, files


def summarize(path, functions, files, top):
    def distribution(key):
        values = [f[key] for f in functions]
        result = {"p" + str(p): percentile(values, p) for p in (50, 75, 90, 95)}
        result["max"] = max(values, default=0)
        return result

    def worst(key):
        ranked = sorted(functions, key=lambda f: f[key], reverse=True)[:top]
        return [{"location": f"{f['file']}:{f['line']}", "name": f["name"], key: f[key]} for f in ranked]

    return {
        "generated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "path": relative(path),
        "budget": BUDGET,
        "files": len(files),
        "functions": len(functions),
        "length": distribution("length"),
        "ccn": distribution("ccn"),
        "params": distribution("params"),
        "over_budget": {
            "length": sum(f["length"] > BUDGET["length"] for f in functions),
            "ccn": sum(f["ccn"] > BUDGET["ccn"] for f in functions),
            "params": sum(f["params"] > BUDGET["params"] for f in functions),
            "files": sum(f["nloc"] > BUDGET["file_nloc"] for f in files),
        },
        "worst": {"length": worst("length"), "ccn": worst("ccn"), "params": worst("params")},
        "largest_files": sorted(files, key=lambda f: f["nloc"], reverse=True)[:top],
    }


def print_summary(summary):
    print(f"Files: {summary['files']}  Functions: {summary['functions']}")
    for key, label in (("length", "Function length"), ("ccn", "Cyclomatic complexity"), ("params", "Parameters")):
        d = summary[key]
        print(f"{label:<22} p50={d['p50']} p75={d['p75']} p90={d['p90']} p95={d['p95']} max={d['max']}")
    ob, budget = summary["over_budget"], summary["budget"]
    print(f"Over budget: length>{budget['length']}: {ob['length']}  complexity>{budget['ccn']}: {ob['ccn']}  "
          f"params>{budget['params']}: {ob['params']}  files>{budget['file_nloc']} lines: {ob['files']}")
    for key in ("length", "ccn", "params"):
        print(f"Top {key}:")
        for item in summary["worst"][key][:5]:
            print(f"  {item[key]:>5}  {item['location']}  {item['name']}")


def compare(summary, baseline_path):
    with open(baseline_path, encoding="utf-8") as handle:
        baseline = json.load(handle)
    violations = []
    print(f"\nCompared with baseline from {baseline.get('generated', 'unknown date')}:")
    for key, current in summary["over_budget"].items():
        before = baseline.get("over_budget", {}).get(key, 0)
        delta = current - before
        marker = "  RATCHET VIOLATION" if delta > 0 else ""
        print(f"  over budget ({key}): {before} -> {current} ({delta:+d}){marker}")
        if delta > 0:
            violations.append(key)
    return violations


def main():
    parser = argparse.ArgumentParser(description="Measure code against the CPLX-01 complexity budget.")
    parser.add_argument("path", help="Directory or file to analyze")
    parser.add_argument("--out", help="Write the JSON summary to this file")
    parser.add_argument("--compare", help="Baseline JSON to compare with; exits 1 if any over-budget count rose")
    parser.add_argument("--exclude", action="append", default=[], help="Extra glob to exclude (repeatable)")
    parser.add_argument("--top", type=int, default=15, help="Number of worst offenders to keep per measure")
    args = parser.parse_args()

    if not os.path.exists(args.path):
        print(f"Path not found: {args.path}", file=sys.stderr)
        sys.exit(3)

    functions, files = analyze(args.path, DEFAULT_EXCLUDES + args.exclude)
    summary = summarize(args.path, functions, files, args.top)
    print_summary(summary)

    if args.out:
        os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as handle:
            json.dump(summary, handle, indent=2)
        print(f"\nWrote {args.out}")

    if args.compare:
        if compare(summary, args.compare):
            sys.exit(1)


if __name__ == "__main__":
    main()
