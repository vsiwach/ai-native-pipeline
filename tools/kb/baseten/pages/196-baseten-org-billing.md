# baseten org billing
Source: https://docs.baseten.co/reference/cli/baseten/org-billing

View billing information

## usage

```sh theme={"system"}
baseten org billing usage [OPTIONS]
```

Show a billing usage summary for the organization. Pass `--since` (relative duration, e.g. 7d, 24h) for a sliding window ending now, or `--start` and `--end` together for an explicit ISO 8601 range. The two modes are mutually exclusive. The range cannot exceed 31 days. Defaults to `--since` 7d.

### Options

<ParamField type="TEXT">
  End of the window. Accepts ISO 8601; values without a timezone are interpreted in the local timezone. Requires --start. Mutually exclusive with --since.
</ParamField>

<ParamField type="TEXT">
  Filter JSON output with a jq expression; implies --output json (or jsonl for streamed commands)
</ParamField>

<ParamField type="TEXT">
  Output format

  One of: `text`, `json`, `jsonl`, `none`
</ParamField>

<ParamField type="TEXT">
  Use a specific stored profile for this command, overriding BASETEN\_PROFILE and the current profile
</ParamField>

<ParamField type="TEXT">
  Relative window ending now (e.g. 24h, 7d). Used when neither --start nor --end is given. Maximum 31d. Mutually exclusive with --start/--end.
</ParamField>

<ParamField type="TEXT">
  Start of the window. Accepts ISO 8601 (e.g. '2026-05-01', '2026-05-01T12:00:00Z'); values without a timezone are interpreted in the local timezone. Requires --end. Mutually exclusive with --since.
</ParamField>

<ParamField type="BOOL">
  Enable verbose logging
</ParamField>

### Examples

Show usage over the last 7 days (default)

```sh theme={"system"}
baseten org billing usage
```

Show usage over an explicit ISO 8601 range

```sh theme={"system"}
baseten org billing usage --start 2026-05-01 --end 2026-05-08
```

### Filter output with `--jq`

Print a top-level total (shape TBD)

```sh theme={"system"}
baseten org billing usage --jq '.total'
```

### Output

**Text mode (`--output text`):** Not yet implemented. The output shape is TBD.

**JSON mode (`--output json`):** payload type `map[string]interface {}`.
