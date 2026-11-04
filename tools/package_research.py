"""Package a reviewed text/source allowlist; exclude all private runtime state."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import zipfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    options = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    fixed = (".gitattributes", ".gitignore", "AGENTS.md", "pyproject.toml", "MANIFEST.in", "README.md", "NOTICE.md",
             "requirements-dev.lock", "CHANGELOG.md", "SETUP-iPadOS-17.0.3.md")
    candidates = [root / name for name in fixed]
    for folder, extensions in (("src/aegis", {".py", ".json"}), ("tests", {".py"}),
                               ("docs", {".md", ".json"}), ("config", {".json"}),
                               ("tools", {".py"}), (".github", {".yml", ".yaml"})):
        candidates.extend(path for path in (root / folder).rglob("*") if path.is_file() and path.suffix in extensions)
    candidates = sorted(set(candidates))
    entries, contents = [], {}
    for path in candidates:
        relative = path.relative_to(root).as_posix()
        assert not path.is_symlink() and path.resolve().is_relative_to(root), relative
        assert not any(part in {".aegis", ".venv", "private", "backups", "__pycache__"} for part in path.parts), relative
        content = path.read_bytes()
        entries.append({"path": relative, "bytes": len(content), "sha256": hashlib.sha256(content).hexdigest()})
        contents[relative] = content
    manifest = {"schema_version": 1, "checked_date": "2026-11-04", "package": "AEGIS research and engineering working tree",
                "baseline_revision": "b99da1cb313845392279792d5ce5701cc03eab99",
                "software_tests": {"passed": 269, "skipped": 3, "platform": "Windows AMD64 / Python 3.12.14"},
                "physical_device_modified": False, "native_linux_boot_verified": False,
                "release_published": False, "files": entries,
                "exclusions": ["Git metadata", "virtual environment", "runtime databases/logs", "device backups/identifiers", "external firmware/payload binaries"]}
    contents["PACKAGE-MANIFEST.json"] = (json.dumps(manifest, indent=2) + "\n").encode()
    options.output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(options.output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for relative, content in sorted(contents.items()):
            entry = zipfile.ZipInfo("AEGIS-iPad/" + relative, date_time=(2026, 11, 4, 0, 0, 0))
            entry.compress_type = zipfile.ZIP_DEFLATED
            entry.external_attr = 0o100644 << 16
            archive.writestr(entry, content)
    with zipfile.ZipFile(options.output) as archive:
        assert archive.testzip() is None
        for item in entries:
            assert hashlib.sha256(archive.read("AEGIS-iPad/" + item["path"])).hexdigest() == item["sha256"]
    checksum = hashlib.sha256(options.output.read_bytes()).hexdigest()
    options.output.with_suffix(".sha256").write_text(checksum + "  " + options.output.name + "\n", encoding="ascii")
    print(json.dumps({"files": len(entries), "bytes": options.output.stat().st_size, "sha256": checksum,
                      "manifest_verified": True, "private_runtime_state_included": False}))


if __name__ == "__main__":
    main()
