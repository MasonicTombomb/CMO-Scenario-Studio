"""Build the Windows release in release/:

    CMO-Scenario-Studio-<version>-setup.exe (+ .sha256)   installer for Program Files (Inno Setup 6)
    CMO-Scenario-Studio-<version>-win64.zip (+ .sha256)   portable copy

    python packaging/build_release.py                  build, sign (if configured), installer, smoke tests, zip
    python packaging/build_release.py --no-test        skip the smoke tests
    python packaging/build_release.py --no-installer   portable zip only

Needs: pip install -e .[dev] pyinstaller, and Inno Setup 6 (ISCC.exe on PATH, in its default folder, or set ISCC).

Code signing (optional) - set one of:
    CMO_SIGN_PFX=<file.pfx> and CMO_SIGN_PFX_PASSWORD=<password>    sign with a certificate file
    CMO_SIGN_ARGS=<signtool sign arguments>                          any other signtool setup, e.g. Azure Trusted
                                                                     Signing with /dlib ... /dmdf ...
The exe, the setup and its uninstaller are then signed and timestamped with SHA-256. Set SIGNTOOL to
signtool.exe if it is not on PATH or in the Windows SDK.
"""

from __future__ import annotations

import hashlib
import os
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile
from pathlib import Path
from typing import Optional

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "src"))

from cmo_studio import APP_NAME, __version__  # noqa: E402

DIST = ROOT / "build" / "dist"
WORK = ROOT / "build" / "work"
RELEASE = ROOT / "release"
APP = "CMO-Scenario-Studio"
TIMESTAMP = os.environ.get("CMO_SIGN_TIMESTAMP", "http://timestamp.digicert.com")

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


# ------------------------------------------------------------------ code signing
def find_signtool() -> Optional[str]:
    if os.environ.get("SIGNTOOL"):
        return os.environ["SIGNTOOL"]
    found = shutil.which("signtool")
    if found:
        return found
    kits = sorted(Path(r"C:\Program Files (x86)\Windows Kits\10\bin").glob("10.*/x64/signtool.exe"))
    return str(kits[-1]) if kits else None


def sign_args() -> Optional[list[str]]:
    """The signtool 'sign' arguments (without the file), or None when signing is not configured."""
    if os.environ.get("CMO_SIGN_ARGS"):
        return ["sign", *shlex.split(os.environ["CMO_SIGN_ARGS"], posix=False)]
    pfx = os.environ.get("CMO_SIGN_PFX")
    if pfx:
        return ["sign", "/fd", "sha256", "/tr", TIMESTAMP, "/td", "sha256", "/f", pfx,
                "/p", os.environ.get("CMO_SIGN_PFX_PASSWORD", "")]
    return None


def sign(*files: Path) -> bool:
    """Sign files when signing is configured; returns whether it was."""
    args, tool = sign_args(), find_signtool()
    if args is None:
        print("code signing: not configured (unsigned build)")
        return False
    if tool is None:
        raise SystemExit("Code signing is configured but signtool.exe was not found (set SIGNTOOL).")
    for f in files:
        subprocess.run([tool, *args, str(f)], check=True)     # not echoed: the arguments may hold a password
        print(f"signed: {f.name}")
    return True


# ------------------------------------------------------------------ installer
def find_iscc() -> Optional[str]:
    if os.environ.get("ISCC"):
        return os.environ["ISCC"]
    found = shutil.which("iscc")
    if found:
        return found
    for base in (os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"),
                 os.environ.get("ProgramFiles", r"C:\Program Files"),
                 os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs")):
        p = Path(base) / "Inno Setup 6" / "ISCC.exe"
        if p.is_file():
            return str(p)
    return None


def build_installer(out: Path) -> Path:
    iscc = find_iscc()
    if iscc is None:
        raise SystemExit("Inno Setup 6 was not found (install it, set ISCC, or pass --no-installer).")
    RELEASE.mkdir(exist_ok=True)
    cmd = [iscc, "/Q", f"/DAppVersion={__version__}", f"/DSourceDir={out}", f"/DOutputDir={RELEASE}"]
    args, tool = sign_args(), find_signtool()
    if args is not None and tool:
        quoted = " ".join(f"$q{a}$q" if " " in a else a for a in args)
        cmd += ["/DSign", f"/Scmostudio=$q{tool}$q {quoted} $f"]
    print("+", iscc, f"/DAppVersion={__version__}", "...", flush=True)   # not echoed in full: may hold a password
    subprocess.run([*cmd, str(HERE / "installer.iss")], check=True)
    setup = RELEASE / f"{APP}-{__version__}-setup.exe"
    if not setup.is_file():
        raise SystemExit(f"Inno Setup did not produce {setup}")
    return setup


def smoke_test_installer(setup: Path) -> None:
    """Install silently for the current user into a temp folder, export the example with it, uninstall."""
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp) / "app"
        log = Path(tmp) / "setup.log"
        subprocess.run([str(setup), "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART", "/CURRENTUSER", "/NOLAUNCH",
                        "/NOICONS", "/TASKS=", f"/DIR={target}", f"/LOG={log}"], check=True, timeout=300)
        exe = target / f"{APP}.exe"
        uninst = next(target.glob("unins*.exe"), None)
        if not exe.is_file() or uninst is None:
            raise SystemExit(f"Installer smoke test: {exe} or the uninstaller is missing.\n"
                             f"{log.read_text(errors='replace') if log.is_file() else ''}")
        smoke_test(target)
        subprocess.run([str(uninst), "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART"], check=True, timeout=300)
        for _ in range(120):            # the uninstaller finishes in a child process
            if not exe.exists():
                break
            time.sleep(0.5)
        if exe.exists():
            raise SystemExit("Installer smoke test: the uninstaller left the program behind.")
    print("installer smoke test: OK (silent install, export, uninstall)")


# ------------------------------------------------------------------ tests and packaging
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


def write_sha256(path: Path) -> str:
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    (path.parent / (path.name + ".sha256")).write_text(f"{digest}  {path.name}\n", encoding="utf-8")
    return digest


def package(out: Path) -> Path:
    RELEASE.mkdir(exist_ok=True)
    zpath = RELEASE / f"{APP}-{__version__}-win64.zip"
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for p in sorted(out.rglob("*")):
            if p.is_file():
                z.write(p, f"{APP}-{__version__}/{p.relative_to(out).as_posix()}")
    digest = write_sha256(zpath)
    print(f"release: {zpath} ({zpath.stat().st_size / 1e6:.1f} MB)\nsha256:  {digest}")
    return zpath


if __name__ == "__main__":
    test = "--no-test" not in sys.argv
    folder = build()
    signed = sign(folder / f"{APP}.exe")
    if test:
        smoke_test(folder)
    if "--no-installer" not in sys.argv:
        setup = build_installer(folder)
        if test:
            smoke_test_installer(setup)
        digest = write_sha256(setup)
        print(f"installer: {setup} ({setup.stat().st_size / 1e6:.1f} MB){' - signed' if signed else ''}\n"
              f"sha256:  {digest}")
    package(folder)
