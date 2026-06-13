# Contributing

Thanks for your interest! This monorepo contains 100+ independent
data-engineering projects. Each one lives in its own directory with its
own `pyproject.toml`, tests, and CI workflow.

## Quick start

```bash
# 1. Fork & clone
git clone https://github.com/<your-username>/data-engineering.git
cd data-engineering

# 2. Pick a project
cd log-based-cdc-from-scratch

# 3. Install dev deps + run the quality gate
pip install -e ".[dev]"
make lint      # ruff
make format    # ruff format
make type      # mypy --strict
make test      # pytest

# 4. Commit on a branch
git checkout -b feat/<short-description>
git commit -m "<scope>: <what & why>"
git push origin feat/<short-description>
```

## What kinds of PRs are welcome?

**Yes please:**

- 🐛 Bug fixes with a regression test.
- 🧪 New tests covering edge cases the current suite misses (every project's `tests/` is small enough to read in one sitting — gaps are easy to spot).
- 📚 Doc improvements — typos, clearer docstrings, README polish.
- ⚡ Performance improvements with a benchmark showing the gain.
- 🔌 Real-backend adapters wired into a project's existing injectable interface
  (e.g. a `psycopg2` adapter for `api-rate-limit-orchestrator`'s `StorageBackend`).
- 📦 New small projects in the spirit of the existing ones (production-grade,
  typed, tested, single-purpose). Open an issue first to discuss scope.

**Probably no, but ask first:**

- Wholesale renames / restructures of an existing project.
- Adding heavy runtime dependencies. Most projects deliberately stay
  stdlib-only or with one small optional extra.
- Changes that lower the test count or remove invariants.

## Quality bar

Every PR must pass each affected project's CI matrix:

- **ruff** — lint clean (`make lint`).
- **ruff format** — formatted (`make format`, then `git diff` should be empty).
- **mypy --strict** — fully typed (`make type`).
- **pytest** — all tests pass (`make test`).
- **Docker** — `make docker` builds the production image.

Most projects already enforce all five on every push via
`.github/workflows/<slug>.yml`. CI will catch anything you miss locally.

## Commit messages

```
<project-slug>: <subject under 70 chars>

Optional body. Explain *why* the change was needed. Reference the
issue number if there is one.
```

Examples:
```
multi-source-collector: handle UTF-16 BOM in CSV source
log-based-cdc-from-scratch: decode pgoutput TYPE messages
delta-vs-iceberg-vs-hudi: add Hudi compaction-throughput test
```

Squash to one commit per logical change. The maintainer may rebase
on merge.

## Tests are non-negotiable

Every new behaviour ships with a test. Bug fixes ship with a
regression test *that fails on `main` and passes on the PR*. Property
tests (Hypothesis) are encouraged for any code with a tractable
invariant.

## Code of conduct

By participating, you agree to the
[Contributor Covenant](CODE_OF_CONDUCT.md).

## Security issues

Don't open a public issue. Email the maintainer (see
[SECURITY.md](SECURITY.md)) — we'll coordinate disclosure.

## License

By contributing, you agree your work is licensed under the
[MIT License](LICENSE).
