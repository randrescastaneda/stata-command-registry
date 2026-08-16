"""
stata_registry — variable_effect gap tests.

Tests for Part 3 of the audit: confirming the variable_effect field
is absent, and documenting the gap as a blocking issue for do2py.
"""
from __future__ import annotations

import inspect
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

    def test_variable_effect_not_in_schema(self):
        """The JSON schema does not define a variable_effect field."""
        import json
        schema = json.loads((_COMMANDS_DIR / "schema.json").read_text())
        cmd_schema = (
            schema["properties"]["categories"]["additionalProperties"]
            ["properties"]["commands"]["items"]["properties"]
        )
        assert "variable_effect" not in cmd_schema, (
            "variable_effect unexpectedly present in schema.json"
        )

    @pytest.mark.xfail(
        reason=(
            "BLOCKING for do2py: variable_effect field does not exist in any YAML "
            "file.  Without it, do2py cannot determine what effect a command has "
            "on variables without hardcoding command names, which violates its "
            "contract."
        ),
        strict=True,
    )
    def test_variable_effect_in_official_yaml(self):
        """At least one command in official YAML should have variable_effect."""
        doc = yaml.safe_load(
            (_COMMANDS_DIR / "official_stata_commands.yaml").read_text()
        )
        found = False
        for cat_val in doc["categories"].values():
            for cmd in cat_val.get("commands", []):
                if "variable_effect" in cmd:
                    found = True
                    break
        assert found, "variable_effect absent from all official commands"

    @pytest.mark.xfail(
        reason=(
            "BLOCKING for do2py: no variable_effect() accessor exists in the "
            "stata_registry module."
        ),
        strict=True,
    )
    def test_variable_effect_accessor_exists(self):
        """The module must expose a variable_effect() function."""
        import stata_registry as sr
        assert hasattr(sr, "variable_effect"), (
            "stata_registry has no variable_effect() function"
        )

    @pytest.mark.xfail(
        reason=(
            "BLOCKING for do2py: variable_effect field confirmed absent from "
            "schema.json, all YAML files, and the reader.  See audit report "
            "Part 3 for implementation plan."
        ),
        strict=True,
    )
    def test_variable_effect_full_stack(self):
        """
        End-to-end: variable_effect in YAML -> schema -> reader -> accessor.
        Fails because none of these exist yet.
        """
        import stata_registry as sr
        result = sr.variable_effect("generate")
        assert result == "creates"