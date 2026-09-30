"""Stress-test the test suite and append the results to a markdown log.

    python tools/stress_test.py LOG.md [round ...]

Rounds: repeat, random, parallel, warnings, coverage (default: all). Each failing test is
listed with the command/seed that reproduces it, and the complete output of every pytest
run is appended to LOG.raw.log next to the report.
"""

import re
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PYTEST = [sys.executable, "-m", "pytest", "-o", "addopts=", "-q", "-rfE", "-p", "no:cacheprovider", "--timeout=120"]
FAIL_LINE = re.compile(r"^(FAILED|ERROR) (\S+)")
SUMMARY = re.compile(r"=+ (.*?(passed|failed|error).*?) in ([\d.]+)s")


RAW_LOG = None  # set in __main__: every run's full output is appended here
_run_no = 0


def run(args):
    global _run_no
    _run_no += 1
    started = time.monotonic()
    proc = subprocess.run(PYTEST + args, cwd=ROOT, capture_output=True, text=True)
    out = proc.stdout + proc.stderr
    if RAW_LOG:
        with open(RAW_LOG, "a") as f:
            f.write(f"\n{'=' * 100}\nRUN {_run_no}  {time.strftime('%H:%M:%S')}  exit={proc.returncode}  "
                    f"cmd: pytest {' '.join(args)}\n{'=' * 100}\n{out}")
    failures = [m.group(2) for line in out.splitlines() if (m := FAIL_LINE.match(line))]
    summary = next((m.group(1) for line in out.splitlines()[::-1] if (m := SUMMARY.search(line))), "no summary")
    return {"args": args, "code": proc.returncode, "failures": failures, "summary": summary,
            "secs": time.monotonic() - started, "out": out}


def section(log, title, runs, note=""):
    failing = Counter(f for r in runs for f in r["failures"])
    bad_runs = [r for r in runs if r["code"] != 0]
    with open(log, "a") as f:
        f.write(f"### {title}\n\n{note}\n\n" if note else f"### {title}\n\n")
        f.write(f"- Runs: {len(runs)}, failed runs: {len(bad_runs)}, "
                f"total time: {sum(r['secs'] for r in runs):.1f}s\n")
        f.write(f"- Example command: `pytest {' '.join(runs[0]['args'])}`\n")
        f.write(f"- Per-run results: " + ", ".join(
            f"#{i + 1} {'✅' if r['code'] == 0 else '❌'} {r['summary']} ({r['secs']:.1f}s)" for i, r in enumerate(runs)) + "\n")
        if not failing:
            f.write(f"- Result: **all runs green** ({runs[0]['summary']})\n\n")
            return failing
        f.write("- Result: **failures**\n\n| Test | Failed in runs | Reproduce with |\n|---|---|---|\n")
        for test, n in failing.most_common():
            repro = next(" ".join(r["args"]) for r in runs if test in r["failures"])
            f.write(f"| `{test}` | {n}/{len(runs)} | `pytest {repro}` |\n")
        f.write("\n<details><summary>First failing run output (tail)</summary>\n\n```\n")
        f.write("\n".join(bad_runs[0]["out"].splitlines()[-60:]))
        f.write("\n```\n</details>\n\n")
    return failing


def round_repeat(log, n=10):
    runs = [run(["-p", "no:randomly"]) for _ in range(n)]
    return section(log, f"Round 1 — Repetition ({n} identical full runs)", runs)


def round_random(log, n=15):
    runs = [run(["-p", "randomly", f"--randomly-seed={seed}"]) for seed in range(1, n + 1)]
    return section(log, f"Round 2 — Random order ({n} seeds)", runs,
                   "pytest-randomly shuffles module, class, and test order and reseeds `random`.")


def round_parallel(log, n=5):
    runs = [run(["-n", "8", "-p", "randomly", f"--randomly-seed={100 + i}"]) for i in range(n)]
    return section(log, f"Round 3 — Parallel (8 workers x {n} runs, random order)", runs,
                   "pytest-xdist runs tests concurrently in 8 processes, exposing shared files, globals, and system state.")


def round_warnings(log):
    runs = [run(["-p", "no:randomly", "-W", "error"])]
    return section(log, "Round 4 — Warnings as errors", runs)


def round_coverage(log):
    r = run(["-p", "no:randomly", "--cov=mhispr", "--cov-branch", "--cov-report=term-missing"])
    table = [l for l in r["out"].splitlines() if l.startswith(("Name", "mhispr/", "TOTAL", "---"))]
    with open(log, "a") as f:
        f.write("### Round 5 — Branch coverage\n\n```\n" + "\n".join(table) + "\n```\n\n")
    return Counter(r["failures"])


ROUNDS = {"repeat": round_repeat, "random": round_random, "parallel": round_parallel,
          "warnings": round_warnings, "coverage": round_coverage}

if __name__ == "__main__":
    log = Path(sys.argv[1])
    RAW_LOG = log.with_suffix(".raw.log")
    for name in sys.argv[2:] or list(ROUNDS):
        failing = ROUNDS[name](log)
        print(f"{name}: {'OK' if not failing else dict(failing)}", flush=True)
