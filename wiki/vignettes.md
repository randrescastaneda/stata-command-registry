# Vignettes

Short, task-oriented examples for working with the `stata_registry` package and
the underlying YAML registries.

<!-- cg:auto:examples -->
## Examples

### Resolve abbreviations to canonical names

When tokenising a do-file you often see abbreviated command forms. Use
`canonical_command` to normalise them before further processing:

```python
import stata_registry as sr

for tok in ["reg", "g", "bys", "foreach", "qui"]:
    print(tok, "->", sr.canonical_command(tok))
# reg      -> regress
# g        -> generate
# bys      -> bysort
# foreach  -> foreach
# qui      -> quietly
```

### Classify a token

```python
import stata_registry as sr

def classify(tok: str) -> str:
    if not sr.is_command(tok):
        return "unknown"
    if sr.is_control_flow(tok):
        return "control_flow"
    if sr.is_prefix(tok):
        return "prefix"
    return sr.category(tok)

print(classify("foreach"))   # control_flow
print(classify("bysort"))    # prefix
print(classify("regress"))   # statistics
print(classify("foobar"))    # unknown
```

### Validate a YAML registry against the schema

Before submitting a contribution, validate your edited YAML against the JSON
Schema:

```bash
pip install check-jsonschema
check-jsonschema --schemafile commands/schema.json commands/official_stata_commands.yaml
```

### Inspect the bundled data directly

The YAML files shipped inside the package are plain data — you can load them
with PyYAML without going through the lookup API:

```python
import stata_registry as sr
from pathlib import Path
import yaml

data_dir = Path(sr.__file__).parent / "data"
for yml in sorted(data_dir.glob("*.yaml")):
    doc = yaml.safe_load(yml.read_text(encoding="utf-8"))
    print(yml.name, doc.get("metadata", {}).get("version"))
```

### Verify a release candidate

Run the complete verification chain before publishing a release:

```bash
python -m pytest
check-jsonschema --schemafile commands/schema.json commands/*.yaml
python -m build
```

Install the resulting wheel in a temporary environment from outside the
repository root, then check the installed version, bundled registry data, and
`variable_effect("generate") == "creates"` through the public API.
<!-- cg:auto:end -->

<!-- cg:auto:use-cases -->
## Use cases

### stataGlow — syntax highlighting

[stataGlow](https://github.com/randrescastaneda/stataGlow) provides Stata
syntax highlighting for VS Code and Positron. Rather than maintaining a
hard-coded command list in the grammar, it consumes `stata-command-registry` as
the canonical vocabulary: `is_command` drives keyword matching, while
`category` and `is_prefix`/`is_control_flow` allow scope-aware highlighting
(e.g. distinguishing prefix commands from control-flow keywords).

### do2screen-py — do-file tracing

`do2screen-py` traces Stata do-file execution. It uses `canonical_command` to
normalise abbreviated tokens before logging, and `is_control_flow` /
`is_prefix` to understand the structural role of each token in the do-file
without re-implementing a Stata parser.

### Generic Stata tooling

Any tool that needs to know "is this a Stata command?" or "what is the full
name of this abbreviation?" can depend on `stata-registry` instead of
duplicating the command list. Because the package is data-and-lookup only (no
parsing, no regex, only PyYAML), it adds negligible weight to a dependency
tree.
<!-- cg:auto:end -->

← [Home](README.md)
