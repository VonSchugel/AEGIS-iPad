import json
from pathlib import Path

from click.testing import CliRunner

from aegis.cli import main


def invoke(runner, tmp_path, *args):
    return runner.invoke(main, ["--db", str(tmp_path / "evidence.sqlite"), *args])


def test_commands_simulate_export_and_linux(tmp_path):
    runner = CliRunner()
    simulation = invoke(runner, tmp_path, "simulate")
    assert simulation.exit_code == 0, simulation.output
    assert json.loads(simulation.output)["native_linux_boot"] == "NOT TESTED"
    export = tmp_path / "evidence.jsonl"
    assert invoke(runner, tmp_path, "export-evidence", "--output", str(export)).exit_code == 0
    records = [json.loads(line) for line in export.read_text().splitlines()]
    assert records and all(record["payload"].get("simulated", True) for record in records)
    linux = invoke(runner, tmp_path, "linux-status")
    assert linux.exit_code == 0, linux.output
    assert "NOT_TESTED" in linux.output


def test_fixture_cannot_be_execute_input(tmp_path):
    runner = CliRunner()
    folder = tmp_path / "backup"
    folder.mkdir()
    binary = tmp_path / "fake"
    binary.write_bytes(b"fixture")
    result = invoke(runner, tmp_path, "execute", "--backup", str(folder), "--binary", str(binary))
    assert result.exit_code == 2
    assert json.loads(result.output)["error"]["code"] == "INTERACTIVE_APPROVAL_REQUIRED"


def test_untrusted_fixture_is_data_and_labeled(tmp_path):
    runner = CliRunner()
    fixture = tmp_path / "fixture.json"
    fixture.write_text(json.dumps({"simulated": True, "host": {"system": "Linux", "machine": "x86_64", "is_wsl": False}, "devices": [{"product_type": "iPad7,11", "product_version": "16.7.10", "build_version": "20H350", "usb_mode": "normal"}]}))
    result = invoke(runner, tmp_path, "compatibility", "--fixture", str(fixture))
    assert result.exit_code == 0, result.output
    assert json.loads(result.output)["simulated"] is True
    fixture.write_text(json.dumps({"simulated": False, "host": {}, "devices": []}))
    assert invoke(runner, tmp_path, "discover", "--fixture", str(fixture)).exit_code == 2


def test_research_snapshots_available_in_application(tmp_path):
    result = invoke(CliRunner(), tmp_path, "research")
    assert result.exit_code == 0, result.output
    output = json.loads(result.output)
    assert output["snapshots"]["compatibility"]
    assert output["rea"]["native_provider_verified"] is False
