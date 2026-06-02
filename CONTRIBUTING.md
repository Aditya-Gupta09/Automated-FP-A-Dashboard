# Contributing

## Getting started

```bash
git clone https://github.com/Aditya-Gupta09/Automated-FP-A-Dashboard.git
cd Automated-FP-A-Dashboard
make install-dev
make etl
make test
```

## Branch naming

```
feature/  add-comps-table
fix/      balance-sheet-loop-indent
docs/     update-data-dictionary
test/     add-dcf-golden-output
```

## Before submitting a PR

1. `make lint` — zero ruff errors
2. `make test` — all tests pass including invariants
3. If you changed financial logic: add or update a golden output test with the 10-K source cited
4. If you changed model structure: update `docs/ARCHITECTURE.md`
5. If you changed an assumption: update `config/assumptions.json` and document the source

## Financial modeling standards

- All assumptions must have a documented source (filing, database, date)
- Never modify `data/raw/` files — they are the source of truth
- New financial functions must have a pure function signature (no global state)
- All division operations must use `safe_divide()` from `src/utils/safe_math.py`
- Financial invariants must pass after any model change
