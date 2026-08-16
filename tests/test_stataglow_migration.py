"""
stata_registry — stataGlow migration status tests.

Tests for Part 6 of the audit: whether stataGlow has been migrated to
consume this package as its single source of truth.
"""
from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

import pytest


_REPO_ROOT = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# 6.1 — Migration status
# ---------------------------------------------------------------------------

class TestStataglowMigration:
    """stataGlow must consume this package, not carry its own YAML copies."""

    @pytest.mark.xfail(
        reason=(
            "BLOCKING: stataGlow (github.com/randrescastaneda/stataGlow) still "
            "carries its own copies of commands/*.yaml that are byte-identical "
            "to this repo's files.  It has NOT been migrated to depend on the "
            "stata-registry package.  The single source of truth does not yet "
            "exist in practice."
        ),
        strict=True,
    )
    def test_stataglow_does_not_carry_yaml_copies(self):
        """stataGlow should not contain its own commands/*.yaml files."""
        # This test is a placeholder — it documents the expected state
        # once migration is complete.  Currently it is expected to fail.
        # When the migration is done, remove the xfail and make this test
        # actually clone stataGlow and check.
        pytest.skip(
            "Manual verification required: clone stataGlow and verify "
            "that it does not contain commands/*.yaml and instead imports "
            "stata-registry as a dependency."
        )

    @pytest.mark.xfail(
        reason=(
            "BLOCKING: stataGlow has not been migrated.  Cannot reproduce "
            "the byte-identical grammar check because migration hasn't "
            "happened yet."
        ),
        strict=True,
    )
    def test_stataglow_grammar_unchanged_after_migration(self):
        """
        When stataGlow migrates to consume this package, the generated
        grammars/stata.json must be byte-identical to the pre-migration version.

        Steps (to be automated after migration):
        1. Clone stataGlow at the pre-migration commit.
        2. Build the grammar from its local YAML.
        3. Install stata-registry from this repo.
        4. Build the grammar from the package YAML.
        5. Diff the two grammar files.
        """
        with tempfile.TemporaryDirectory() as td:
            clone = Path(td) / "stataGlow"
            result = subprocess.run(
                ["git", "clone", "--depth", "1",
                 "https://github.com/randrescastaneda/stataGlow.git",
                 str(clone)],
                capture_output=True, text=True,
            )
            if result.returncode != 0:
                pytest.skip(f"Cannot clone stataGlow: {result.stderr}")

            # Check if stataGlow has its own YAML
            yamls = list((clone / "commands").glob("*.yaml"))
            assert len(yamls) == 0, (
                f"stataGlow still carries {len(yamls)} YAML files in commands/; "
                f"migration not complete"
            )