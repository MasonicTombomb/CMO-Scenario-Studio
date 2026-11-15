"""Updates from GitHub releases: find the latest release, download its installer, verify it and hand over.

The studio's releases (github.com/<GITHUB_REPO>/releases) carry ``CMO-Scenario-Studio-<v>-setup.exe`` with a
``.sha256`` file next to it. An installed copy (one with an uninstaller next to the exe) downloads the setup into
a temporary folder, checks its SHA-256 against the release's checksum file and - when this copy is code-signed -
that the setup is signed by the same publisher, then runs it and quits; the setup replaces the program files in
Program Files and starts the new version. Portable (zip) copies and source checkouts are pointed at the release
page instead.

Only HTTPS URLs on github.com / githubusercontent.com are ever followed.
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
import tempfile
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional
from urllib.parse import urlparse

from . import APP_NAME, GITHUB_REPO, __version__
from .paths import app_dir, is_frozen

API_LATEST = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
RELEASES_PAGE = f"https://github.com/{GITHUB_REPO}/releases"
ALLOWED_HOSTS = ("github.com", "api.github.com", "objects.githubusercontent.com",
                 "release-assets.githubusercontent.com", "github-releases.githubusercontent.com")
USER_AGENT = f"CMO-Scenario-Studio/{__version__} (+https://github.com/{GITHUB_REPO})"


class UpdateError(Exception):
    pass


def parse_version(text: str) -> tuple[int, ...]:
    """'v1.5.2' / '1.5.2' / '1.6.0-beta' -> (1, 5, 2) / (1, 6, 0). Unparseable -> ()."""
    m = re.match(r"\s*v?(\d+(?:\.\d+)*)", text or "")
    if not m:
        return ()
    parts = [int(p) for p in m.group(1).split(".")]
    while len(parts) > 1 and parts[-1] == 0:
        parts.pop()
    return tuple(parts)


def is_newer(latest: str, current: str = __version__) -> bool:
    a, b = parse_version(latest), parse_version(current)
    return bool(a) and a > b


@dataclass
class Asset:
    name: str
    url: str
    size: int = 0


@dataclass
class ReleaseInfo:
    version: str
    tag: str
    name: str
    notes: str
    page: str
    published: str = ""
    assets: list[Asset] = field(default_factory=list)

    def asset(self, suffix: str) -> Optional[Asset]:
        return next((a for a in self.assets if a.name.lower().endswith(suffix.lower())), None)

    @property
    def installer(self) -> Optional[Asset]:
        return self.asset("-setup.exe")

    @property
    def installer_sha256(self) -> Optional[Asset]:
        return self.asset("-setup.exe.sha256")

    @property
    def is_newer(self) -> bool:
        return is_newer(self.version)


def _check_url(url: str) -> str:
    u = urlparse(url)
    if u.scheme != "https" or not any(u.hostname == h or (u.hostname or "").endswith("." + h)
                                      for h in ALLOWED_HOSTS):
        raise UpdateError(f"Refusing to download from an unexpected address: {url}")
    return url


class _SafeRedirects(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        _check_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


_opener = urllib.request.build_opener(_SafeRedirects)


def _open(url: str, timeout: float, accept: str = "application/octet-stream"):
    req = urllib.request.Request(_check_url(url), headers={"User-Agent": USER_AGENT, "Accept": accept})
    return _opener.open(req, timeout=timeout)


def release_from_json(d: dict) -> ReleaseInfo:
    tag = str(d.get("tag_name", ""))
    return ReleaseInfo(version=tag.lstrip("vV"), tag=tag, name=str(d.get("name") or tag),
                       notes=str(d.get("body") or ""), page=str(d.get("html_url") or RELEASES_PAGE),
                       published=str(d.get("published_at") or ""),
                       assets=[Asset(str(a.get("name", "")), str(a.get("browser_download_url", "")),
                                     int(a.get("size") or 0)) for a in d.get("assets", [])])


def fetch_latest(timeout: float = 10.0) -> ReleaseInfo:
    """The latest published (non-draft, non-prerelease) release."""
    try:
        with _open(API_LATEST, timeout, "application/vnd.github+json") as r:
            data = json.loads(r.read().decode("utf-8"))
    except UpdateError:
        raise
    except Exception as exc:  # noqa: BLE001 - network problems of every kind
        raise UpdateError(f"Could not reach GitHub: {exc}") from exc
    if "tag_name" not in data:
        raise UpdateError("GitHub did not return a release.")
    return release_from_json(data)


def expected_sha256(text: str, filename: str) -> str:
    """Parse a 'digest  filename' checksum file."""
    for line in text.splitlines():
        parts = line.strip().split()
        if len(parts) >= 1 and re.fullmatch(r"[0-9a-fA-F]{64}", parts[0]):
            if len(parts) == 1 or parts[-1].lstrip("*") == filename:
                return parts[0].lower()
    raise UpdateError(f"No SHA-256 checksum for {filename} in the release.")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def download(url: str, dest: Path, progress: Optional[Callable[[int, int], bool]] = None,
             timeout: float = 30.0) -> Path:
    """Download ``url`` to ``dest``. ``progress(done, total)`` may return False to cancel."""
    tmp = dest.with_suffix(dest.suffix + ".part")
    try:
        with _open(url, timeout) as r, open(tmp, "wb") as f:
            total = int(r.headers.get("Content-Length") or 0)
            done = 0
            while True:
                chunk = r.read(1 << 16)
                if not chunk:
                    break
                f.write(chunk)
                done += len(chunk)
                if progress is not None and progress(done, total) is False:
                    raise UpdateError("Download cancelled.")
    except UpdateError:
        tmp.unlink(missing_ok=True)
        raise
    except Exception as exc:  # noqa: BLE001
        tmp.unlink(missing_ok=True)
        raise UpdateError(f"Download failed: {exc}") from exc
    tmp.replace(dest)
    return dest


# ------------------------------------------------------------------ Authenticode
@dataclass
class Signature:
    status: str          # 'Valid', 'NotSigned', 'HashMismatch', ... (PowerShell SignatureStatus) or 'Unknown'
    subject: str = ""

    @property
    def valid(self) -> bool:
        return self.status == "Valid"


def authenticode(path: Path) -> Signature:
    """Authenticode status of a file (Windows only; 'Unknown' elsewhere or on failure)."""
    if sys.platform != "win32":
        return Signature("Unknown")
    ps = ("$s = Get-AuthenticodeSignature -LiteralPath $env:CMO_SIG_PATH; "
          "Write-Output $s.Status; Write-Output $s.SignerCertificate.Subject")
    try:
        res = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", ps], capture_output=True,
                             text=True, timeout=30, env={**_env(), "CMO_SIG_PATH": str(path)},
                             creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    except (OSError, subprocess.SubprocessError):
        return Signature("Unknown")
    lines = [ln.strip() for ln in res.stdout.splitlines()]
    return Signature(lines[0] if lines and lines[0] else "Unknown", lines[1] if len(lines) > 1 else "")


def _env() -> dict:
    import os
    return dict(os.environ)


# ------------------------------------------------------------------ install modes
def install_mode() -> str:
    """'installed' (setup with an uninstaller), 'portable' (zip) or 'source' (running from a checkout)."""
    if not is_frozen():
        return "source"
    return "installed" if any(app_dir().glob("unins*.exe")) else "portable"


def verify_installer(path: Path, sha_text: str, current_exe: Optional[Path] = None) -> Signature:
    """Check the downloaded setup's SHA-256 and, when this copy is signed, its publisher. Raises UpdateError."""
    want = expected_sha256(sha_text, path.name)
    got = sha256_file(path)
    if got != want:
        raise UpdateError(f"The download does not match the release checksum.\nExpected {want}\nGot      {got}")
    sig = authenticode(path)
    me = authenticode(current_exe) if current_exe else Signature("Unknown")
    if me.valid:
        if not sig.valid:
            raise UpdateError(f"The installer is not validly signed ({sig.status}); this copy of {APP_NAME} is. "
                              "Not installing it.")
        if sig.subject != me.subject:
            raise UpdateError(f"The installer is signed by a different publisher:\n{sig.subject}")
    elif sig.status in ("HashMismatch", "NotTrusted", "Incompatible"):
        raise UpdateError(f"The installer's signature is broken ({sig.status}).")
    return sig


