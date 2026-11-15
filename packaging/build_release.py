"""Build the Windows release: CMO-Scenario-Studio-<version>-win64.zip (+ .sha256) in release/.

    python packaging/build_release.py            build, smoke-test, zip
    python packaging/build_release.py --no-test  skip the smoke test

Needs: pip install -e .[dev] pyinstaller
"""

from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "src"))

from cmo_studio import APP_NAME, __version__  # noqa: E402

DIST = ROOT / "build" / "dist"
WORK = ROOT / "build" / "work"
RELEASE = ROOT / "release"
APP = "CMO-Scenario-Studio"

VERSION_INFO = """# UTF-8
VSVersionInfo(
  ffi=FixedFileInfo(filevers={t}, prodvers={t}, mask=0x3f, flags=0x0, OS=0x40004, fileType=0x1, subtype=0x0,
                    date=(0, 0)),
  kids=[
    StringFileInfo([StringTable('040904B0', [
      StringStruct('CompanyName', 'CMO Scenario Studio'),
      StringStruct('FileDescription', '{name}'),
      StringStruct('FileVersion', '{v}'),
      StringStruct('InternalName', '{app}'),
      StringStruct('LegalCopyright', 'MIT License'),
      StringStruct('OriginalFilename', '{app}.exe'),
      StringStruct('ProductName', '{name}'),
      StringStruct('ProductVersion', '{v}')])]),
    VarFileInfo([VarStruct('Translation', [1033, 1200])])
  ]
)
"""


def run(cmd: list[str], **kw) -> subprocess.CompletedProcess:
    print("+", " ".join(str(c) for c in cmd), flush=True)
    return subprocess.run(cmd, check=True, **kw)


def version_tuple(v: str) -> tuple[int, int, int, int]:
    parts = [int("".join(ch for ch in p if ch.isdigit()) or 0) for p in v.split(".")][:4]
    return tuple(parts + [0] * (4 - len(parts)))  # type: ignore[return-value]


def build() -> Path:
    env = dict(os.environ, QT_QPA_PLATFORM="offscreen")
    run([sys.executable, str(HERE / "make_icons.py")], env=env)
    (HERE / "version_info.txt").write_text(
        VERSION_INFO.format(t=version_tuple(__version__), v=__version__, name=APP_NAME, app=APP), encoding="utf-8")
    run([sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--distpath", str(DIST), "--workpath",
         str(WORK), str(HERE / "cmo_studio.spec")])
    out = DIST / APP
    # User-facing files next to the exe
    for name in ("README.md", "LICENSE", "THIRD_PARTY_NOTICES.md", "CHANGELOG.md"):
        shutil.copy2(ROOT / name, out / name)
    shutil.copytree(ROOT / "docs", out / "docs", dirs_exist_ok=True)
    ex = out / "examples"
    ex.mkdir(exist_ok=True)
    for p in (ROOT / "examples").glob("*.cmoproj"):
        shutil.copy2(p, ex / p.name)
    shutil.copytree(ROOT / "examples" / "output", ex / "output", dirs_exist_ok=True)
    (out / "README.txt").write_text(
        f"{APP_NAME} {__version__}\r\n\r\n"
        f"Run {APP}.exe. On first start choose your Command: Modern Operations folder if it is not found.\r\n"
        "Open examples\\Baltic Sentinel.cmoproj for a complete example.\r\n"
        "The user guide is docs\\USER_GUIDE.md.\r\n\r\n"
        "Command line (from a terminal):\r\n"
        f"  {APP}.exe project.cmoproj --dry-run\r\n"
        f"  {APP}.exe project.cmoproj --export <folder>\r\n", encoding="utf-8")
    return out


def smoke_test(out: Path) -> None:
    """Run the frozen exe headless: export + dry-run the example."""
    exe = out / f"{APP}.exe"
    with tempfile.TemporaryDirectory() as tmp:
        args = [str(exe), str(out / "examples" / "Baltic Sentinel.cmoproj"), "--export", tmp]
        if os.environ.get("CMO_DIR") or _cmo():
            args += ["--dry-run", "--cmo", os.environ.get("CMO_DIR") or str(_cmo())]
        res = subprocess.run(args, capture_output=True, text=True, timeout=180)
        built = Path(tmp) / "Lua" / "Baltic Sentinel" / "Build_Scenario.lua"
        if res.returncode != 0 or not built.is_file():
            raise SystemExit(f"Smoke test failed (exit {res.returncode}).\n{res.stdout}\n{res.stderr}")
    print("smoke test: OK (frozen exe exported" + (" and dry-ran" if "--dry-run" in args else "") + " the example)")


def _cmo():
    try:
        from cmo_studio.settings import detect_cmo_dir
        return detect_cmo_dir()
    except Exception:  # noqa: BLE001
        return None


def package(out: Path) -> Path:
    RELEASE.mkdir(exist_ok=True)
    zpath = RELEASE / f"{APP}-{__version__}-win64.zip"
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for p in sorted(out.rglob("*")):
            if p.is_file():
                z.write(p, f"{APP}-{__version__}/{p.relative_to(out).as_posix()}")
    digest = hashlib.sha256(zpath.read_bytes()).hexdigest()
    (RELEASE / (zpath.name + ".sha256")).write_text(f"{digest}  {zpath.name}\n", encoding="utf-8")
    print(f"release: {zpath} ({zpath.stat().st_size / 1e6:.1f} MB)\nsha256:  {digest}")
    return zpath


if __name__ == "__main__":
    folder = build()
    if "--no-test" not in sys.argv:
        smoke_test(folder)
    package(folder)
