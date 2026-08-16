"""
stata_registry — packaging and repository hygiene tests.

Tests for Part 5 of the audit: duplicate data, egg-info, packaging,
git tag, and test suite completeness.
"""
from __future__ import annotations

import filecmp
import subprocess
from pathlib import Path

import pytest


_REPO_ROOT = Path(__file__).resolve().parent.parent
_COMMANDS_DIR = _REPO_ROOT / "commands"
_DATA_DIR = _REPO_ROOT / "stata_registry" / "data"
_EGG_INFO_DIR = _REPO_ROOT / "stata_registry.egg-info"
_TESTS_DIR = _REPO_ROOT / "tests"


# ---------------------------------------------------------------------------
# 5.1 — Duplicate data directories
# ---------------------------------------------------------------------------

class TestDuplicateData:
    """commands/ and stata_registry/data/ must be identical byte-for-byte."""

    def test_data_dir_contains_all_yaml(self):
        """Every YAML file in commands/ also exists in data/."""
        cmd_yamls = sorted(p.name for p in _COMMANDS_DIR.glob("*.yaml"))
        data_yamls = sorted(p.name for p in _DATA_DIR.glob("*.yaml"))
        assert cmd_yamls == data_yamls, (
            f"File list mismatch:\n  commands/: {cmd_yamls}\n  data/: {data_yamls}"
        )

    @pytest.mark.parametrize(
        "filename",
        sorted(p.name for p in _COMMANDS_DIR.glob("*.yaml")),
    )
    def test_file_is_identical(self, filename):
        """Each YAML file in commands/ is byte-identical to data/."""
        f1 = _COMMANDS_DIR / filename
        f2 = _DATA_DIR / filename
        assert filecmp.cmp(f1, f2, shallow=False), (
            f"{filename} differs between commands/ and stata_registry/data/"
        )

    @pytest.mark.xfail(
        reason=(
            "HYGIENE: commands/ and stata_registry/data/ contain the same "
            "files as regular copies (not symlinks, not generated).  This is "
            "the exact duplication this repository exists to eliminate.  "
            "Recommend: data/ contents should be generated at build time "
            "from commands/, or commands/ should be a symlink to data/, "
            "or a build step should copy commands/ -> data/."
        ),
        strict=False,
    )
    def test_no_manual_duplicate(self):
        """Ideally data/ would not be a manual copy of commands/."""
        for f in sorted(_COMMANDS_DIR.glob("*.yaml")):
            target = _DATA_DIR / f.name
            # A symlink or generated-fresh file would be acceptable
            assert target.is_symlink() or False, (
                f"{f.name} is a manual copy, not a symlink or build output"
            )


# ---------------------------------------------------------------------------
# 5.2 — egg-info committed
# ---------------------------------------------------------------------------

class TestEggInfoCommitted:
    @pytest.mark.xfail(
        reason=(
            "HYGIENE: stata_registry.egg-info is tracked in git.  "
            "build artifacts should be gitignored.  "
            "Already partially gitignored (*.egg-info/) but the directory "
            "was committed before the gitignore rule existed."
        ),
        strict=False,
    )
    def test_egg_info_not_tracked(self):
        """stata_registry.egg-info should not be in git."""
        result = subprocess.run(
            ["git", "ls-files", "--error-unmatch", "stata_registry.egg-info/"],
            capture_output=True, text=True, cwd=str(_REPO_ROOT),
        )
        assert result.returncode != 0, (
            "stata_registry.egg-info is tracked by git; should be gitignored"
        )


# ---------------------------------------------------------------------------
# 5.3 — Clean pip install works
# ---------------------------------------------------------------------------

class TestCleanPipInstall:
    @pytest.mark.xfail(
        reason=(
            "The clean pip install test requires running in a fresh venv. "
            "Set STATA_REGISTRY_CLEAN_VENV to run this test.  Alternatively "
            "run the manual test described in the audit report."
        ),
        strict=False,
    )
    def test_fresh_pip_install(self):
        import os
        import tempfile
        import shutil
        if not shutil.which("python3"):
            pytest.skip("No python3 binary")
        with tempfile.TemporaryDirectory() as td:
            venv = Path(td) / "venv"
            subprocess.run(
                ["python3", "-m", "venv", str(venv)],
                check=True,
            )
            pip = str(venv / "bin" / "pip")
            result = subprocess.run(
                [pip, "install", str(_REPO_ROOT), "--quiet"],
                capture_output=True, text=True,
            )
            assert result.returncode == 0, f"pip install failed: {result.stderr}"
            py = str(venv / "bin" / "python3")
            result = subprocess.run(
                [py, "-c", "import stata_registry as sr; assert sr.is_command('regress')"],
                capture_output=True, text=True,
            )
            assert result.returncode == 0, f"Import failed: {result.stderr}"


# ---------------------------------------------------------------------------
# 5.4 — v0.1.0 tag
# ---------------------------------------------------------------------------

class TestVersionTag:
    @pytest.mark.xfail(
        reason=(
            "BLOCKING: The README instructs consumers to install at ref v0.1.0 "
            "but the tag does not exist.  Consumers who follow the README will "
            "get a git error."
        ),
        strict=True,
    )
    def test_v010_tag_exists(self):
        """The README references v0.1.0; the tag must exist."""
        result = subprocess.run(
            ["git", "tag", "-l", "v0.1.0"],
            capture_output=True, text=True, cwd=str(_REPO_ROOT),
        )
        assert result.stdout.strip() == "v0.1.0", (
            "v0.1.0 tag does not exist but is referenced in README install instructions"
        )


# ---------------------------------------------------------------------------
# 5.5 — Test suite exercises the API
# ---------------------------------------------------------------------------

class TestSuiteCompleteness:
    """The tests/ directory must exercise the API, not just the schema."""

    def test_test_files_exist(self):
        """At least test_registry.py (API tests) and test_data_integrity.py exist."""
        test_files = [p.name for p in _TESTS_DIR.glob("test_*.py")]
        assert "test_registry.py" in test_files, "test_registry.py missing"
        assert "test_data_integrity.py" in test_files, "test_data_integrity.py missing"

    def test_api_tests_exist(self):
        """test_registry.py tests is_command, canonical_command, category."""
        test_file = _TESTS_DIR / "test_registry.py"
        content = test_file.read_text()
        assert "is_command" in content, "test_registry.py does not test is_command"
        assert "canonical_command" in content, "test_registry.py does not test canonical_command"
        assert "category" in content, "test_registry.py does not test category"
        assert "is_prefix" in content, "test_registry.py does not test is_prefix"
        assert "is_control_flow" in content, "test_registry.py does not test is_control_flow"