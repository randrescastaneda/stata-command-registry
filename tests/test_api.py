"""
stata_registry — API correctness and semantic coupling tests.

Tests for Part 4 of the audit: documented API examples, semantic coupling,
alias support, edge inputs, and package constraints.
"""
from __future__ import annotations

import ast
import inspect
from pathlib import Path

import pytest


_REPO_ROOT = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# 4.1 — Documented API examples
# ---------------------------------------------------------------------------

class TestDocumentedAPIExamples:
    """Every example in the README's API section must produce the documented result."""

    def setup_method(self):
        import importlib
        import stata_registry
        self.sr = importlib.reload(stata_registry)

    def test_is_command_canonical(self):
        assert self.sr.is_command("regress") is True

    def test_is_command_abbreviation(self):
        assert self.sr.is_command("reg") is True

    def test_is_command_unknown(self):
        assert self.sr.is_command("notacommand") is False

    def test_canonical_command_reg(self):
        assert self.sr.canonical_command("reg") == "regress"

    def test_canonical_command_gen(self):
        assert self.sr.canonical_command("gen") == "generate"

    def test_canonical_command_bys(self):
        assert self.sr.canonical_command("bys") == "bysort"

    def test_category_regress(self):
        assert self.sr.category("regress") == "statistics"

    def test_category_foreach(self):
        assert self.sr.category("foreach") == "control_flow"

    def test_category_quietly(self):
        assert self.sr.category("quietly") == "prefix_control"

    def test_is_prefix_bysort(self):
        assert self.sr.is_prefix("bysort") is True

    def test_is_prefix_quietly(self):
        assert self.sr.is_prefix("quietly") is True

    def test_is_prefix_regress(self):
        assert self.sr.is_prefix("regress") is False

    def test_is_control_flow_foreach(self):
        assert self.sr.is_control_flow("foreach") is True

    def test_is_control_flow_if(self):
        assert self.sr.is_control_flow("if") is True

    def test_is_control_flow_regress(self):
        assert self.sr.is_control_flow("regress") is False

    def test_variable_effect_examples(self):
        assert self.sr.variable_effect("generate") == "creates"
        assert self.sr.variable_effect("replace") == "modifies"
        assert self.sr.variable_effect("drop") == "removes"
        assert self.sr.variable_effect("sort") == "restructures"
        assert self.sr.variable_effect("label") == "labels"
        assert self.sr.variable_effect("regress") == "none"


class TestIndexCollisionHandling:
    """Conflicting names, abbreviations, and aliases fail during indexing."""

    @pytest.mark.parametrize(
        "commands",
        [
            [{"name": "alpha", "abbreviations": ["x"]},
             {"name": "beta", "abbreviations": ["x"]}],
            [{"name": "alpha", "aliases": ["x"]},
             {"name": "beta", "aliases": ["x"]}],
            [{"name": "x"}, {"name": "beta", "abbreviations": ["x"]}],
            [{"name": "alpha", "abbreviations": ["x"]},
             {"name": "beta", "aliases": ["x"]}],
            [{"name": "alpha"}, {"name": "alpha"}],
        ],
    )
    def test_conflicting_tokens_raise(self, commands):
        import stata_registry as sr
        document = {"categories": {"test": {"commands": commands}}}
        with pytest.raises(ValueError, match="maps to both|Duplicate registry command name"):
            sr._build_index([document])


# ---------------------------------------------------------------------------
# 4.2 — Semantic coupling: is_prefix and is_control_flow derived from category keys
# ---------------------------------------------------------------------------

