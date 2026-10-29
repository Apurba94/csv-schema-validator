import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout

from csv_schema_validator.cli import main
from csv_schema_validator.core import validate_rows

SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "..", "examples", "schema.json")
with open(SCHEMA_PATH, encoding="utf-8") as fh:
    SCHEMA = json.load(fh)
HEADER = ["subject_id", "visit", "date", "age", "sex", "pregnant", "weight_kg"]
GOOD = ["S001", "1", "2026-01-05", "34", "F", "no", "61.5"]


def rules(rows, header=HEADER, schema=SCHEMA):
    return [(v.row, v.column, v.rule) for v in validate_rows(header, rows, schema)]


class ValidateTests(unittest.TestCase):
    def test_valid(self):
        self.assertEqual(rules([GOOD]), [])

    def test_type_range_enum_pattern(self):
        bad = ["X1", "4", "05/01/2026", "17", "female", "maybe", "abc"]
        got = {r[2] for r in rules([bad])}
        self.assertEqual(got, {"pattern", "enum", "type", "min"})
        self.assertEqual(len(rules([bad])), 7)

    def test_required_and_missing_values(self):
        row = ["", "1", "NA", "NA", "F", "", ""]
        self.assertEqual(rules([row]), [(2, "subject_id", "required"), (2, "date", "required")])

    def test_primary_key(self):
        self.assertEqual(rules([GOOD, list(GOOD)]), [(3, "subject_id+visit", "primary-key")])

    def test_row_rule(self):
        male = ["S002", "1", "2026-01-05", "40", "M", "yes", "80"]
        self.assertEqual(rules([male]), [(2, "pregnant", "row-rule")])

    def test_columns_strict_and_row_length(self):
        got = rules([["S001", "1"]], header=["subject_id", "visit", "extra"])
        self.assertIn((0, "date", "missing-column"), got)
        self.assertIn((0, "extra", "unexpected-column"), got)
        self.assertIn((2, "", "row-length"), got)

    def test_unique(self):
        schema = {"columns": {"id": {"unique": True}}}
        self.assertEqual(rules([["a"], ["b"], ["a"]], ["id"], schema), [(4, "id", "unique")])

    def test_cli(self):
        with tempfile.TemporaryDirectory() as d:
            p, rep = os.path.join(d, "d.csv"), os.path.join(d, "r.csv")
            with open(p, "w", encoding="utf-8") as fh:
                fh.write(",".join(HEADER) + "\n" + ",".join(GOOD) + "\nS003,9,2026-01-01,50,F,no,70\n")
            with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()) as err:
                self.assertEqual(main([p, SCHEMA_PATH, "--report", rep]), 1)
            self.assertIn("INVALID: 1 violation", err.getvalue())
            self.assertTrue(os.path.exists(rep))


if __name__ == "__main__":
    unittest.main()