def prepare_update(release: ReleaseInfo, progress: Optional[Callable[[int, int], bool]] = None,
                   folder: Optional[Path] = None) -> tuple[Path, Signature]:
    """Download and verify the release's installer. Returns (setup path, its signature)."""
    setup = release.installer
    sha = release.installer_sha256
    if setup is None or sha is None:
        raise UpdateError(f"Release {release.version} has no installer to download.")
    folder = folder or Path(tempfile.mkdtemp(prefix="cmo-studio-update-"))
    with _open(sha.url, 30.0) as r:
        sha_text = r.read(4096).decode("utf-8", "replace")
    path = download(setup.url, folder / setup.name, progress)
    exe = Path(sys.executable) if is_frozen() else None
    return path, verify_installer(path, sha_text, exe)


def launch_installer(setup: Path, silent: bool = True) -> None:
    """Start the setup (it asks for administrator rights itself) and return; the caller then quits."""
    if sys.platform != "win32":
        raise UpdateError("Installing updates is only supported on Windows.")
    import ctypes
    params = "/SILENT /SUPPRESSMSGBOXES /NORESTART /CLOSEAPPLICATIONS" if silent else ""
    rc = ctypes.windll.shell32.ShellExecuteW(None, "open", str(setup), params, str(setup.parent), 1)
    if rc <= 32:
        raise UpdateError(f"Could not start the installer (error {rc}).")
