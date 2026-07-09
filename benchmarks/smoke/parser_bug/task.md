# Task: Fix parser whitespace handling

Fix the parser so it strips surrounding whitespace before returning the parsed value.

## Acceptance

- `parse_value("  miku  ")` returns `"miku"`.
- Existing non-whitespace behavior remains unchanged.
