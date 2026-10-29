"""Command-line interface for csv-schema-validator."""
import argparse
import csv
import json
import sys

from .core import summarize, validate_file


def main(argv=None):
    ap = argparse.ArgumentParser(prog="csv-schema-validator", description="Validate a CSV against a JSON schema.")
    ap.add_argument("csvfile")
    ap.add_argument("schema", help="JSON schema file")
    ap.add_argument("--max-errors", type=int, default=1000)
    ap.add_argument("--report", help="write all violations to this CSV")
    ap.add_argument("-q", "--quiet", action="store_true", help="summary only")
    args = ap.parse_args(argv)
    with open(args.schema, encoding="utf-8") as fh:
        schema = json.load(fh)
    viol = validate_file(args.csvfile, schema, args.max_errors)
    if not args.quiet:
        for v in viol[:200]:
            print("row %s, %s: [%s] %r %s" % (v.row or "-", v.column or "-", v.rule, v.value, v.message))
    for (col, rule), n in sorted(summarize(viol).items()):
        print("  %-20s %-15s %d" % (col, rule, n), file=sys.stderr)
    print("%s: %d violation(s)" % ("VALID" if not viol else "INVALID", len(viol)), file=sys.stderr)
    if args.report:
        with open(args.report, "w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(["row", "column", "rule", "value", "message"])
            w.writerows(viol)
    return 1 if viol else 0
