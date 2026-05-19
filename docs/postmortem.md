# Postmortem: Dagster failed to load assets with `DagsterInvalidDefinitionError`

**Date:** 2026-05-18
**Severity:** Build-time (no production impact — caught before first run)
**Author:** Samer

## Summary

The first end-to-end load of the Dagster definitions module raised
`DagsterInvalidDefinitionError: Cannot annotate context parameter with type
AssetExecutionContext`. The asset code looked correct against the
documented signature, so the error was non-obvious.

## Impact

- Dagster UI would not start.
- `dagster asset materialize` could not be invoked.
- No data was lost; nothing was running yet.
- Time-to-detect: 0s (caught by `python -c "from dach_jobs import defs"`).
- Time-to-recover: ~2 minutes once root cause was identified.

## Timeline

- **T+0** — Wrote `dach_jobs/assets/bronze.py` with
  `from __future__ import annotations` at the top of the file (the
  standard modern Python idiom) and `def bronze_arbeitnow_jobs(context:
  AssetExecutionContext, ...)`.
- **T+5m** — Ran `python -c "from dach_jobs import defs"` as a smoke check.
- **T+5m** — Stack trace pointed at Dagster's `_validate_context_type_hint`
  failing on the asset's `context` parameter.

## Root cause

`from __future__ import annotations` makes *all* annotations strings at
runtime (PEP 563). Dagster's asset decorator introspects the runtime type
of `context` directly via `inspect.signature(...).parameters[…].annotation`
to enforce that the parameter is one of a small allow-list of context
types. With deferred annotations, the runtime annotation is the *string*
`"AssetExecutionContext"`, not the class — Dagster sees an unknown type
and refuses to build the op.

This is a real PEP-563-vs-runtime-introspection collision; Pydantic v2,
FastAPI, and SQLAlchemy 2.x all hit variants of the same issue.

## Fix

Removed `from __future__ import annotations` from the asset module only.
The rest of the codebase keeps it (no introspection-dependent decorators
elsewhere).

```diff
- from __future__ import annotations
-
  import io
```

`ruff check` still passes; the asset still type-checks.

## What we changed

- Documented this trap in `docs/postmortem.md` (you're reading it).
- Considered adding a CI guard that fails if `from __future__ import
  annotations` appears in any file under `dach_jobs/assets/` — decided
  against it for now; the smoke check (`python -c "from dach_jobs import
  defs"`) catches the failure mode reliably and lives in CI already.

## What we got right

- Smoke-checked Definitions loading immediately after writing them.
  This is now a standing rule for every new asset module.
- The fix was a one-line revert; the surrounding code was correct.

## What we'd do differently

- Add `python -c "from dach_jobs import defs"` to the pre-commit hook
  set so the failure surfaces on commit, not on CI or in the UI.
