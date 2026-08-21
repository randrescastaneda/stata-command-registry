"""
stata_registry — packaging and repository hygiene tests.

Tests for Part 5 of the audit: duplicate data, egg-info, packaging,
git tag, and test suite completeness.
"""
from __future__ import annotations

import filecmp
import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest


_REPO_ROOT = Path(__file__).resolve().parent.parent
_COMMANDS_DIR = _REPO_ROOT / "commands"
_DATA_DIR = _REPO_ROOT / "stata_registry" / "data"
_EGG_INFO_DIR = _REPO_ROOT / "stata_registry.egg-info"
_TESTS_DIR = _REPO_ROOT / "tests"


def _load_generator():
    path = _REPO_ROOT / "scripts" / "generate_registry_data.py"
    spec = importlib.util.spec_from_file_location("registry_generator", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


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

    def test_generation_check_passes(self):
        """The checked-in source and bundled data pass the generator check."""
        result = subprocess.run(
            [
                sys.executable,
                str(_REPO_ROOT / "scripts" / "generate_registry_data.py"),
                "--check",
            ],
            capture_output=True,
            text=True,
            cwd=str(_REPO_ROOT),
        )
        assert result.returncode == 0, result.stderr

    def test_sdist_manifest_contains_generation_pipeline(self):
        """Source releases retain the evidence and generator used to build data."""
        manifest = (_REPO_ROOT / "MANIFEST.in").read_text()
        assert "recursive-include commands *.yaml *.json" in manifest
        assert "include scripts/generate_registry_data.py" in manifest
        assert "include scripts/source_driver_evidence.yaml" in manifest

    def test_generator_handles_quoted_names_without_newline(self):
        """The line-preserving generator safely handles valid YAML edge cases."""
        generator = _load_generator()
        text = "categories:\n  test:\n    commands:\n      - name: 'do'"
        generated = generator._annotate_source_text(
            text, {"do": {"include_driver": True}}
        )
        assert generated.endswith("include_driver: true\n")
        document = generator.yaml.safe_load(generated)
        assert document["categories"]["test"]["commands"][0]["name"] == "do"

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
# 5.2 — generated artifacts not committed
# ---------------------------------------------------------------------------

class TestEggInfoCommitted:
    def test_egg_info_not_tracked(self):
        """Generated egg-info metadata should not be tracked in git."""
        result = subprocess.run(
            ["git", "ls-files", "--error-unmatch", "stata_registry.egg-info/PKG-INFO"],
            capture_output=True, text=True, cwd=str(_REPO_ROOT),
        )
        assert result.returncode != 0, (
            "stata_registry.egg-info is tracked by git; should be gitignored"
        )

    @pytest.mark.parametrize(
        "path",
        [
            "stata_registry/__pycache__",
            "tests/__pycache__",
        ],
    )
    def test_bytecode_not_tracked(self, path):
        """Interpreter bytecode directories should not be tracked in git."""
        result = subprocess.run(
            ["git", "ls-files", "--error-unmatch", path],
            capture_output=True, text=True, cwd=str(_REPO_ROOT),
        )
        assert result.returncode != 0, f"Generated bytecode is tracked: {path}"


# ---------------------------------------------------------------------------
# 5.3 — Clean pip install works
# ---------------------------------------------------------------------------

class TestCleanPipInstall:
    def test_fresh_pip_install(self):
        import sys
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            venv = Path(td) / "venv"
            subprocess.run(
                [sys.executable, "-m", "venv", str(venv)],
                check=True,
            )
            python = venv / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
            pip = venv / ("Scripts/pip.exe" if sys.platform == "win32" else "bin/pip")
            result = subprocess.run(
                [str(pip), "install", str(_REPO_ROOT), "--quiet"],
                capture_output=True, text=True,
            )
            assert result.returncode == 0, f"pip install failed: {result.stderr}"
            script = (
                "import importlib.metadata as metadata; "
                "from pathlib import Path; "
                "import stata_registry as sr; "
                "assert 'site-packages' in Path(sr.__file__).resolve().parts; "
                "assert metadata.version('stata-registry') == '0.4.0'; "
                "assert sr.variable_effect('generate') == 'creates'; "
                "assert sr.is_include('do') is True; "
                "assert sr.is_include('run') is True; "
                "assert sr.is_include('include') is True"
            )
            result = subprocess.run(
                [str(python), "-c", script],
                capture_output=True, text=True, cwd=td,
            )
            assert result.returncode == 0, f"Import failed: {result.stderr}"

    def test_project_version_is_040(self):
        """The project metadata declares the source-driver release."""
        pyproject = (_REPO_ROOT / "pyproject.toml").read_text()
        assert 'version = "0.4.0"' in pyproject


# ---------------------------------------------------------------------------
# 5.4 — v0.1.0 tag
# ---------------------------------------------------------------------------

class TestVersionTag:
    def test_v010_tag_exists(self):
        """The immutable baseline tag remains available."""
        result = subprocess.run(
            ["git", "tag", "-l", "v0.1.0"],
            capture_output=True, text=True, cwd=str(_REPO_ROOT),
        )
        assert result.stdout.strip() == "v0.1.0", (
            "v0.1.0 baseline tag does not exist"
        )

    def test_release_reference_matches_version(self):
        """README and metadata identify the same remediation release."""
        pyproject = (_REPO_ROOT / "pyproject.toml").read_text()
        readme = (_REPO_ROOT / "README.md").read_text()
        assert 'version = "0.4.0"' in pyproject
        assert "@v0.4.0" in readme


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
