"""A small JSON Schema validator covering the subset used by
project.schema.json (stdlib only, so no `jsonschema` dependency).

Supported keywords: type, enum, const, properties, required,
additionalProperties, items, minItems, maxItems, minLength, maxLength,
pattern, minimum, maximum, anyOf, oneOf, $ref (local "#/..." only).
Annotation keywords (description, default, title, $id, $schema) are ignored.
"""

import re

_TYPES = {
    "object": lambda v: isinstance(v, dict),
    "array": lambda v: isinstance(v, list),
    "string": lambda v: isinstance(v, str),
    "integer": lambda v: isinstance(v, int) and not isinstance(v, bool),
    "number": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
    "boolean": lambda v: isinstance(v, bool),
    "null": lambda v: v is None,
}


def _resolve(root, ref):
    if not ref.startswith("#/"):
        raise ValueError(f"unsupported $ref {ref!r}")
    node = root
    for part in ref[2:].split("/"):
        node = node[part.replace("~1", "/").replace("~0", "~")]
    return node


def _path(parts):
    out = ""
    for p in parts:
        out += f"[{p}]" if isinstance(p, int) else (f".{p}" if out else p)
    return out or "(root)"


def validate(instance, schema, root=None, path=()):
    """Return a list of (path, message). Empty list means valid."""
    root = root if root is not None else schema
    errors = []

    if "$ref" in schema:
        errors += validate(instance, _resolve(root, schema["$ref"]), root, path)

    if "type" in schema:
        types = schema["type"] if isinstance(schema["type"], list) else [schema["type"]]
        if not any(_TYPES[t](instance) for t in types):
            return errors + [(_path(path), f"expected {' or '.join(types)}, got {_typename(instance)}")]

    if "const" in schema and instance != schema["const"]:
        errors.append((_path(path), f"must be {schema['const']!r}"))
    if "enum" in schema and instance not in schema["enum"]:
        errors.append((_path(path), f"must be one of {', '.join(map(repr, schema['enum']))}"))

    if isinstance(instance, str):
        if "minLength" in schema and len(instance) < schema["minLength"]:
            errors.append((_path(path), f"must have at least {schema['minLength']} characters"))
        if "maxLength" in schema and len(instance) > schema["maxLength"]:
            errors.append((_path(path), f"must have at most {schema['maxLength']} characters"))
        if "pattern" in schema and not re.search(schema["pattern"], instance):
            errors.append((_path(path), f"{instance!r} does not match {schema['pattern']}"))

    if _TYPES["number"](instance):
        if "minimum" in schema and instance < schema["minimum"]:
            errors.append((_path(path), f"must be >= {schema['minimum']}"))
        if "maximum" in schema and instance > schema["maximum"]:
            errors.append((_path(path), f"must be <= {schema['maximum']}"))

    if isinstance(instance, list):
        if "minItems" in schema and len(instance) < schema["minItems"]:
            errors.append((_path(path), f"must have at least {schema['minItems']} items"))
        if "maxItems" in schema and len(instance) > schema["maxItems"]:
            errors.append((_path(path), f"must have at most {schema['maxItems']} items"))
        if "items" in schema:
            for i, item in enumerate(instance):
                errors += validate(item, schema["items"], root, path + (i,))

    if isinstance(instance, dict):
        props = schema.get("properties", {})
        for key in schema.get("required", []):
            if key not in instance:
                errors.append((_path(path), f"missing required property {key!r}"))
        for key, value in instance.items():
            if key in props:
                errors += validate(value, props[key], root, path + (key,))
            else:
                extra = schema.get("additionalProperties", True)
                if extra is False:
                    errors.append((_path(path + (key,)), "unknown property"))
                elif isinstance(extra, dict):
                    errors += validate(value, extra, root, path + (key,))

    for kw in ("anyOf", "oneOf"):
        if kw in schema:
            results = [validate(instance, sub, root, path) for sub in schema[kw]]
            ok = sum(1 for r in results if not r)
            if kw == "anyOf" and ok == 0 or kw == "oneOf" and ok != 1:
                # report the branch with the fewest errors: usually the intended one
                best = min(results, key=len)
                if len(schema[kw]) > 1 and all(len(r) == 1 for r in results):
                    errors.append((_path(path), "; or ".join(r[0][1] for r in results)))
                else:
                    errors += best
    return errors


def _typename(v):
    for name in ("null", "boolean", "integer", "number", "string", "array", "object"):
        if _TYPES[name](v):
            return name
    return type(v).__name__
