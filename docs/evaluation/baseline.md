## Baseline (V0)

- commit `b5d2f67`, upstream `TauricResearch/TradingAgents@9fa1196`
- Python 3.12.16, `pip install -e ".[dev]"`
- `.venv/bin/python -m pytest -q` → 1412 passed, 1 skipped, 1 deselected

### Results

| Result   | Count |
|----------|-------|
| Passed   | 1412  |
| Failed   | 0     |
| Skipped  | 1     |

### Reproduce

```bash
git checkout b5d2f67
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
python -m pytest -q
```
