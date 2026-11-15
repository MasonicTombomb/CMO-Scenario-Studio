# Building, signing and releasing

## What a release contains

| File | What it is |
| --- | --- |
| `CMO-Scenario-Studio-<version>-setup.exe` | The installer: installs per machine into `C:\Program Files\CMO Scenario Studio` (asks for administrator rights), adds Start-menu shortcuts, optionally a desktop icon and the `.cmoproj` file association, and an uninstaller. |
| `CMO-Scenario-Studio-<version>-win64.zip` | The same program as a portable folder. |
| `*.sha256` | SHA-256 checksums. The in-app updater checks the setup against its checksum before running it. |

The program, its built-in data (`templates.json`, `templates_uk.json`, `areas.json`, `callsigns.json`, the Lua
engine) and the docs and examples live in the install folder and are replaced by every update. Everything a user
creates or changes stays in their own profile and survives updates and uninstalling:

| Where | What |
| --- | --- |
| `%APPDATA%\CMOScenarioStudio\CMO Scenario Studio\` | your libraries (`templates.json`, `areas.json`, `callsigns.json`), export backups, `error.log` |
| `HKCU\Software\CMOScenarioStudio\CMO Scenario Studio` | settings (CMO folder, recent files, window layout, update preferences) |
| `%LOCALAPPDATA%\CMOScenarioStudio\CMO Scenario Studio\cache\` | map tile cache |
| wherever you save them (Documents by default) | your `.cmoproj` projects |

## Building locally

```bash
pip install -e .[dev] pyinstaller
python packaging/build_release.py
```

Needs [Inno Setup 6](https://jrsoftware.org/isinfo.php) for the installer (`winget install JRSoftware.InnoSetup`,
or set `ISCC` to `ISCC.exe`); `--no-installer` builds only the zip. The script builds the exe with PyInstaller,
signs it if signing is configured, smoke-tests it (export and, with CMO installed, a dry-run of the example),
builds the setup from `packaging/installer.iss`, smoke-tests the setup (silent per-user install into a temporary
folder, export with the installed copy, silent uninstall) and writes the zip and checksums to `release/`.

## Publishing

Bump `src/cmo_studio/__init__.py` and `pyproject.toml`, add `docs/releases/<version>.md`, commit, then push a tag:

```bash
git tag -a v1.6.0 -m "CMO Scenario Studio 1.6.0"
git push origin main v1.6.0
```

`.github/workflows/release.yml` (the only workflow) runs the tests, builds the setup and zip, and publishes the
GitHub release. Installed copies find it through the GitHub API (`releases/latest`) on their next start.

## Updates in the app

- At start-up (if *Settings > Check GitHub for a new version* is on) and from **Help > Check for updates**, the
  studio asks `api.github.com` for the latest release and compares versions.
- An installed copy offers **Download and install**: it downloads `...-setup.exe` and its `.sha256` from the
  release, checks the checksum (and, when the running copy is code-signed, that the setup is validly signed by the
  same publisher), then runs the setup silently and quits. The setup asks Windows for permission (UAC), replaces
  the program in Program Files and starts the new version.
- Portable (zip) copies and source checkouts are pointed at the release page instead.
- Only HTTPS addresses on github.com / githubusercontent.com are followed. *Skip this version* stops the start-up
  prompt for that version.

## Code signing

Unsigned builds work, but Windows SmartScreen warns about an unknown publisher on download and first run, and
the updater can only rely on the SHA-256 checksum. Signing needs a code-signing certificate from a trusted
authority; self-signed certificates do not help with SmartScreen. Options:

| Option | Cost | Notes |
| --- | --- | --- |
| [SignPath Foundation](https://signpath.org) | free for open-source projects | Apply with the GitHub repository; they sign builds produced by GitHub Actions. Certificate is issued to SignPath Foundation with your project name. |
| [Azure Artifact Signing](https://learn.microsoft.com/azure/trusted-signing/) (formerly Trusted Signing) | about US$10 a month | Microsoft-managed certificate, identity validation required (check availability for individuals in your country). Use `CMO_SIGN_ARGS` with signtool's `/dlib` and `/dmdf` options. |
| OV / EV certificate from a CA (Sectigo, DigiCert, SSL.com...) | roughly £150-500 a year | Keys must be on a hardware token or cloud HSM (CA/B Forum rules since 2023), so CI signing usually goes through the vendor's cloud signing service. |

Either way, the build script signs the exe, the setup and the uninstaller (SHA-256, RFC 3161 timestamp) once one
of these is set:

```text
CMO_SIGN_PFX=<file.pfx>  CMO_SIGN_PFX_PASSWORD=<password>    a certificate file
CMO_SIGN_ARGS=<signtool sign arguments>                       anything else signtool supports (/dlib, /sha1, /csp...)
```

In GitHub Actions, add the repository secrets `SIGN_PFX_BASE64` (the `.pfx`, base64-encoded) and
`SIGN_PFX_PASSWORD`; the release workflow then signs automatically and deletes the certificate file after the
build. For a cloud signing service, add its login step before *Build exe, installer and zip* and set
`CMO_SIGN_ARGS` instead.

Once releases are signed, an installed signed copy refuses updates that are unsigned or signed by someone else.
