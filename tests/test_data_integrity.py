"""
stata_registry — data integrity tests.

Tests for Part 1 of the audit: schema conformance, uniqueness,
required fields, reserved words, and coverage claims.

These tests are read-only: they inspect the YAML source files on disk and the
built index, without modifying any data.
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import pytest
import yaml

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
_REPO_ROOT = Path(__file__).resolve().parent.parent
_COMMANDS_DIR = _REPO_ROOT / "commands"
_SCHEMA_PATH = _COMMANDS_DIR / "schema.json"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_all_entries() -> list[tuple[str, dict, str]]:
    """Return (name, cmd_dict, filename) for every command in every YAML."""
    entries: list[tuple[str, dict, str]] = []
    for yf in sorted(_COMMANDS_DIR.glob("*.yaml")):
        doc = yaml.safe_load(yf.read_text())
        if not doc or "categories" not in doc:
            continue
        for cat_key, cat_val in doc["categories"].items():
            for cmd in cat_val.get("commands") or []:
                entries.append((cmd.get("name", "<MISSING>"), cmd, yf.name))
    return entries


def _load_all_docs() -> list[tuple[Path, dict]]:
    docs = []
    for yf in sorted(_COMMANDS_DIR.glob("*.yaml")):
        doc = yaml.safe_load(yf.read_text())
        docs.append((yf, doc))
    return docs


# ---------------------------------------------------------------------------
# 1.1 — Schema conformance
# ---------------------------------------------------------------------------

class TestSchemaConformance:
    """Every YAML file must validate against commands/schema.json."""

    @pytest.fixture(autouse=True)
    def _load_schema(self):
        self.schema = json.loads(_SCHEMA_PATH.read_text())

    def test_all_files_present(self):
        """At least the three expected YAML files exist."""
        names = sorted(p.name for p in _COMMANDS_DIR.glob("*.yaml"))
        assert "official_stata_commands.yaml" in names
        assert "ssc_contributed_commands.yaml" in names
        assert "github_contributed_commands.yaml" in names

    @pytest.mark.parametrize(
        "filename",
        sorted(p.name for p in _COMMANDS_DIR.glob("*.yaml")),
    )
    def test_file_validates_schema(self, filename):
        """Each YAML file must validate against the JSON schema."""
        from jsonschema import validate, ValidationError

        path = _COMMANDS_DIR / filename
        doc = yaml.safe_load(path.read_text())
        try:
            validate(instance=doc, schema=self.schema)
        except ValidationError as exc:
            pytest.fail(f"{filename} fails schema validation: {exc.message}")


# ---------------------------------------------------------------------------
# 1.2 — Uniqueness
# ---------------------------------------------------------------------------

class TestUniqueness:
    """No command name, abbreviation, or alias may collide."""

    def test_no_duplicate_names_within_file(self):
        """Each YAML file must not list the same command name twice."""
        for yf in sorted(_COMMANDS_DIR.glob("*.yaml")):
            doc = yaml.safe_load(yf.read_text())
            if not doc or "categories" not in doc:
                continue
            names = []
            for cat_val in doc["categories"].values():
                for cmd in cat_val.get("commands") or []:
                    names.append(cmd.get("name"))
            dupes = {k: v for k, v in Counter(names).items() if v > 1 and k is not None}
            assert not dupes, f"{yf.name} has duplicate names: {dupes}"

    def test_no_duplicate_names_across_files(self):
        """Command names must not collide across registry files."""
        names = []
        for yf in sorted(_COMMANDS_DIR.glob("*.yaml")):
            doc = yaml.safe_load(yf.read_text())
            if not doc or "categories" not in doc:
                continue
            for cat_val in doc["categories"].values():
                for cmd in cat_val.get("commands") or []:
                    names.append(cmd.get("name"))
        dupes = {k: v for k, v in Counter(names).items() if v > 1 and k is not None}
        assert not dupes, f"Cross-file duplicate names: {dupes}"

    def test_no_abbreviation_collides_with_name(self):
        """An abbreviation must not collide with another command's name."""
        all_names: set[str] = set()
        all_abbrevs: dict[str, set[str]] = {}
        for _name, cmd, _fn in _load_all_entries():
            if _name and _name != "<MISSING>":
                all_names.add(_name)
            for abbr in cmd.get("abbreviations") or []:
                all_abbrevs.setdefault(abbr, set()).add(cmd["name"])

        collisions = {
            abbr: sorted(maps_to)
            for abbr, maps_to in all_abbrevs.items()
            if abbr in all_names and maps_to != {abbr}
        }
        assert not collisions, f"Abbreviation-name collisions: {collisions}"

    def test_no_alias_collides_with_name(self):
        """An alias must not collide with another command's name."""
        all_names: set[str] = set()
        all_aliases: dict[str, set[str]] = {}
        for _name, cmd, _fn in _load_all_entries():
            if _name and _name != "<MISSING>":
                all_names.add(_name)
            for alias in cmd.get("aliases") or []:
                all_aliases.setdefault(alias, set()).add(cmd["name"])

        collisions = {
            alias: sorted(maps_to)
            for alias, maps_to in all_aliases.items()
            if alias in all_names and maps_to != {alias}
        }
        assert not collisions, f"Alias-name collisions: {collisions}"

    def test_no_abbreviation_collides_with_alias(self):
        """An abbreviation must not collide with a different command's alias."""
        all_abbrevs: dict[str, set[str]] = {}
        all_aliases: dict[str, set[str]] = {}
        for _name, cmd, _fn in _load_all_entries():
            for abbr in cmd.get("abbreviations") or []:
                all_abbrevs.setdefault(abbr, set()).add(cmd["name"])
            for alias in cmd.get("aliases") or []:
                all_aliases.setdefault(alias, set()).add(cmd["name"])

        collisions = {
            abbr: (sorted(all_abbrevs[abbr]), sorted(all_aliases[abbr]))
            for abbr in all_abbrevs
            if abbr in all_aliases
            and all_abbrevs[abbr] != all_aliases[abbr]
        }
        assert not collisions, f"Abbreviation-alias collisions: {collisions}"


