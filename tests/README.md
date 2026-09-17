# Scanner tests

```bash
python3 -m pip install pytest pyyaml   # once
python3 -m pytest tests/ -q
```

Each fixture under `tests/fixtures/` is a minimal project (Spring Boot with Gradle
Kotlin DSL, Express, FastAPI). Tests copy a fixture to a temp directory before
scanning so `docs/architecture/` output never lands in the repo.
