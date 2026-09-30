"""Mutation testing: plant one small bug at a time and check the tests catch it.

    python tools/mutation_test.py LOG.md [module ...]

Each mutant is applied in a throwaway copy of the repo (the working tree is never
modified), and only the module's own test file(s) run. A mutant is "killed" when the
tests fail (or time out) and "survives" when they still pass: a survivor means no test
would notice that bug. Rendering code and debug logging are skipped: planting bugs in
colours or log text says nothing about correctness.
"""

import ast
import os
import shutil
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from queue import Queue

ROOT = Path(__file__).resolve().parent.parent
WORKERS = 8
TIMEOUT = 60

TESTS = {
    "cleanup": ["tests/test_cleanup.py"],
    "transcribe": ["tests/test_transcribe.py"],
    "storage": ["tests/test_storage.py"],
    "settings": ["tests/test_settings_models_setup.py"],
    "models": ["tests/test_settings_models_setup.py"],
    "setup": ["tests/test_settings_models_setup.py"],
    "levels": ["tests/test_settings_models_setup.py"],
    "audio": ["tests/test_audio.py"],
    "hotkey": ["tests/test_hotkey.py"],
    "context": ["tests/test_context_paste.py"],
    "paste": ["tests/test_context_paste.py"],
    "screens": ["tests/test_screens_sounds_app.py"],
    "sounds": ["tests/test_screens_sounds_app.py"],
    "app": ["tests/test_screens_sounds_app.py"],
    "draw": ["tests/test_draw.py"],
    "widget": ["tests/test_widget.py"],
    "threads": ["tests/test_threads.py"],
}

# Functions whose job is purely visual or process wiring (covered by render checks / manual runs).
SKIP_FUNCTIONS = {
    "draw", "_draw_mistake_card", "_draw_tooltip", "drawRect_", "log", "main", "__main__",
}

CMP_SWAP = {ast.Lt: ast.LtE, ast.LtE: ast.Lt, ast.Gt: ast.GtE, ast.GtE: ast.Gt,
            ast.Eq: ast.NotEq, ast.NotEq: ast.Eq, ast.In: ast.NotIn, ast.NotIn: ast.In,
            ast.Is: ast.IsNot, ast.IsNot: ast.Is}
BIN_SWAP = {ast.Add: ast.Sub, ast.Sub: ast.Add, ast.Mult: ast.Div, ast.Div: ast.Mult,
            ast.FloorDiv: ast.Div, ast.Mod: ast.Mult, ast.BitOr: ast.BitAnd, ast.BitAnd: ast.BitOr}


@dataclass
class Mutant:
    module: str
    line: int
    kind: str
    before: str
    after: str
    source: str  # full mutated module source


class Collector(ast.NodeVisitor):
    """Walks the AST and records (node, kind) mutation sites outside skipped functions."""

    def __init__(self):
        self.sites = []
        self._skip = 0
        self._docstrings = set()

    def visit_FunctionDef(self, node):
        skip = node.name in SKIP_FUNCTIONS
        self._skip += skip
        self._mark_docstring(node)
        self.generic_visit(node)
        self._skip -= skip

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_ClassDef(self, node):
        self._mark_docstring(node)
        self.generic_visit(node)

    def visit_Module(self, node):
        self._mark_docstring(node)
        self.generic_visit(node)

    def visit_If(self, node):
        if not self._skip and not _is_main_guard(node):
            self.sites.append((node, "negate-if"))
        if not _is_main_guard(node):
            self.generic_visit(node)

    def _mark_docstring(self, node):
        body = getattr(node, "body", [])
        if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant):
            self._docstrings.add(id(body[0].value))

    def generic_visit(self, node):
        if not self._skip:
            if isinstance(node, ast.Compare) and type(node.ops[0]) in CMP_SWAP:
                self.sites.append((node, "compare"))
            elif isinstance(node, ast.BinOp) and type(node.op) in BIN_SWAP:
                self.sites.append((node, "arith"))
            elif isinstance(node, ast.BoolOp):
                self.sites.append((node, "boolop"))
            elif isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
                self.sites.append((node, "drop-not"))
            elif isinstance(node, ast.Constant) and id(node) not in self._docstrings:
                if isinstance(node.value, bool) or (isinstance(node.value, (int, float)) and not isinstance(node.value, bool)):
                    self.sites.append((node, "constant"))
            elif isinstance(node, ast.Return) and node.value is not None and not (
                    isinstance(node.value, ast.Constant) and node.value.value is None):
                self.sites.append((node, "return-none"))
            elif isinstance(node, ast.Expr) and isinstance(node.value, ast.Call) and not _is_log_call(node.value):
                self.sites.append((node, "drop-call"))
        super().generic_visit(node)


def _is_main_guard(node):
    return isinstance(node.test, ast.Compare) and isinstance(node.test.left, ast.Name) and node.test.left.id == "__name__"


def _is_log_call(call):
    f = call.func
    name = f.id if isinstance(f, ast.Name) else f.attr if isinstance(f, ast.Attribute) else ""
    return name in {"log", "print"}


def _mutate(node, kind):
    """Mutate `node` in place; return an undo function, or None if not applicable."""
    if kind == "compare":
        old = node.ops[0]
        node.ops[0] = CMP_SWAP[type(old)]()
        return lambda: node.ops.__setitem__(0, old)
    if kind == "arith":
        old = node.op
        node.op = BIN_SWAP[type(old)]()
        return lambda: setattr(node, "op", old)
    if kind == "boolop":
        old = node.op
        node.op = ast.Or() if isinstance(old, ast.And) else ast.And()
        return lambda: setattr(node, "op", old)
    if kind == "constant":
        old = node.value
        if isinstance(old, bool):
            node.value = not old
        elif isinstance(old, int):
            node.value = old + 1
        else:
            node.value = old * 1.5 if old else 1.0
        return lambda: setattr(node, "value", old)
    raise ValueError(kind)


