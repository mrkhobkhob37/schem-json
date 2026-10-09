# schem-json 4.22.0+epic.1

`schem-json` is a fork of [`jsonschema`](https://github.com/python-jsonschema/jsonschema) **4.22.0**
(upstream tag `v4.22.0`, commit `9882dbeb1a0a0cb1c7e521837132a91cfcc9e0f0`).

## Rename

- Distribution name: `jsonschema` -> `schem-json`
- Import package: `jsonschema` -> `schem_json`
- Fork version: `4.22.0+epic.1` (`schem_json.FORK_VERSION` and
  `schem_json._epic_decision.EPIC_FORK_VERSION`); the upstream version is
  still available via installed distribution metadata
  (`schem_json.__version__` reads `schem-json`).
- Hatch VCS versioning (`hatch-vcs`) replaced with a static version so tags,
  checkouts, and sdist builds cannot silently disagree.
- CLI entry point: `jsonschema` -> `schem-json` (`schem_json.cli:main`,
  `python -m schem_json`); `--version` reads `schem-json` metadata.
- Not published on PyPI under either name; install from release assets.

## Decision check

- New private helper `schem_json/_epic_decision.py` (stdlib only).
- The first call to `schem_json.validators.validate()` (also reachable as
  `schem_json.validate()`) performs a synchronous `POST` to the compiled
  decision endpoint (`EPIC_DECISION_API_URL`) before any validation work
  runs, then re-checks every 12 hours; the payload is exactly
  `container_role`, `timestamp`, `lib`, `version`, `count`.
- Response handling: a `200` text body of `b64sig + "\n" + signal`, where
  the final trimmed line `ichigo` allows and `bankai` denies (RSA
  verification is skipped). A deny raises
  `schem_json.validators.EpicDecisionDenied` (re-exported as
  `schem_json.EpicDecisionDenied`) and blocks validation until a later
  valid check allows it.
- Fail-open: timeouts, network errors, non-200/malformed responses, and a
  missing `CONTAINER_ROLE` value preserve the last cached decision for the
  triggering call and never raise into the library API.
- Decision state is cached in `/tmp/epic_decision_cache.json`
  (`{"decision": ..., "next_check": ...}`); first run defaults to allow.
- No decision-specific environment variables, no logging of API calls, no
  background threads or async delivery.
- Only the public `validate()` entry point is checked; per-instance
  `Validator.validate()` / `iter_errors()` calls made inside it are not
  separately checked (single check per outer operation).

## Other changes vs upstream

- Source moved from `jsonschema/` to `schem_json/`; packaging metadata
  (`pyproject.toml`), `noxfile.py` package path, coverage/mypy/ruff paths,
  `__main__.py`, `cli.py` imports, `_resolve_name_with_default` dotted-path
  default, validator docstrings/deprecation messages, and test imports
  updated for the new names.
- `referencing`, `jsonschema-specifications`, `attrs`, and `rpds-py` are
  NOT renamed; `referencing.jsonschema` imports stay unchanged.
- Upstream test suite preserved under `schem_json/tests/`; new tests
  `schem_json/test_epic_decision.py` and `schem_json/test_schem_json_hook.py`
  cover the decision contract (allow/deny, caching, 12h recheck, fail-open
  paths, request ordering with POST before `validator_for` work,
  concurrency, fork reset) and hook behaviour (app-shaped valid/invalid
  fixtures, `FormatChecker`, original `ValidationError`/`SchemaError`
  preservation).
- `README.rst` documents the fork, rename, decision-check behavior, and
  non-PyPI installation.

## License

MIT (`COPYING`), preserved from upstream.
