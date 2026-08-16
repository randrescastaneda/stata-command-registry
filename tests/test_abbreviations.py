"""
stata_registry — abbreviation semantics tests.

Tests for Part 2 of the audit: the reader must honour the convention
that YAML abbreviations are the set of tokens the package advertises,
and the reader must NOT generate intermediate forms on its own.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest
import yaml

_REPO_ROOT = Path(__file__).resolve().parent.parent
_COMMANDS_DIR = _REPO_ROOT / "commands"


# ---------------------------------------------------------------------------
# 2.1 — Reader contract: enumeration semantics
# ---------------------------------------------------------------------------

class TestAbbreviationSemantics:
    """The reader resolves ONLY tokens present in the abbreviations field."""

    def test_enumerated_abbreviation_resolves(self):
        """'regr' IS listed in the YAML for regress and must resolve."""
        import stata_registry as sr
        assert sr.canonical_command("regr") == "regress"

    def test_enumerated_intermediate_resolves(self):
        """'regre' IS listed in the YAML for regress and must resolve."""
        import stata_registry as sr
        assert sr.canonical_command("regre") == "regress"

    @pytest.mark.xfail(
        reason=(
            "Enumeration semantics: 'genr' is NOT listed in YAML for generate. "
            "The reader does NOT generate intermediate forms. "
            "If the contract changes to 'implied intermediates', this test should pass."
        ),
        strict=True,
    )
    def test_implied_intermediate_resolves(self):
        """If the contract were 'implied intermediates', genr would resolve."""
        import stata_registry as sr
        assert sr.canonical_command("genr") == "generate"

    def test_unlisted_form_does_not_resolve(self):
        """'genr' is NOT in the generate abbreviations list; must NOT resolve."""
        import stata_registry as sr
        with pytest.raises(KeyError):
            sr.canonical_command("genr")


# ---------------------------------------------------------------------------
# 2.3 — Non-abbreviable commands
# ---------------------------------------------------------------------------

class TestNonAbbreviableCommands:
    """Commands that Stata forbids abbreviating must have explicit signal."""

    @pytest.mark.xfail(
        reason=(
            "Defect: replace has no 'abbreviations' field.  There is no way to "
            "distinguish 'abbreviations deliberately forbidden' from 'entry not "
            "yet completed'.  An explicit abbreviations: [] meaning 'none allowed' "
            "is required; absence should mean 'unknown'."
        ),
        strict=False,
    )
    def test_replace_abbreviations_field_present(self):
        """replace must have an explicit abbreviations field (defect if absent)."""
        _assert_cmd_has_abbreviations_field("replace")

    @pytest.mark.xfail(
        reason="Same defect as replace: egen must have explicit abbreviations: []",
        strict=False,
    )
    def test_egen_abbreviations_field_present(self):
        _assert_cmd_has_abbreviations_field("egen")

    @pytest.mark.xfail(
        reason="Same defect: destring must have explicit abbreviations: []",
        strict=False,
    )
    def test_destring_abbreviations_field_present(self):
        _assert_cmd_has_abbreviations_field("destring")


def _assert_cmd_has_abbreviations_field(cmd_name: str):
    """Fail with a clear message if the command has no abbreviations field."""
    doc = yaml.safe_load(
        (_COMMANDS_DIR / "official_stata_commands.yaml").read_text()
    )
    for cat_val in doc["categories"].values():
        for cmd in cat_val.get("commands", []):
            if cmd["name"] == cmd_name:
                assert "abbreviations" in cmd, (
                    f"'{cmd_name}' entry has no 'abbreviations' field"
                )
                return
    pytest.fail(f"'{cmd_name}' not found in YAML")


# ---------------------------------------------------------------------------
# 2.4 — Verify against real Stata behaviour
# ---------------------------------------------------------------------------

class TestRealStataAbbreviations:
    """
    Verify abbreviations agree with Stata's documented abbreviation rules.

    In Stata, a command can be abbreviated to its shortest unambiguous prefix.
    Some commands cannot be abbreviated at all.
    """

    @pytest.mark.xfail(
        reason=(
            "Defect: 'g' is missing from generate's abbreviations list. "
            "The YAML lists [ge, gen, gene, gener, genera, generat] but Stata "
            "accepts 'g' as the shortest abbreviation for generate."
        ),
        strict=True,
    )
    def test_generate_abbreviates_to_g(self):
        """generate abbreviates to 'g' in Stata."""
        import stata_registry as sr
        assert sr.canonical_command("g") == "generate", (
            "generate must be reachable via 'g' — the shortest Stata abbreviation"
        )

    @pytest.mark.xfail(
        reason=(
            "Defect: 'g' is missing from generate's abbreviations list. "
            "The YAML lists [ge, gen, gene, gener, genera, generat] but Stata "
            "accepts 'g' as the shortest abbreviation for generate."
        ),
        strict=True,
    )
    def test_generate_shortest_abbreviation_in_yaml(self):
        """The YAML must include 'g' as an abbreviation for generate."""
        doc = yaml.safe_load(
            (_COMMANDS_DIR / "official_stata_commands.yaml").read_text()
        )
        for cat_val in doc["categories"].values():
            for cmd in cat_val.get("commands", []):
                if cmd["name"] == "generate":
                    assert "g" in cmd.get("abbreviations", [])
                    return
        pytest.fail("generate not found")

    def test_replace_not_abbreviable(self):
        """replace cannot be abbreviated in Stata."""
        import stata_registry as sr
        for prefix in ["r", "re", "rep", "repl", "repla", "replac"]:
            assert not sr.is_command(prefix), (
                f"'{prefix}' must not resolve to 'replace'"
            )

    def test_rename_abbreviation_ren(self):
        """rename abbreviates minimally to 'ren' in Stata."""
        import stata_registry as sr
        assert sr.canonical_command("ren") == "rename"
        assert sr.canonical_command("rena") == "rename"
        assert sr.canonical_command("renam") == "rename"

    def test_bysort_abbreviation_bys(self):
        """bysort abbreviates to 'by' in Stata."""
        import stata_registry as sr
        assert sr.canonical_command("by") == "bysort"
        assert sr.canonical_command("bys") == "bysort"

    def test_summarize_abbreviation_su(self):
        """summarize abbreviates to 'su' in Stata."""
        import stata_registry as sr
        assert sr.canonical_command("su") == "summarize"

    def test_egen_no_short_form(self):
        """egen cannot be abbreviated in Stata."""
        import stata_registry as sr
        for prefix in ["e", "eg"]:
            assert not sr.is_command(prefix), (
                f"'{prefix}' must not resolve to 'egen'"
            )

    def test_destring_no_short_form(self):
        """destring cannot be abbreviated in Stata.
        
        Note: 'de' resolves to 'describe', not 'destring'.  We must verify
        that no prefix of 'destring' resolves specifically to 'destring',
        regardless of whether a prefix resolves to a different command.
        """
        import stata_registry as sr
        # check every prefix shorter than the full name
        for i in range(1, len("destring")):
            prefix = "destring"[:i]
            if sr.is_command(prefix):
                # If the prefix matches ANY command, it must NOT be destring
                assert sr.canonical_command(prefix) != "destring", (
                    f"'{prefix}' must not resolve to 'destring' "
                    f"(destring is not abbreviable in Stata)"
                )

    @pytest.mark.xfail(
        reason=(
            "Stata abbreviates 'describe' to 'd', but the YAML lists "
            "[de, des, desc, descr, descri, describ] — missing 'd'."
        ),
        strict=True,
    )
    def test_describe_abbreviation_d_in_yaml(self):
        """describe must list 'd' as an abbreviation per Stata's rules."""
        doc = yaml.safe_load(
            (_COMMANDS_DIR / "official_stata_commands.yaml").read_text()
        )
        for cat_val in doc["categories"].values():
            for cmd in cat_val.get("commands", []):
                if cmd["name"] == "describe":
                    assert "d" in cmd.get("abbreviations", [])
                    return
        pytest.fail("describe not found")

    @pytest.mark.xfail(
        reason=(
            "Stata abbreviates 'list' to 'l' (since Stata 14).  The YAML "
            "lists [li] but not 'l'.  Verify current Stata behaviour before fixing."
        ),
        strict=True,
    )
    def test_list_abbreviation_l_in_yaml(self):
        """list must list 'l' as an abbreviation per recent Stata rules."""
        doc = yaml.safe_load(
            (_COMMANDS_DIR / "official_stata_commands.yaml").read_text()
        )
        for cat_val in doc["categories"].values():
            for cmd in cat_val.get("commands", []):
                if cmd["name"] == "list":
                    assert "l" in cmd.get("abbreviations", [])
                    return
        pytest.fail("list not found")


# ---------------------------------------------------------------------------
# 2.2 — Discrepancy documentation
# ---------------------------------------------------------------------------

@pytest.mark.xfail(
    reason=(
        "BUG: The README field reference says abbreviations lists only the "
        "'shortest accepted form' with intermediates implied.  But the actual "
        "YAML data enumerates ALL intermediate forms (e.g. regress has "
        "[reg, regr, regre, regres]).  And the reader only registers forms "
        "explicitly present in the YAML, with no generation of intermediates. "
        "The field reference text is inconsistent with both the data and the code."
    ),
    strict=False,
)
def test_readme_field_reference_matches_code():
    """
    The README says shortest-abbreviation-only; the code says enumeration.
    This test documents the discrepancy — it fails because the documentation
    is wrong, not because of a code bug.
    """
    readme = (_REPO_ROOT / "README.md").read_text()
    # The README says abbreviations lists the shortest accepted form
    assert "shortest" not in readme.lower() or "implied" not in readme.lower()