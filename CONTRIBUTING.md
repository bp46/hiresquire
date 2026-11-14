# Contributing

## Setup

```bash
git clone https://github.com/bp46/hiresquire.git
cd hiresquire
python -m pip install -e ".[dev]"
```

## Workflow

1. Create a feature branch from `main`.
2. Implement changes; add/update tests under `tests/`.
3. Run `ruff check src tests`, `ruff format src tests`, `mypy src`, and `pytest`.
4. Open a pull request.

## Releasing

Releases are published to PyPI automatically via GitHub release (`publish.yml`).
Bump `__version__` in `src/hiresquire/__version__.py` and update `CHANGELOG.md`.
