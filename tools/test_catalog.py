"""Write a catalogue of every test, Python and Swift, with what each one checks:
python tools/test_catalog.py [OUT.md]   (default: logs/<timestamp>_test-catalog.md)

Descriptions come from the tests themselves: a test's docstring (Python) or the `///` comment
above its class (Swift) introduces each group, and each test's name is turned into a sentence
("test_no_text_box_copies_instead" -> "no text box copies instead").
"""
import ast
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def words(name):
    """test_fn_press_and_release / testCutsAtAPause -> 'fn press and release' / 'cuts at a pause'."""
    name = re.sub(r"^test_?", "", name)
    name = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", name).replace("_", " ")
    return name.strip().lower()


def first_line(doc):
    return (doc or "").strip().split("\n")[0].strip()


def python_tests():
    """{file: [(group, group_doc, [(test, description)])]} from tests/*.py."""
    out = {}
    for path in sorted((ROOT / "tests").glob("test_*.py")):
        tree = ast.parse(path.read_text())
        groups = []
        loose = [(n.name, first_line(ast.get_docstring(n)) or words(n.name))
                 for n in tree.body if isinstance(n, ast.FunctionDef) and n.name.startswith("test")]
        if loose:
            groups.append(("(module)", first_line(ast.get_docstring(tree)), loose))
        for node in tree.body:
            if isinstance(node, ast.ClassDef) and node.name.startswith("Test"):
                tests = [(n.name, first_line(ast.get_docstring(n)) or words(n.name))
                         for n in node.body if isinstance(n, ast.FunctionDef) and n.name.startswith("test")]
                if tests:
                    groups.append((node.name, first_line(ast.get_docstring(node)), tests))
        out[str(path.relative_to(ROOT))] = groups
    return out


def swift_tests():
    """{file: [(class, doc, [(test, description)])]} from macos/Tests/**/*.swift."""
    out = {}
    for path in sorted((ROOT / "macos" / "Tests").rglob("*.swift")):
        lines = path.read_text().splitlines()
        groups, current = [], None
        for i, line in enumerate(lines):
            m = re.match(r"\s*final class (\w+)\s*:\s*XCTestCase", line)
            if m:
                doc = []
                j = i - 1
                while j >= 0 and lines[j].strip().startswith("///"):
                    doc.insert(0, lines[j].strip()[3:].strip())
                    j -= 1
                current = (m.group(1), " ".join(doc), [])
                groups.append(current)
                continue
            m = re.match(r"\s*func (test\w+)\(", line)
            if m and current is not None:
                current[2].append((m.group(1), words(m.group(1))))
        groups = [g for g in groups if g[2]]
        if groups:
            out[str(path.relative_to(ROOT))] = groups
    return out


def render(title, suites):
    total = sum(len(t) for groups in suites.values() for _, _, t in groups)
    md = [f"## {title} — {total} tests\n"]
    for file, groups in suites.items():
        count = sum(len(t) for _, _, t in groups)
        md.append(f"### `{file}` ({count})\n")
        for name, doc, tests in groups:
            md.append(f"**{name}**" + (f" — {doc}" if doc else "") + "\n")
            md += [f"- `{t}`: {d}" for t, d in tests]
            md.append("")
    return "\n".join(md), total


def main():
    stamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "logs" / f"{stamp}_test-catalog.md"
    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    py, py_total = render("Python (pytest)", python_tests())
    sw, sw_total = render("Swift (XCTest)", swift_tests())
    header = (f"# Test catalogue\n\nGenerated {datetime.now():%Y-%m-%d %H:%M} at commit `{commit}` by "
              f"`tools/test_catalog.py`. {py_total + sw_total} test functions: {py_total} Python, {sw_total} Swift "
              f"(parametrized Python tests run more cases than they're listed here).\n\n"
              "Each group's description is the test class's own docstring or comment; each line is the test's name "
              "read as a sentence.\n")
    out.write_text(header + "\n" + py + "\n" + sw)
    print(f"wrote {out} ({py_total} Python + {sw_total} Swift)")


if __name__ == "__main__":
    main()