# ---------------------------------------------------------------------------
# 1.3 — Required fields
# ---------------------------------------------------------------------------

class TestRequiredFields:
    def test_every_entry_has_name(self):
        """Every command entry must have a 'name' field."""
        for _name, cmd, fn in _load_all_entries():
            assert "name" in cmd, f"Entry missing 'name' in {fn}: {cmd}"

    def test_every_file_has_metadata(self):
        """Every YAML file must have a metadata block."""
        for yf, doc in _load_all_docs():
            assert "metadata" in doc, f"{yf.name} missing metadata"

    def test_metadata_has_version(self):
        for yf, doc in _load_all_docs():
            meta = doc.get("metadata", {})
            assert "version" in meta, f"{yf.name} metadata missing 'version'"

    def test_metadata_has_source(self):
        for yf, doc in _load_all_docs():
            meta = doc.get("metadata", {})
            assert "source" in meta, f"{yf.name} metadata missing 'source'"


# ---------------------------------------------------------------------------
# 1.4 — Reserved words
# ---------------------------------------------------------------------------

class TestReservedWords:
    """Stata control flow and program keywords must appear as entries."""

    RESERVED_WORDS = [
        "if", "else", "while", "foreach", "forvalues",
        "program", "end", "capture", "continue", "break", "exit",
    ]

    def _all_names(self) -> set[str]:
        names = set()
        for _name, cmd, _fn in _load_all_entries():
            names.add(cmd.get("name"))
        return names

    @pytest.mark.parametrize("word", RESERVED_WORDS)
    def test_reserved_word_present(self, word):
        all_names = self._all_names()
        assert word in all_names, (
            f"Reserved word '{word}' not found as a registry entry"
        )


# ---------------------------------------------------------------------------
# 1.5 — Coverage claim
# ---------------------------------------------------------------------------

class TestCoverageClaim:
    """README claims 569 official and 100 SSC commands."""

    def test_official_count(self):
        doc = yaml.safe_load(
            (_COMMANDS_DIR / "official_stata_commands.yaml").read_text()
        )
        count = sum(
            len(cat.get("commands", []))
            for cat in doc["categories"].values()
        )
        assert count == 567, f"Official commands: expected 567, got {count}"

    def test_ssc_count(self):
        doc = yaml.safe_load(
            (_COMMANDS_DIR / "ssc_contributed_commands.yaml").read_text()
        )
        count = sum(
            len(cat.get("commands", []))
            for cat in doc["categories"].values()
        )
        assert count == 100, f"SSC commands: expected 100, got {count}"
