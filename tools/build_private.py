"""Run local tests and package only the private integration, docs and tests."""

from __future__ import annotations

import ast
import hashlib
import importlib.util
import json
import subprocess
import sys
import unittest
import zipfile
from datetime import UTC, datetime
from importlib.metadata import version
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = ROOT.parents[3] / "2026-10-15" / "15-10-2026-08-34-46"
OUTPUT = ROOT.parents[1] / "outputs" / "Aqara_M1S_Local_v0.6.0_STOCK_LAB_TEST"
DEPS = ROOT.parent / "aqara-m1s-060-testdeps"
sys.path.insert(0, str(DEPS))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(name, document):
    (ROOT / name).write_text(
        json.dumps(document, indent=2, ensure_ascii=True) + "\n", encoding="utf-8"
    )


def sources():
    lab = SOURCE_ROOT / "work" / "m1s_native_controller_v030_20261021"
    items = {
        "base_0.5.9_manifest": Path.home()
        / "Desktop/M1S/aqara_m1s_local_v0_5_9/custom_components/aqara_m1s_local/manifest.json",
        "stock_logical_light_contract": lab
        / "protocol/STOCK_LOGICAL_LIGHT_CONTRACT.txt",
        "stock_contract_modules": lab / "protocol/CONTRACT_MODULES.txt",
        "native_cli_ack_validator": lab / "stock/m1s_stock_cli.c",
        "physical_lab_probe": SOURCE_ROOT
        / "outputs/M1S_Controller_v0.2.0-lab_Proba_hub_2026-10-21.txt",
        "stock_mqtt_contract": SOURCE_ROOT
        / "outputs/M1S109_Interfete_stock_2026-10-21/Contracte_MQTT_stock.txt",
        "upstream_protocol_facts": SOURCE_ROOT
        / "work/m1s109_audit_20261021/research/AqaraGateway/custom_components/aqara_gateway/core/utils.py",
    }
    result = {}
    for label, path in items.items():
        if not path.is_file():
            raise FileNotFoundError(f"Evidence source is missing: {label}")
        result[label] = {
            "file": path.name,
            "sha256": digest(path),
            "bytes": path.stat().st_size,
        }
    write_json(
        "SOURCE_EVIDENCE.json",
        {
            "scope": "Local evidence fingerprints only; original private source content is not redistributed",
            "upstream_commit": "1a868ff7876a3bed74c59ed7d21a9d5d3883540e",
            "sources": result,
        },
    )


