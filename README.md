# csv-schema-validator

**Declare what your data must look like (types, ranges, allowed values, patterns, keys,
conditional rules) in a JSON file and validate every CSV against it, with row-level error reports.**

Part of the *Research Automation Toolkit*: 100 open tools for daily research work.

## Why

Data errors are cheapest to fix at entry time. Multi-site studies, field campaigns and lab
pipelines receive CSV files from many people and instruments; one site writing `05/01/2026` or
`female` instead of `F` breaks the analysis weeks later. A machine-readable schema doubles as data
documentation and as an automatic quality gate.

## Schema

```json
{
  "strict": true,
  "primary_key": ["subject_id", "visit"],
  "missing_values": ["", "NA"],
  "columns": {
    "subject_id": {"type": "string", "required": true, "pattern": "S\\d{3}"},
    "visit": {"type": "integer", "enum": [1, 2, 3]},
    "date": {"type": "date", "format": "%Y-%m-%d"},
    "age": {"type": "integer", "min": 18, "max": 99},
    "weight_kg": {"type": "number", "min": 20, "max": 300}
  },
  "row_rules": [{"if": {"sex": "M"}, "then": {"pregnant": "empty"}}]
}
```

Column rules: `type` (string, integer, number, boolean, date), `required`, `unique`, `min`, `max`,
`enum`, `pattern`, `format`, `min_length`, `max_length`, `missing_values`. Table rules: `strict`
(no extra columns), `primary_key`, conditional `row_rules` (`required` / `empty`).

## Usage

```bash
pip install .
csv-schema-validator site3_upload.csv examples/schema.json
csv-schema-validator data.csv schema.json --report errors.csv -q
```

Exit code 1 when any violation is found, so it can run in CI or upload pipelines.

## Testing

```bash
python -m unittest discover -s tests -t .
```

## License

MIT (c) JANIN A APURBA
