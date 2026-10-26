# Troubleshooting slice

Use the smallest reproducible fixture before changing production data or configuration. Run commands from the repository root.

## A pipeline exits 3 but writes a report

Read soundness diagnostics. This is the requested strict gate, not a serialization failure; the full report remains available.

## A slice exceeds the symbol budget

Review scope/depth and the dependency graph. The budget is a diagnostic gate, not permission to discard necessary symbols.

## A target is not found

Use symbols --query to find its fully qualified name. Repository roots and module qualification determine names.

## Reproduce and report

1. Record the exact command or UI action, runtime version, expected result, and actual result.
2. Run the regression command below on the same checkout and keep its first failure, not only the final summary.
3. Reduce the issue to a deterministic fixture without personal data or credentials.
4. Include the affected source path from the [feature guide](RECENT_IMPROVEMENTS.md) and whether it reproduces on a clean checkout.

```sh
python3 -m unittest discover -s tests -v
```

## Recovery

Keep a copy of input data before experimenting. Revert the individual source change with Git and rerun the same fixture; a source revert does not automatically reverse browser storage, downloaded files, or external service state. Do not delete a lockfile or weaken a validation gate to make a failure disappear.
