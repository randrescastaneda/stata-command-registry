"""
stata_registry — A lightweight reader for the Stata command registry.

Exposes a set of lookup functions over the YAML command definitions bundled
with this package:

    is_command(token)          -> bool
    canonical_command(token)   -> str   # resolves abbreviations, e.g. "g" -> "generate"
    category(command)          -> str   # returns the category key, e.g. "data_management"
    is_prefix(command)         -> bool  # bysort, quietly, capture, noisily, …
    is_control_flow(command)   -> bool  # foreach, forvalues, if, else, while, …
"""

from __future__ import annotations

import threading
from pathlib import Path
from typing import Dict, Optional

import yaml

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_REGISTRY_DIR = Path(__file__).parent / "data"

# Category keys that represent prefix commands
_PREFIX_CATEGORIES = {"prefix_commands", "prefix_control"}

# Category keys that represent control-flow keywords
_CONTROL_FLOW_CATEGORIES = {"control_flow"}


def _load_yaml_files() -> list[dict]:
    """Return a list of parsed YAML registry documents from the data/ directory."""
    docs = []
    for path in sorted(_REGISTRY_DIR.glob("*.yaml")):
        with path.open(encoding="utf-8") as fh:
            doc = yaml.safe_load(fh)
            if doc and isinstance(doc.get("categories"), dict):
                docs.append(doc)
    return docs


def _build_index(docs: list[dict]) -> tuple[
    Dict[str, str],   # token (name/abbrev) -> canonical name
    Dict[str, str],   # canonical name -> category key
    set[str],         # prefix canonical names
    set[str],         # control-flow canonical names
]:
    """Build lookup tables from the parsed YAML documents."""
    token_to_canonical: Dict[str, str] = {}
    name_to_category: Dict[str, str] = {}
    prefix_names: set[str] = set()
    control_flow_names: set[str] = set()

    for doc in docs:
        for cat_key, cat_val in doc["categories"].items():
            for cmd in cat_val.get("commands") or []:
                name: str = cmd["name"]

                # canonical mapping: name -> name
                token_to_canonical[name] = name
                name_to_category[name] = cat_key

                # abbreviation mapping: abbrev -> name
                for abbrev in cmd.get("abbreviations") or []:
                    token_to_canonical[abbrev] = name

                # alias mapping: alias -> name (aliases are full alternative names)
                for alias in cmd.get("aliases") or []:
                    token_to_canonical[alias] = name

                if cat_key in _PREFIX_CATEGORIES:
                    prefix_names.add(name)
                if cat_key in _CONTROL_FLOW_CATEGORIES:
                    control_flow_names.add(name)

    return token_to_canonical, name_to_category, prefix_names, control_flow_names


# ---------------------------------------------------------------------------
# Module-level initialisation (lazy, thread-safe)
# ---------------------------------------------------------------------------

_token_to_canonical: Optional[Dict[str, str]] = None
_name_to_category: Optional[Dict[str, str]] = None
_prefix_names: Optional[set[str]] = None
_control_flow_names: Optional[set[str]] = None
_load_lock = threading.Lock()


def _ensure_loaded() -> None:
    global _token_to_canonical, _name_to_category, _prefix_names, _control_flow_names
    if _token_to_canonical is not None:
        return
    with _load_lock:
        if _token_to_canonical is None:
            docs = _load_yaml_files()
            (
                _token_to_canonical,
                _name_to_category,
                _prefix_names,
                _control_flow_names,
            ) = _build_index(docs)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def is_command(token: str) -> bool:
    """Return True if *token* is a known Stata command name or abbreviation."""
    _ensure_loaded()
    return token in _token_to_canonical  # type: ignore[operator]


def canonical_command(token: str) -> str:
    """Resolve *token* to its canonical (full) command name.

    Raises ``KeyError`` if *token* is not a recognised command or abbreviation.
    """
    _ensure_loaded()
    try:
        return _token_to_canonical[token]  # type: ignore[index]
    except KeyError:
        raise KeyError(f"Unknown Stata command or abbreviation: {token!r}") from None


def category(command: str) -> str:
    """Return the registry category key for *command*.

    *command* may be either the canonical name or a known abbreviation.
    Raises ``KeyError`` if *command* is not recognised.
    """
    _ensure_loaded()
    canonical = canonical_command(command)
    return _name_to_category[canonical]  # type: ignore[index]


def is_prefix(command: str) -> bool:
    """Return True if *command* is a Stata prefix command.

    Prefix commands (e.g. ``bysort``, ``quietly``, ``capture``) appear before
    another command and modify how it executes.  *command* may be an
    abbreviation.
    """
    _ensure_loaded()
    if not is_command(command):
        return False
    canonical = _token_to_canonical[command]  # type: ignore[index]
    return canonical in _prefix_names  # type: ignore[operator]


def is_control_flow(command: str) -> bool:
    """Return True if *command* is a control-flow keyword.

    Control-flow keywords (e.g. ``foreach``, ``forvalues``, ``if``,
    ``else``, ``while``) govern the flow of execution in do-files.
    *command* may be an abbreviation.
    """
    _ensure_loaded()
    if not is_command(command):
        return False
    canonical = _token_to_canonical[command]  # type: ignore[index]
    return canonical in _control_flow_names  # type: ignore[operator]
