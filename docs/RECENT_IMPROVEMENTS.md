# Automation-friendly context reports

This guide covers implemented behavior. It does not change deployment or account configuration.

## Usage

```bash
python3 -m slice_ctx symbols . --query cli --json
python3 -m slice_ctx analyze . --target slice_ctx.cli.main --json --include-source --output report.json
python3 -m slice_ctx analyze . --target slice_ctx.cli.main --strict --max-symbols 100 --json
```

## Contracts and limits

- symbols lists stable, sorted fully qualified names. Query matching is case-insensitive.
- --include-source adds rendered context to JSON. The default JSON report remains metadata-only.
- --strict exits 3 when the static-analysis report is unsound. --max-symbols exits 4 when the complete slice exceeds budget; it never silently truncates dependencies. Strict status takes precedence.
- Output is rendered before atomic replacement. An unknown target leaves an existing output file untouched. Usage errors exit 2, while ordinary target/I/O errors exit 1.

## Source map

- [`slice_ctx/cli.py`](../slice_ctx/cli.py)
<!-- source: slice_ctx/cli.py -->
- [`tests/test_cli_round2.py`](../tests/test_cli_round2.py)
<!-- source: tests/test_cli_round2.py -->

## Regression command

Run from the repository root:

```sh
python3 -m unittest discover -s tests -v
```


## Discovery and context budgets

`symbols` accepts `--kind`, `--module`, `--limit`, `--offset`, and `--details --json`. Paging reports full match counts and continuation metadata. Details contain navigation locations, not source text. `analyze --max-tokens N` writes the complete report and exits 5 if rendered context exceeds the reported tokenizer/heuristic budget. Soundness (3) and symbol limits (4) take precedence. No dependency context is silently truncated.