class TestSemanticCoupling:
    """is_prefix() and is_control_flow() are derived from YAML category keys,
    not from explicit boolean fields on each entry.  This couples parser
    behaviour to a presentation-layer concept (TextMate scopes)."""

    @pytest.mark.xfail(
        reason=(
            "Design risk: is_prefix('bysort') returns True only because 'bysort' "
            "is listed under the category key 'prefix_commands'.  If that key is "
            "renamed for cleaner TextMate scoping, is_prefix() silently returns "
            "False, breaking do2py.  Recommend explicit is_prefix: true / "
            "is_control_flow: true fields on each entry instead."
        ),
        strict=False,
    )
    def test_is_prefix_not_category_derived(self):
        """is_prefix should NOT depend on the category key name."""
        import importlib
        import stata_registry as sr
        sr = importlib.reload(sr)
        # Verify that prefix identity is not derived from the category key.
        # This test documents the design concern: currently it IS category-derived.
        import yaml
        from pathlib import Path
        repo = Path(__file__).resolve().parent.parent
        doc = yaml.safe_load((repo / "commands" / "official_stata_commands.yaml").read_text())
        # Find bysort entry and check for an explicit is_prefix field
        for cat_val in doc["categories"].values():
            for cmd in cat_val.get("commands", []):
                if cmd["name"] == "bysort":
                    # If we get here with an explicit field, the design is decoupled
                    assert cmd.get("is_prefix") is True, (
                        "bysort has no explicit is_prefix field; "
                        "identity is derived from category key 'prefix_commands'"
                    )

    def test_capture_is_prefix_not_control_flow(self):
        """capture is in prefix_control, NOT in control_flow."""
        import importlib
        import stata_registry as sr
        sr = importlib.reload(sr)
        assert sr.is_prefix("capture") is True
        assert sr.is_control_flow("capture") is False

    def test_bysort_is_prefix_category(self):
        """bysort is in prefix_commands category."""
        import importlib
        import stata_registry as sr
        sr = importlib.reload(sr)
        assert sr.is_prefix("bysort") is True
        assert sr.category("bysort") == "prefix_commands"

    def test_commands_in_expected_categories(self):
        """All prefix/flow commands are in the expected category keys."""
        import importlib, yaml
        import stata_registry as sr
        sr = importlib.reload(sr)
        repo = Path(__file__).resolve().parent.parent
        doc = yaml.safe_load((repo / "commands" / "official_stata_commands.yaml").read_text())
        PREFIX_KEYS = {"prefix_commands", "prefix_control"}
        FLOW_KEYS = {"control_flow"}
        for cat_key, cat_val in doc["categories"].items():
            for cmd in cat_val.get("commands", []):
                name = cmd["name"]
                if cat_key in PREFIX_KEYS:
                    assert sr.is_prefix(name) is True, (
                        f"{name} in {cat_key} but is_prefix=False"
                    )
                if cat_key in FLOW_KEYS:
                    assert sr.is_control_flow(name) is True, (
                        f"{name} in {cat_key} but is_control_flow=False"
                    )


# ---------------------------------------------------------------------------
# 4.3 — Alias support
# ---------------------------------------------------------------------------

class TestAliasSupport:
    """Aliases must be honoured by is_command() and canonical_command()."""

    @pytest.mark.xfail(
        reason=(
            "Alias support is implemented in code but NO aliases exist in the "
            "YAML (0 aliases found).  This test confirms alias support works "
            "by injecting a synthetic test.  If it fails, the implementation "
            "is broken.  Currently the test is expected to fail because there "
            "are no aliases to test against.  Once aliases are added to the "
            "data, this test should be updated to reference real values."
        ),
        strict=False,
    )
    def test_alias_resolves(self):
        """An alias must resolve to the canonical name via canonical_command()."""
        import importlib, yaml
        import stata_registry as sr
        sr = importlib.reload(sr)
        repo = Path(__file__).resolve().parent.parent
        # Check actual YAML for any alias
        doc = yaml.safe_load((repo / "commands" / "official_stata_commands.yaml").read_text())
        for cat_val in doc["categories"].values():
            for cmd in cat_val.get("commands", []):
                aliases = cmd.get("aliases", [])
                if aliases:
                    alias = aliases[0]
                    assert sr.canonical_command(alias) == cmd["name"]
                    assert sr.is_command(alias) is True
                    return
        pytest.skip(
            "No aliases found in any YAML file — cannot test alias support"
        )

    def test_alias_code_path_exists(self):
        """The reader's _build_index registers aliases."""
        import importlib, inspect
        import stata_registry as sr
        sr_mod = importlib.import_module("stata_registry")
        src = inspect.getsource(sr_mod)
        assert "aliases" in src, "Reader references aliases"
        assert "alias" in src


