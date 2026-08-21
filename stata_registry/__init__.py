"""
stata_registry — A lightweight reader for the Stata command registry.

Exposes a set of lookup functions over the YAML command definitions bundled
with this package:

    is_command(token)          -> bool
    canonical_command(token)   -> str   # resolves abbreviations, e.g. "g" -> "generate"
    category(command)          -> str   # returns the category key, e.g. "data_management"
    variable_effect(command)   -> str   # e.g. "creates", "modifies", "none"
    is_include(token)          -> bool  # do, run, include, and any future source drivers
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
    Dict[str, str],   # canonical name -> variable_effect
    set[str],         # prefix canonical names
    set[str],         # control-flow canonical names
    set[str],         # include-driver canonical names
]:
    """Build lookup tables from the parsed YAML documents."""
    token_to_canonical: Dict[str, str] = {}
    name_to_category: Dict[str, str] = {}
    name_to_variable_effect: Dict[str, str] = {}
    prefix_names: set[str] = set()
    control_flow_names: set[str] = set()
    include_driver_names: set[str] = set()

    def register_token(token: str, canonical: str) -> None:
        """Register a token and reject conflicting registry definitions."""
        existing = token_to_canonical.get(token)
        if existing is not None and existing != canonical:
            raise ValueError(
                f"Registry token {token!r} maps to both "
                f"{existing!r} and {canonical!r}"
            )
        token_to_canonical[token] = canonical

    for doc in docs:
        for cat_key, cat_val in doc["categories"].items():
            for cmd in cat_val.get("commands") or []:
                name: str = cmd["name"]

                if name in name_to_category:
                    raise ValueError(f"Duplicate registry command name: {name!r}")

                # canonical mapping: name -> name
                register_token(name, name)
                name_to_category[name] = cat_key

                # variable_effect mapping: name -> effect
                if "variable_effect" in cmd:
                    name_to_variable_effect[name] = cmd["variable_effect"]

                # abbreviation mapping: abbrev -> name
                for abbrev in cmd.get("abbreviations") or []:
                    register_token(abbrev, name)

                # alias mapping: alias -> name (aliases are full alternative names)
                for alias in cmd.get("aliases") or []:
                    register_token(alias, name)

                if cat_key in _PREFIX_CATEGORIES:
                    prefix_names.add(name)
                if cat_key in _CONTROL_FLOW_CATEGORIES:
                    control_flow_names.add(name)
                if cmd.get("include_driver") is True:
                    include_driver_names.add(name)

    return (
        token_to_canonical,
        name_to_category,
        name_to_variable_effect,
        prefix_names,
        control_flow_names,
        include_driver_names,
    )


# ---------------------------------------------------------------------------
# Module-level initialisation (lazy, thread-safe)
# ---------------------------------------------------------------------------

_Index = tuple[
    Dict[str, str],
    Dict[str, str],
    Dict[str, str],
    set[str],
    set[str],
    set[str],
]

_index: Optional[_Index] = None
_load_lock = threading.Lock()


def _ensure_loaded() -> None:
    global _index
    if _index is not None:
        return
    with _load_lock:
        if _index is None:
            _index = _build_index(_load_yaml_files())


def _loaded_index() -> _Index:
    """Return the atomically published lookup index."""
    _ensure_loaded()
    assert _index is not None
    return _index


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def is_command(token: str) -> bool:
    """Return True if *token* is a known Stata command name or abbreviation."""
    if not isinstance(token, str):
        return False
    token_to_canonical, *_ = _loaded_index()
    return token in token_to_canonical


def canonical_command(token: str) -> str:
    """Resolve *token* to its canonical (full) command name.

    Raises ``KeyError`` if *token* is not a recognised command or abbreviation.
    """
    token_to_canonical, *_ = _loaded_index()
    if not isinstance(token, str):
        raise KeyError(f"Unknown Stata command or abbreviation: {token!r}")
    try:
        return token_to_canonical[token]
    except KeyError:
        raise KeyError(f"Unknown Stata command or abbreviation: {token!r}") from None


def category(command: str) -> str:
    """Return the registry category key for *command*.

    *command* may be either the canonical name or a known abbreviation.
    Raises ``KeyError`` if *command* is not recognised.
    """
    canonical = canonical_command(command)
    _, name_to_category, *_ = _loaded_index()
    return name_to_category[canonical]


def is_prefix(command: str) -> bool:
    """Return True if *command* is a Stata prefix command.

    Prefix commands (e.g. ``bysort``, ``quietly``, ``capture``) appear before
    another command and modify how it executes.  *command* may be an
    abbreviation.
    """
    if not isinstance(command, str):
        return False
    token_to_canonical, _, _, prefix_names, _, _ = _loaded_index()
    canonical = token_to_canonical.get(command)
    return canonical in prefix_names


def is_include(token: str) -> bool:
    """Return True if *token* resolves to an include-driver command.

    Include drivers execute commands stored in another Stata source file.  The
    result comes only from the registry's explicit ``include_driver`` field;
    it is independent of ``variable_effect``.  *token* may be a canonical
    command name, abbreviation, or alias.  Unknown tokens return ``False``.
    """
    if not isinstance(token, str):
        return False
    token_to_canonical, _, _, _, _, include_driver_names = _loaded_index()
    canonical = token_to_canonical.get(token)
    return canonical in include_driver_names


def variable_effect(command: str) -> str:
    """Return the variable_effect value for *command*.

    Values are one of ``creates``, ``modifies``, ``renames``, ``removes``,
    ``labels``, ``restructures``, or ``none``.  *command* may be an
    abbreviation.

    Raises ``KeyError`` if *command* is not recognised.
    Raises ``ValueError`` if the entry has no ``variable_effect`` field.
    """
    canonical = canonical_command(command)
    _, _, name_to_variable_effect, *_ = _loaded_index()
    try:
        return name_to_variable_effect[canonical]
    except KeyError:
        raise ValueError(
            f"No variable_effect defined for command {command!r}"
        ) from None


def is_control_flow(command: str) -> bool:
    """Return True if *command* is a control-flow keyword.

    Control-flow keywords (e.g. ``foreach``, ``forvalues``, ``if``,
    ``else``, ``while``) govern the flow of execution in do-files.
    *command* may be an abbreviation.
    """
    if not isinstance(command, str):
        return False
    token_to_canonical, _, _, _, control_flow_names, _ = _loaded_index()
    canonical = token_to_canonical.get(command)
    return canonical in control_flow_names
