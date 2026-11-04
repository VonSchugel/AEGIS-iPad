"""Verify an isolated installed wheel without model, network or device access."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", required=True, type=Path)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    options = parser.parse_args()
    target, source = options.target.resolve(), options.source.resolve()
    sys.path.insert(0, str(target))
    import aegis
    from aegis.cli import main as cli
    from click.testing import CliRunner
    assert Path(aegis.__file__).resolve().is_relative_to(target), "Source checkout imported instead of installed wheel"
    checked = 0
    for path in source.joinpath("aegis").rglob("*"):
        if path.suffix in {".py", ".json"} and path.is_file():
            installed = target / path.relative_to(source)
            assert hashlib.sha256(installed.read_bytes()).digest() == hashlib.sha256(path.read_bytes()).digest(), path.name
            checked += 1
    runner = CliRunner()
    outcomes = {}
    with TemporaryDirectory(prefix="aegis-package-review-") as directory:
        database = Path(directory) / "evidence.sqlite"
        for scenario in ("success", "disconnect", "timeout", "partial", "unsupported"):
            result = runner.invoke(cli, ["--db", str(database), "simulate", "--scenario", scenario])
            assert result.exit_code == 0, result.output
            payload = json.loads(result.output)
            assert payload["simulated"] and payload["device_modified"] is False
            outcomes[scenario] = {"state": payload["state"], "status": payload["status"]}
        result = runner.invoke(cli, ["--db", str(database), "research"])
        assert result.exit_code == 0, result.output
        result = runner.invoke(cli, ["--db", str(database), "search-evidence", "PongoOS"])
        assert result.exit_code == 0, result.output
        results = json.loads(result.output)["results"]
        assert results and all(item["source_url"] and item["revision"] for item in results)
        result = runner.invoke(cli, ["linux-status"])
        assert result.exit_code == 0, result.output
        milestones = json.loads(result.output)["research_milestones"]
        assert [item["id"] for item in milestones] == [f"L{i}" for i in range(6)]
        assert all(item["physical_status"] == "NOT_TESTED" for item in milestones)
    summary = {"checked_date": "2026-11-04", "classification": "VERIFIED", "installed_import_isolated": True,
               "source_files_match": checked, "scenarios": outcomes, "source_search_results": len(results),
               "linux_milestones": "L0-L5 NOT_TESTED", "network_or_device_access": False,
               "limitations": ["Installed-wheel software smoke tests only; no hardware/provider verification", "Working-tree build retains existing project version; no release was published"]}
    options.output.parent.mkdir(parents=True, exist_ok=True)
    options.output.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
