"""Check a release is ready before tagging it.

    python tools/release_check.py            # everything, including both test runs and the git state
    python tools/release_check.py --ci       # what the release workflow checks (no tests, no git state)
    python tools/release_check.py --tag v1.9.1

Checks:
  * the version is the same in pyproject.toml, src/cmo_studio/__init__.py and the User Manual's About page
    (and matches --tag);
  * CHANGELOG.md starts with that version (not 'Unreleased') and docs/releases/<version>.md exists and names it;
  * the PDF manuals were rebuilt from the current sources (tools/make_manuals.py records a fingerprint);
  * every table the compiler produces is written into Build_Scenario.lua (1.9.0 shipped without its forecast);
  * the tests pass, with and without CMO (full run only);
  * git: on main, nothing uncommitted, not behind origin, and the tag does not exist yet (full run only).

Exits 1 if anything fails.
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tools"))

results: list[tuple[bool, str, str]] = []


def check(ok: bool, what: str, detail: str = "") -> bool:
    results.append((bool(ok), what, detail))
    return bool(ok)


def read(rel: str) -> str:
    p = ROOT / rel
    return p.read_text(encoding="utf-8") if p.is_file() else ""


def versions() -> dict[str, str]:
    found = {}
    m = re.search(r'^version\s*=\s*"([^"]+)"', read("pyproject.toml"), re.M)
    found["pyproject.toml"] = m.group(1) if m else "?"
    m = re.search(r'__version__\s*=\s*"([^"]+)"', read("src/cmo_studio/__init__.py"))
    found["src/cmo_studio/__init__.py"] = m.group(1) if m else "?"
    m = re.search(r"describes CMO Scenario Studio version ([0-9][0-9.]*[0-9])", read("docs/manual/user/00-about.md"))
    found["docs/manual/user/00-about.md"] = m.group(1) if m else "?"
    return found


def check_version(tag: str | None) -> str:
    found = versions()
    v = found["src/cmo_studio/__init__.py"]
    same = len(set(found.values())) == 1
    check(same, f"Version {v} everywhere", "" if same else ", ".join(f"{k}: {x}" for k, x in found.items()))
    if tag:
        check(tag.lstrip("v") == v, f"Tag {tag} matches the version", f"the code says {v}")
    return v


def check_notes(v: str) -> None:
    first = re.search(r"^## (.+)$", read("CHANGELOG.md"), re.M)
    head = first.group(1).strip() if first else ""
    check(head.startswith(v + " "), "CHANGELOG.md starts with this version",
          f"its first heading is '{head}'" if head else "no '## <version>' heading")
    notes = read(f"docs/releases/{v}.md")
    check(bool(notes), f"Release notes docs/releases/{v}.md exist")
    if notes:
        check(v in notes.splitlines()[0] and f"CMO-Scenario-Studio-{v}-setup.exe" in notes,
              "Release notes name this version and its downloads")


def check_manuals() -> None:
    import make_manuals
    for _src, _title, pdf, _blurb in make_manuals.MANUALS.values():
        p = make_manuals.OUT / pdf
        check(p.is_file() and p.read_bytes()[:5] == b"%PDF-", f"{pdf} is there")
    recorded = make_manuals.DIGEST.read_text(encoding="utf-8").strip() if make_manuals.DIGEST.is_file() else ""
    current = make_manuals.sources_digest()
    check(recorded == current, "PDF manuals were rebuilt from the current sources and version",
          "run: python tools/make_manuals.py" if recorded != current else "")


def check_build_tables() -> None:
    from cmo_studio.export.compiler import compile_build_data
    from cmo_studio.export.exporter import Exporter
    from cmo_studio.model.project import Project
    example = ROOT / "examples" / "Baltic Sentinel.cmoproj"
    p = Project.load(example)
    lua = Exporter(p).build_scenario_lua()
    missing = [k for k in compile_build_data(p) if f"D.{k} = " not in lua]
    check(not missing, "Every build table reaches Build_Scenario.lua", ", ".join(missing))


def check_tests() -> None:
    env = dict(os.environ, QT_QPA_PLATFORM="offscreen")
    for label, extra in (("Tests pass", {}), ("Tests pass without CMO", {"CMO_STUDIO_TEST_NO_CMO": "1"})):
        r = subprocess.run([sys.executable, "-m", "pytest", "-q"], cwd=ROOT, env=dict(env, **extra),
                           capture_output=True, text=True)
        last = (r.stdout.strip().splitlines() or ["(no output)"])[-1]
        check(r.returncode == 0, label, last)


def git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True).stdout.strip()


def check_git(v: str) -> None:
    branch = git("branch", "--show-current")
    check(branch == "main", "On main", f"on '{branch}'")
    dirty = git("status", "--porcelain")
    check(not dirty, "Nothing uncommitted", f"{len(dirty.splitlines())} changed file(s)")
    git("fetch", "-q", "--tags")
    counts = git("rev-list", "--left-right", "--count", "main...origin/main").split()
    behind = int(counts[1]) if len(counts) == 2 else 0
    check(behind == 0, "Not behind GitHub", f"{behind} commit(s) on origin/main not here")
    check(not git("tag", "-l", f"v{v}"), f"Tag v{v} not used yet")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--ci", action="store_true", help="skip the test runs and the git checks")
    ap.add_argument("--tag", help="the tag being released, e.g. v1.9.1")
    ap.add_argument("--no-tests", action="store_true", help="skip the test runs")
    a = ap.parse_args(argv)
    results.clear()
    v = check_version(a.tag)
    check_notes(v)
    check_manuals()
    check_build_tables()
    if not (a.ci or a.no_tests):
        check_tests()
    if not a.ci:
        check_git(v)
    width = max(len(w) for _ok, w, _d in results)
    for ok, what, detail in results:
        print(f"  {'[ok]  ' if ok else '[FAIL]'} {what.ljust(width)}  {'' if ok else detail}".rstrip())
    bad = sum(1 for ok, *_ in results if not ok)
    print(f"\n{'Ready to release' if not bad else f'{bad} problem(s): not ready to release'} ({v}).")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