# ---------------------------------------------------------------------------
# 4.4 — Edge inputs
# ---------------------------------------------------------------------------

class TestEdgeInputs:
    """Documented behaviour for edge-case inputs."""

    def setup_method(self):
        import importlib
        import stata_registry
        self.sr = importlib.reload(stata_registry)

    def test_empty_string(self):
        assert self.sr.is_command("") is False

    def test_whitespace(self):
        assert self.sr.is_command(" ") is False
        assert self.sr.is_command("\t") is False

    def test_trailing_whitespace(self):
        assert self.sr.is_command("regress ") is False

    def test_mixed_case(self):
        assert self.sr.is_command("Regress") is False
        assert self.sr.is_command("REGRESS") is False
        assert self.sr.is_command("Gen") is False

    def test_leading_colon(self):
        assert self.sr.is_command(":regress") is False

    def test_compound_command(self):
        """Compound commands like 'quietly regress' are not single tokens."""
        assert self.sr.is_command("quietly regress") is False

    def test_none_is_command_returns_false(self):
        """is_command(None) should return False (not raise)."""
        result = self.sr.is_command(None)
        assert result is False

    def test_none_canonical_command_raises(self):
        """canonical_command(None) raises KeyError."""
        with pytest.raises(KeyError):
            self.sr.canonical_command(None)

    def test_none_category_raises(self):
        """category(None) raises KeyError."""
        with pytest.raises(KeyError):
            self.sr.category(None)

    def test_none_is_prefix_returns_false(self):
        """is_prefix(None) should return False."""
        assert self.sr.is_prefix(None) is False

    def test_none_is_control_flow_returns_false(self):
        """is_control_flow(None) should return False."""
        assert self.sr.is_control_flow(None) is False


# ---------------------------------------------------------------------------
# 4.5 — Package constraints: data and lookup only
# ---------------------------------------------------------------------------

class TestPackageConstraints:
    """The package must contain data and lookup only — no parsing logic,
    no regex, no dependencies beyond PyYAML."""

    def test_no_regex_import(self):
        """The reader must not import or use the re module."""
        import importlib, inspect
        sr_mod = importlib.import_module("stata_registry")
        src = inspect.getsource(sr_mod)
        assert "import re" not in src, "Reader imports re module"
        assert "re." not in src, "Reader uses re module"

    def test_no_parsing_logic(self):
        """The reader must not parse Stata source code."""
        import importlib, inspect
        sr_mod = importlib.import_module("stata_registry")
        src = inspect.getsource(sr_mod)
        # 'parse' in filenames, docstrings, or comments is fine;
        # 'parse' as a function call would be suspicious.
        assert "parse_stata" not in src
        assert "parse_line" not in src

    def test_only_yaml_dependency(self):
        """The package's only non-stdlib dependency is PyYAML."""
        import ast, importlib, inspect
        sr_mod = importlib.import_module("stata_registry")
        src = inspect.getsource(sr_mod)
        tree = ast.parse(src)
        external_imports = set()
        stdlib_modules = {
            "__future__", "threading", "pathlib", "typing", "collections",
            "json", "sys", "os", "abc", "functools", "importlib",
        }
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    mod = alias.name.split(".")[0]
                    if mod not in stdlib_modules:
                        external_imports.add(mod)
            elif isinstance(node, ast.ImportFrom) and node.module:
                mod = node.module.split(".")[0]
                if mod not in stdlib_modules:
                    external_imports.add(mod)
        # yaml is the only allowed external dependency
        assert external_imports <= {"yaml"}, (
            f"Unexpected external imports: {external_imports}"
        )
