# Lilya Baseline Measurement Report
Date: 2026-02-16

## Coverage
- **Total**: 92.0%
- **Core modules**:

| Module | Coverage | Statements | Missing |
|--------|----------|------------|---------|
| lilya/routing.py | 88% | 875 | 101 |
| lilya/apps.py | 91% | 253 | 22 |
| lilya/responses.py | 93% | 716 | 52 |
| lilya/dependencies.py | 81% | 376 | 72 |

- **Gap to 100%**: 2744 uncovered lines across the entire project (Total: 33484 statements).

## Mypy Error Codes
- **Current suppressed**: 6 codes (attr-defined, has-type, override, misc, safe-super, import-untyped) and 3 boolean flags (strict_optional, no_implicit_optional, strict_equality).
- **Error counts per code**:

| Code/Flag | Error Count |
|-----------|-------------|
| no_implicit_optional | 1 |
| import-untyped | 3 |
| strict_equality | 6 |
| has-type | 7 |
| safe-super | 11 |
| override | 19 |
| misc | 19 |
| attr-defined | 100 |
| strict_optional | 135 |
| **Total** | **301** |

- **Recommended enablement order**:
  1. `no_implicit_optional` (1)
  2. `import-untyped` (3)
  3. `strict_equality` (6)
  4. `has-type` (7)
  5. `safe-super` (11)
  6. `override` (19)
  7. `misc` (19)
  8. `attr-defined` (100)
  9. `strict_optional` (135)
- **Interdependencies noted**: `strict_optional` enablement is likely to resolve or reveal more `attr-defined` errors, as many attribute access errors stem from potential `None` values.

## docs_src Categorization
- **Total files**: 308
- **By category**:

| Category | Count | Percentage | Description |
|----------|-------|------------|-------------|
| Executable | ~209 | 67.9% | Instantiates `Lilya` app or ASGI app |
| Snippet-only | ~83 | 26.9% | Decorators, utility classes, partial code |
| External-dep | ~16 | 5.2% | Requires Redis, Postgres, or MongoDB |

- **By subdirectory (Sample)**:
  - `routing/`: 45 files (Mostly executable)
  - `middleware/`: 34 files (Mostly executable)
  - `responses/`: 26 files (Executable)
  - `openapi/`: 26 files (Mixed)
  - `dependencies/`: 15 files (Mixed)
- **Recommended verification strategy per category**:
  - **Executable**: Automated import tests and basic TestClient GET/POST requests.
  - **Snippet-only**: Require integration wrappers or minimal app shells for testing.
  - **External-dep**: Requires service mocking (e.g., fakeredis) or dedicated test environment with sidecars.

## Import Dependency Graph
- **Core module cross-dependencies**:

| Module | Imports From |
|--------|--------------|
| lilya/apps.py | routing, dependencies, responses |
| lilya/routing.py | dependencies, responses |
| lilya/responses.py | (Foundation - no cross-imports) |
| lilya/dependencies.py | (Foundation - no cross-imports) |

- **External consumer count per module**:

| Module | Consuming Files | Total Imports |
|--------|-----------------|---------------|
| lilya/apps.py | 17 | 41 |
| lilya/routing.py | 17 | 38 |
| lilya/responses.py | 28 | 33 |
| lilya/dependencies.py | 4 | 4 |

- **Circular imports**: None found between core modules. Dependency hierarchy flows cleanly upward from Foundation (Level 1) to Routing (Level 2) to Application (Level 3).
- **Recommended decomposition targets**: `lilya/routing.py` is the primary target for decomposition due to its size (2773 lines), central role as an integration layer, and high number of external consumers.
