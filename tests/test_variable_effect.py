"""
stata_registry — variable_effect contract tests.

Tests for Part 3 of the audit: validating the variable_effect field and
accessor contract for the shipped registry.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml


_REPO_ROOT = Path(__file__).resolve().parent.parent
_COMMANDS_DIR = _REPO_ROOT / "commands"


# ---------------------------------------------------------------------------
# 3.1 — Field existence
# ---------------------------------------------------------------------------

class TestVariableEffectPresence:
    """variable_effect is a required deliverable for do2py; confirm its status."""

    def test_variable_effect_in_schema(self):
        """The JSON schema defines a variable_effect field."""
        schema = json.loads((_COMMANDS_DIR / "schema.json").read_text())
        cmd_schema = (
            schema["properties"]["categories"]["additionalProperties"]
            ["properties"]["commands"]["items"]["properties"]
        )
        assert "variable_effect" in cmd_schema, (
            "variable_effect missing from schema.json"
        )
        assert "creates" in cmd_schema["variable_effect"]["enum"]
        assert "none" in cmd_schema["variable_effect"]["enum"]

    def test_variable_effect_documented_defaults(self):
        """README documents the resolved scalar primary-effect policy."""
        readme = (_REPO_ROOT / "README.md").read_text()
        for text in (
            "egen: creates",
            "recode: modifies",
            "merge`/`append`/`sort: restructures",
            "keep: removes",
        ):
            assert text in readme

    def test_variable_effect_optional_in_schema(self):
        """Entries without variable_effect still validate against the schema."""
        from jsonschema import validate, ValidationError

        schema = json.loads((_COMMANDS_DIR / "schema.json").read_text())
        cmd_props = {
            "type": "object",
            "properties": schema["properties"]["categories"]["additionalProperties"]
            ["properties"]["commands"]["items"]["properties"],
            "required": ["name"],
        }
        for entry in ({"name": "regress"}, {"name": "foo", "variable_effect": "creates"}):
            try:
                validate(instance=entry, schema=cmd_props)
            except ValidationError as exc:
                pytest.fail(f"Entry {entry} fails schema: {exc.message}")

    def test_variable_effect_invalid_value_rejected(self):
        """Invalid variable_effect values are rejected by the schema."""
        from jsonschema import validate, ValidationError

        schema = json.loads((_COMMANDS_DIR / "schema.json").read_text())
        cmd_props = {
            "type": "object",
            "properties": schema["properties"]["categories"]["additionalProperties"]
            ["properties"]["commands"]["items"]["properties"],
            "required": ["name"],
        }
        with pytest.raises(ValidationError):
            validate(instance={"name": "foo", "variable_effect": "explodes"}, schema=cmd_props)

    def test_variable_effect_complete_in_source_and_bundled_yaml(self):
        """Every source and bundled command has a valid effect value."""
        schema = json.loads((_COMMANDS_DIR / "schema.json").read_text())
        allowed = set(
            schema["properties"]["categories"]["additionalProperties"]
            ["properties"]["commands"]["items"]["properties"]
            ["variable_effect"]["enum"]
        )
        roots = (_COMMANDS_DIR, _REPO_ROOT / "stata_registry" / "data")
        for root in roots:
            for path in sorted(root.glob("*.yaml")):
                doc = yaml.safe_load(path.read_text())
                for category in doc["categories"].values():
                    for command in category.get("commands") or []:
                        effect = command.get("variable_effect")
                        assert effect in allowed, (
                            f"{path.name}:{command['name']} has invalid effect {effect!r}"
                        )

    def test_variable_effect_accessor_exists(self):
        """The module must expose a variable_effect() function."""
        import stata_registry as sr
        assert hasattr(sr, "variable_effect"), (
            "stata_registry has no variable_effect() function"
        )

    def test_variable_effect_full_stack(self):
        """
        End-to-end: variable_effect in YAML -> schema -> reader -> accessor.
        """
        import stata_registry as sr
        result = sr.variable_effect("generate")
        assert result == "creates"

    def test_variable_effect_keyerror_unknown(self):
        """variable_effect('notacommand') raises KeyError."""
        import stata_registry as sr
        with pytest.raises(KeyError):
            sr.variable_effect("notacommand")

    def test_variable_effect_valueerror_for_missing_field(self, monkeypatch):
        """A legacy entry without an effect raises ValueError."""
        import stata_registry as sr
        legacy_index = sr._build_index(
            [{"categories": {"legacy": {"commands": [{"name": "legacy"}]}}}]
        )
        monkeypatch.setattr(sr, "_index", legacy_index)
        with pytest.raises(ValueError):
            sr.variable_effect("legacy")
