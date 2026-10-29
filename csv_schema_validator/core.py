"""Column-level and table-level validation rules."""
import csv
import re
from collections import Counter, namedtuple
from datetime import datetime

Violation = namedtuple("Violation", "row column rule value message")

TYPES = ("string", "integer", "number", "boolean", "date")
BOOL = {"true", "false", "1", "0", "yes", "no", "y", "n", "t", "f"}


def _typed(value, ctype, fmt=None):
    if ctype == "integer":
        if not re.fullmatch(r"[-+]?\d+", value):
            raise ValueError
        return int(value)
    if ctype == "number":
        return float(value)
    if ctype == "boolean":
        if value.lower() not in BOOL:
            raise ValueError
        return value.lower() in ("true", "1", "yes", "y", "t")
    if ctype == "date":
        return datetime.strptime(value, fmt or "%Y-%m-%d")
    return value


def validate_rows(header, rows, schema, max_errors=1000):
    """Validate rows (lists of strings) against schema dict. Returns list of Violation.

    Schema: {"columns": {name: {type, required, unique, min, max, pattern, enum, format,
    min_length, max_length, missing_values}}, "strict": bool, "primary_key": [cols],
    "row_rules": [{"if": {...}, "then": {...}}]} (see README).
    """
    cols = schema.get("columns", {})
    out = []
    missing_default = set(schema.get("missing_values", ["", "NA"]))
    for name, rule in cols.items():
        if name not in header and rule.get("required_column", True):
            out.append(Violation(0, name, "missing-column", "", "column '%s' is missing" % name))
    if schema.get("strict"):
        for h in header:
            if h not in cols:
                out.append(Violation(0, h, "unexpected-column", "", "column '%s' is not in the schema" % h))
    idx = {h: i for i, h in enumerate(header)}
    seen = {c: {} for c, r in cols.items() if r.get("unique")}
    pk = schema.get("primary_key")
    pk_seen = {}
    for rn, row in enumerate(rows, start=2):  # row 1 is the header
        if len(row) != len(header):
            out.append(Violation(rn, "", "row-length", "", "row has %d fields, header has %d" % (len(row), len(header))))
        typed = {}
        for name, rule in cols.items():
            if name not in idx:
                continue
            raw = row[idx[name]].strip() if idx[name] < len(row) else ""
            missing = raw in set(rule.get("missing_values", missing_default))
            if missing:
                if rule.get("required"):
                    out.append(Violation(rn, name, "required", raw, "value is required"))
                typed[name] = None
                continue
            ctype = rule.get("type", "string")
            try:
                v = _typed(raw, ctype, rule.get("format"))
            except ValueError:
                out.append(Violation(rn, name, "type", raw, "expected %s" % ctype + (" (%s)" % rule["format"] if rule.get("format") else "")))
                continue
            typed[name] = v
            if "min" in rule and ctype in ("integer", "number") and v < rule["min"]:
                out.append(Violation(rn, name, "min", raw, "below minimum %s" % rule["min"]))
            if "max" in rule and ctype in ("integer", "number") and v > rule["max"]:
                out.append(Violation(rn, name, "max", raw, "above maximum %s" % rule["max"]))
            if "enum" in rule and raw not in [str(e) for e in rule["enum"]]:
                out.append(Violation(rn, name, "enum", raw, "not one of %s" % ", ".join(map(str, rule["enum"]))))
            if "pattern" in rule and not re.fullmatch(rule["pattern"], raw):
                out.append(Violation(rn, name, "pattern", raw, "does not match %s" % rule["pattern"]))
            if "min_length" in rule and len(raw) < rule["min_length"]:
                out.append(Violation(rn, name, "min_length", raw, "shorter than %d" % rule["min_length"]))
            if "max_length" in rule and len(raw) > rule["max_length"]:
                out.append(Violation(rn, name, "max_length", raw, "longer than %d" % rule["max_length"]))
            if name in seen:
                if raw in seen[name]:
                    out.append(Violation(rn, name, "unique", raw, "duplicate of row %d" % seen[name][raw]))
                else:
                    seen[name][raw] = rn
        if pk:
            key = tuple(row[idx[c]] if c in idx and idx[c] < len(row) else "" for c in pk)
            if key in pk_seen:
                out.append(Violation(rn, "+".join(pk), "primary-key", "|".join(key), "duplicate key (row %d)" % pk_seen[key]))
            pk_seen.setdefault(key, rn)
        for rr in schema.get("row_rules", []):
            cond = all(str(row[idx[c]]).strip() == str(v) for c, v in rr["if"].items() if c in idx)
            if cond:
                for c, req in rr["then"].items():
                    val = typed.get(c)
                    if req == "required" and val in (None, ""):
                        out.append(Violation(rn, c, "row-rule", "", rr.get("message", "required when %s" % rr["if"])))
                    elif req == "empty" and val not in (None, ""):
                        out.append(Violation(rn, c, "row-rule", str(val), rr.get("message", "must be empty when %s" % rr["if"])))
        if len(out) >= max_errors:
            break
    return out


def validate_file(path, schema, max_errors=1000):
    with open(path, encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.reader(fh, delimiter=schema.get("delimiter", ",")))
    if not rows:
        return [Violation(0, "", "empty", "", "file is empty")]
    return validate_rows(rows[0], rows[1:], schema, max_errors)


def summarize(violations):
    return Counter((v.column, v.rule) for v in violations)