class Replacer(ast.NodeTransformer):
    """Statement-level mutations that replace a node with a different node."""

    def __init__(self, target, kind):
        self.target, self.kind = target, kind

    def visit(self, node):
        if node is self.target:
            if self.kind == "negate-if":
                node = ast.If(test=ast.UnaryOp(op=ast.Not(), operand=node.test), body=node.body, orelse=node.orelse)
            elif self.kind == "drop-not":
                return node.operand
            elif self.kind == "return-none":
                return ast.Return(value=ast.Constant(value=None))
            elif self.kind == "drop-call":
                return ast.Pass()
            return ast.copy_location(node, self.target)
        return self.generic_visit(node)


def mutants_for(module):
    path = ROOT / "mispr" / f"{module}.py"
    src = path.read_text()
    lines = src.splitlines()
    collector = Collector()
    collector.visit(ast.parse(src))
    out = []
    for i, (_, kind) in enumerate(collector.sites):
        tree = ast.parse(src)  # fresh tree per mutant
        fresh = Collector()
        fresh.visit(tree)
        node, _ = fresh.sites[i]
        line = getattr(node, "lineno", 0)
        before = lines[line - 1].strip() if line else ""
        if kind in ("compare", "arith", "boolop", "constant"):
            _mutate(node, kind)
        else:
            tree = Replacer(node, kind).visit(tree)
        ast.fix_missing_locations(tree)
        mutated = ast.unparse(tree)
        mutated_lines = mutated.splitlines()
        # Show the mutated line: find it by position in the unparsed output (best effort).
        after = _changed_line(ast.unparse(ast.parse(src)).splitlines(), mutated_lines)
        out.append(Mutant(module, line, kind, before, after, mutated))
    return out


def _changed_line(a, b):
    for x, y in zip(a, b):
        if x != y:
            return y.strip()
    return "(statement removed)" if len(b) < len(a) else ""


def _make_worktree(base):
    d = Path(tempfile.mkdtemp(prefix="mut-", dir=base))
    for name in ("mispr", "tests"):
        shutil.copytree(ROOT / name, d / name, ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copy(ROOT / "pyproject.toml", d / "pyproject.toml")
    return d


def run_mutant(worktrees, m):
    wt = worktrees.get()
    target = wt / "mispr" / f"{m.module}.py"
    original = (ROOT / "mispr" / f"{m.module}.py").read_text()
    try:
        target.write_text(m.source)
        cmd = [sys.executable, "-m", "pytest", "-o", "addopts=", "-q", "-x", "-p", "no:randomly",
               "-p", "no:cacheprovider", *TESTS[m.module]]
        try:
            proc = subprocess.run(cmd, cwd=wt, capture_output=True, text=True, timeout=TIMEOUT,
                                  env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})
            killed = proc.returncode != 0
            how = "killed" if killed else "SURVIVED"
        except subprocess.TimeoutExpired:
            killed, how = True, "killed (timeout)"
        return m, killed, how
    finally:
        target.write_text(original)
        worktrees.put(wt)


def main(log, modules):
    base = Path(tempfile.mkdtemp(prefix="mutation-"))
    worktrees = Queue()
    for _ in range(WORKERS):
        worktrees.put(_make_worktree(base))
    started = time.monotonic()
    results = []
    all_mutants = [m for mod in modules for m in mutants_for(mod)]
    print(f"{len(all_mutants)} mutants across {len(modules)} modules", flush=True)
    with ThreadPoolExecutor(WORKERS) as pool:
        for i, r in enumerate(pool.map(lambda m: run_mutant(worktrees, m), all_mutants), 1):
            results.append(r)
            if i % 50 == 0:
                print(f"  {i}/{len(all_mutants)}", flush=True)
    shutil.rmtree(base, ignore_errors=True)
    write_report(log, results, time.monotonic() - started, modules)
    return results


def write_report(log, results, secs, modules):
    raw = Path(log).with_suffix(".raw.log")
    with open(raw, "a") as f:
        f.write(f"\n{'=' * 100}\nMUTATION TESTING — every mutant\n{'=' * 100}\n")
        for m, killed, how in results:
            f.write(f"{how:<17} mispr/{m.module}.py:{m.line:<4} [{m.kind}]  {m.before}  -->  {m.after}\n")
    with open(log, "a") as f:
        total = len(results)
        killed = sum(k for _, k, _ in results)
        f.write(f"- Mutants: {total}, killed: {killed}, survived: {total - killed}, "
                f"**mutation score: {killed / total:.1%}** ({secs:.0f}s, {WORKERS} workers)\n\n")
        f.write("| Module | Mutants | Killed | Score |\n|---|---|---|---|\n")
        for mod in modules:
            rs = [r for r in results if r[0].module == mod]
            if rs:
                k = sum(x[1] for x in rs)
                f.write(f"| `{mod}` | {len(rs)} | {k} | {k / len(rs):.0%} |\n")
        survivors = [m for m, k, _ in results if not k]
        if survivors:
            f.write("\n**Surviving mutants** (a planted bug no test caught):\n\n| Location | Kind | Original | Mutated |\n|---|---|---|---|\n")
            for m in survivors:
                f.write(f"| `mispr/{m.module}.py:{m.line}` | {m.kind} | `{m.before.replace('|', '\\|')}` | `{m.after.replace('|', '\\|')}` |\n")
        f.write("\n")


if __name__ == "__main__":
    mods = sys.argv[2:] or list(TESTS)
    res = main(sys.argv[1], mods)
    print(f"survivors: {sum(not k for _, k, _ in res)}/{len(res)}")
