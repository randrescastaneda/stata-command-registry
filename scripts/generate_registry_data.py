#!/usr/bin/env python3
"""Annotate source registries and regenerate the bundled package data."""

from __future__ import annotations

import argparse
import os
import tempfile
from pathlib import Path

import yaml


_ROOT = Path(__file__).resolve().parents[1]
_SOURCE_DIR = _ROOT / "commands"
_BUNDLED_DIR = _ROOT / "stata_registry" / "data"
_EVIDENCE_PATH = Path(__file__).with_name("source_driver_evidence.yaml")


def _command_entries(document: dict) -> list[dict]:
    entries: list[dict] = []
    for category in document.get("categories", {}).values():
        entries.extend(category.get("commands") or [])
    return entries


def _load_evidence() -> dict[str, dict]:
    document = yaml.safe_load(_EVIDENCE_PATH.read_text(encoding="utf-8"))
    evidence: dict[str, dict] = {}
    for entry in document.get("commands") or []:
        name = entry["name"]
        if name in evidence:
            raise ValueError(f"Duplicate source-driver evidence for {name!r}")
        if type(entry.get("include_driver")) is not bool:
            raise ValueError(f"Evidence for {name!r} must use a boolean value")
        evidence[name] = entry
    return evidence


def _expected_include_driver(name: str, evidence: dict[str, dict]) -> bool:
    return bool(evidence.get(name, {}).get("include_driver", False))


def _line_ending(line: str) -> str:
    if line.endswith("\r\n"):
        return "\r\n"
    if line.endswith("\n"):
        return "\n"
    if line.endswith("\r"):
        return "\r"
    return "\n"


def _command_name(line: str) -> str:
    raw_name = line.strip()[len("- name:") :].strip()
    name = yaml.safe_load(raw_name)
    if not isinstance(name, str) or not name:
        raise ValueError(f"Invalid command name line: {line.rstrip()!r}")
    return name


def _annotate_source_text(text: str, evidence: dict[str, dict]) -> str:
    """Add or replace include_driver while preserving source formatting."""
    lines = text.splitlines(keepends=True)
    output: list[str] = []
    index = 0

    while index < len(lines):
        line = lines[index]
        stripped = line.strip()
        if stripped == "# Run: python .process/scripts/generate_official_yaml.py":
            newline = "\n" if line.endswith("\n") else ""
            output.append(f"# Run: python scripts/generate_registry_data.py{newline}")
            index += 1
            continue
        if not stripped.startswith("- name:"):
            output.append(line)
            index += 1
            continue

        entry_indent = line[: len(line) - len(line.lstrip())]
        name = _command_name(stripped)
        newline = _line_ending(line)
        output.append(line if line.endswith(("\n", "\r")) else line + newline)
        output.append(
            f"{entry_indent}  include_driver: "
            f"{str(_expected_include_driver(name, evidence)).lower()}{newline}"
        )
        index += 1

        # Keep all other fields in their original order and remove any old
        # include_driver field so rerunning the generator is idempotent.
        while index < len(lines):
            candidate = lines[index]
            candidate_stripped = candidate.strip()
            candidate_indent = candidate[: len(candidate) - len(candidate.lstrip())]
            if (
                candidate_indent == entry_indent
                and candidate_stripped.startswith("- name:")
            ):
                break
            if candidate_stripped.startswith("include_driver:"):
                index += 1
                continue
            output.append(candidate)
            index += 1

    return "".join(output)


def _validate_document(document: dict, label: str, evidence: dict[str, dict]) -> None:
    for entry in _command_entries(document):
        value = entry.get("include_driver")
        if type(value) is not bool:
            raise ValueError(
                f"{label}:{entry['name']} must have a boolean include_driver"
            )
        expected = _expected_include_driver(entry["name"], evidence)
        if value is not expected:
            raise ValueError(
                f"{label}:{entry['name']} has include_driver={value}; "
                f"expected {expected} from {_EVIDENCE_PATH.name}"
            )


def _yaml_paths(directory: Path) -> list[Path]:
    return sorted(directory.glob("*.yaml"))


def _atomic_write(path: Path, text: str) -> None:
    descriptor, temporary_name = tempfile.mkstemp(
        dir=path.parent, prefix=f".{path.name}.", text=True
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="") as handle:
            handle.write(text)
        os.replace(temporary_name, path)
    except BaseException:
        Path(temporary_name).unlink(missing_ok=True)
        raise


def _write() -> None:
    evidence = _load_evidence()
    _BUNDLED_DIR.mkdir(parents=True, exist_ok=True)

    source_paths = _yaml_paths(_SOURCE_DIR)
    all_names = {
        entry["name"]
        for path in source_paths
        for entry in _command_entries(yaml.safe_load(path.read_text(encoding="utf-8")))
    }
    missing = sorted(set(evidence) - all_names)
    if missing:
        raise ValueError(
            f"Evidence names are absent from source data: {', '.join(missing)}"
        )

    generated: list[tuple[Path, str]] = []
    for source_path in source_paths:
        annotated = _annotate_source_text(
            source_path.read_text(encoding="utf-8"), evidence
        )
        _validate_document(yaml.safe_load(annotated), source_path.name, evidence)
        generated.append((source_path, annotated))

    for source_path, annotated in generated:
        _atomic_write(source_path, annotated)
        _atomic_write(_BUNDLED_DIR / source_path.name, annotated)


def _check() -> None:
    evidence = _load_evidence()
    source_paths = _yaml_paths(_SOURCE_DIR)
    bundled_paths = _yaml_paths(_BUNDLED_DIR)
    if [path.name for path in source_paths] != [path.name for path in bundled_paths]:
        raise ValueError("Source and bundled YAML file lists differ")

    all_names = {
        entry["name"]
        for path in source_paths
        for entry in _command_entries(yaml.safe_load(path.read_text(encoding="utf-8")))
    }
    missing = sorted(set(evidence) - all_names)
    if missing:
        raise ValueError(
            f"Evidence names are absent from source data: {', '.join(missing)}"
        )

    for source_path, bundled_path in zip(source_paths, bundled_paths):
        _validate_document(
            yaml.safe_load(source_path.read_text(encoding="utf-8")),
            source_path.name,
            evidence,
        )
        if source_path.read_bytes() != bundled_path.read_bytes():
            raise ValueError(f"Source and bundled data differ: {source_path.name}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="validate source classifications and source/bundle consistency",
    )
    args = parser.parse_args()
    if args.check:
        _check()
    else:
        _write()


if __name__ == "__main__":
    main()