def main():
    if version("probatio") != "0.13.0":
        raise RuntimeError(
            "Tests require the target HA schema library probatio==0.13.0"
        )

    sources()
    component = ROOT / "custom_components/aqara_m1s_local"
    # Mechanical build outputs, never test dependencies, caches or personal data.
    (component / "translations/en.json").write_bytes(
        (component / "strings.json").read_bytes()
    )
    python_files = list((ROOT / "custom_components").rglob("*.py")) + list(
        (ROOT / "tests").glob("*.py")
    )
    for path in python_files:
        ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    json_files = [p for p in component.rglob("*.json")] + [ROOT / "hacs.json"]
    for path in json_files:
        json.loads(path.read_text(encoding="utf-8"))
    manifest = json.loads((component / "manifest.json").read_text())
    assert manifest["version"] == "0.6.0"
    assert manifest["domain"] == "aqara_m1s_local"
    code = "\n".join(
        path.read_text(encoding="utf-8") for path in component.glob("*.py")
    )
    for forbidden in (
        "/dev/ttyS1",
        "create_subprocess_exec",
        "setprop ",
        "kill -",
        "dd if=",
        "flash_erase",
    ):
        if forbidden in code:
            raise ValueError(f"Unexpected stock ownership mutation path: {forbidden}")
    if importlib.util.find_spec("ruff") is None:
        raise RuntimeError(
            "Build validation requires ruff in the local test environment"
        )
    for args in (
        ("check", "custom_components", "tests", "tools"),
        ("format", "--check", "custom_components", "tests", "tools"),
    ):
        completed = subprocess.run(
            [sys.executable, "-m", "ruff", *args],
            cwd=ROOT,
            check=False,
            env=__import__("os").environ | {"PYTHONPATH": str(DEPS)},
        )
        if completed.returncode:
            raise RuntimeError("Lint or formatting check failed")
    suite = unittest.defaultTestLoader.discover(str(ROOT / "tests"))
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    report = {
        "built_at_utc": datetime.now(UTC).isoformat(),
        "python": sys.version.split()[0],
        "schema_library": "probatio==0.13.0",
        "tests_run": result.testsRun,
        "failures": len(result.failures),
        "errors": len(result.errors),
        "skipped": len(result.skipped),
        "passed": result.wasSuccessful(),
        "syntax_files_checked": len(python_files),
        "json_files_checked": len(json_files),
        "lint": "ruff check and format --check passed",
        "test_kind": "synthetic protocol/runtime tests, localhost MQTT server, HA API test doubles",
        "real_home_assistant_boot": False,
        "physical_hub_test_this_build": False,
        "ha_installation_or_restart": False,
        "github_publication": False,
    }
    write_json("TEST_RESULTS.json", report)
    if not result.wasSuccessful():
        raise RuntimeError("Tests failed; no new archive produced")
    allowed = [
        ROOT / name
        for name in (
            "README.md",
            "CAPABILITATI.md",
            "PROVENANCE.md",
            "CHANGELOG.md",
            "hacs.json",
            "SOURCE_EVIDENCE.json",
            "TEST_RESULTS.json",
        )
    ]
    for folder in ("custom_components", "tests", "tools"):
        allowed += [
            p
            for p in (ROOT / folder).rglob("*")
            if p.is_file()
            and "__pycache__" not in p.parts
            and p.suffix in (".py", ".json", ".yaml", ".txt")
        ]
    files = {
        p.relative_to(ROOT).as_posix(): {"sha256": digest(p), "bytes": p.stat().st_size}
        for p in sorted(set(allowed))
    }
    write_json(
        "BUILD_MANIFEST.json",
        {
            "version": "0.6.0",
            "release": "STOCK_LAB_TEST",
            "private": True,
            "publication": "not_authorized",
            "files": files,
            "self_hash_note": "This manifest excludes its own hash; archive SHA256 is provided separately",
        },
    )
    allowed.append(ROOT / "BUILD_MANIFEST.json")
    OUTPUT.mkdir(parents=True, exist_ok=True)
    archive = OUTPUT / "Aqara_M1S_Local_v0.6.0_STOCK_LAB_TEST.zip"
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zipped:
        for path in sorted(set(allowed)):
            zipped.write(path, path.relative_to(ROOT).as_posix())
    with zipfile.ZipFile(archive) as zipped:
        if zipped.testzip() is not None:
            raise RuntimeError("Archive CRC check failed")
        expected = set(files) | {"BUILD_MANIFEST.json"}
        if set(zipped.namelist()) != expected:
            raise RuntimeError("Archive file list mismatch")
        for name, metadata in files.items():
            if hashlib.sha256(zipped.read(name)).hexdigest() != metadata["sha256"]:
                raise RuntimeError(f"Archive hash mismatch: {name}")
    sha = digest(archive)
    (OUTPUT / "SHA256SUMS.txt").write_text(f"{sha}  {archive.name}\n", encoding="ascii")
    for name in (
        "README.md",
        "CAPABILITATI.md",
        "TEST_RESULTS.json",
        "BUILD_MANIFEST.json",
    ):
        (OUTPUT / name).write_bytes((ROOT / name).read_bytes())
    print(
        json.dumps(
            {
                "archive": str(archive),
                "bytes": archive.stat().st_size,
                "sha256": sha,
                "files": len(allowed),
                "tests_passed": result.testsRun,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
