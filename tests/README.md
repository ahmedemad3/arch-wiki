# Scanner tests

```bash
python3 -m pip install -r tests/requirements.txt   # once
python3 -m pytest tests/ -q
```

Each fixture under `tests/fixtures/` is a minimal project (Spring Boot with Gradle
Kotlin DSL, Express, FastAPI). Tests copy a fixture to a temp directory before
scanning so `docs/architecture/` output never lands in the repo.

CI runs the same suite on Python 3.9 and 3.12, with and without PyYAML (`.github/workflows/test.yml`).
