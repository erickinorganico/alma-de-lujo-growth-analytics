---
phase: 01-versioned-operating-intake
plan: 01
subsystem: data-contract
tags: [python, csv, json, source-packs, unittest]

# Dependency graph
requires: []
provides:
  - Ordered operating-v1 registry for 22 aggregate sources
  - Exact metadata and canonical identity contract
  - Deterministic public blank and synthetic source packs
  - Linked synthetic cash, stock, reservation, budget, quality, and receipt evidence
affects: [01-02, 01-03, reconciled-decision-metrics]

# Tech tracking
tech-stack:
  added: []
  patterns: [registry-driven CSV schemas, canonical JSON bytes, fail-closed pack initialization]

key-files:
  created:
    - alma/operating_contracts.py
    - scripts/operating_pack.py
    - tests/test_operating_contracts.py
    - client/source-packs/v1/blank/
    - client/source-packs/v1/synthetic/
  modified: []

key-decisions:
  - "Keep operating-v1 isolated from the released v0.2 row-level interchange and warehouse contracts."
  - "Represent nullable uniqueness explicitly for delivery cohorts and cash supersession predecessors."
  - "Validate America/Tijuana offset deterministically on Windows even when the Python runtime has no IANA tzdata package."

patterns-established:
  - "Registry ownership: later intake code imports ordered fields, keys, relationships, metadata vocabulary, and identity preimage names from one module."
  - "Pack reproducibility: metadata uses canonical sorted JSON and CSV uses UTF-8 with stable LF line endings."
  - "Public provenance: every example row uses a bounded synthetic source_ref and public generation accepts only blank or synthetic kinds."

requirements-completed: [DATA-01, DATA-04]

# Metrics
duration: 21min
completed: 2026-09-22
---

# Phase 1 Plan 01: Versioned Operating Source Contracts Summary

**Exact 22-source operating-v1 registry with reproducible blank and linked synthetic packs, including cash forecast supersession and receipt-quality evidence**

## Performance

- **Duration:** 21 min
- **Started:** 2026-09-23T02:55:19Z
- **Completed:** 2026-09-23T03:16:11Z
- **Tasks:** 2
- **Files modified:** 49

## Accomplishments

- Defined exact ordered headers, field types, nullable states, units, enum allowlists, keys, foreign relationships, provenance, coverage vocabulary, and canonical identity fields for all 22 sources.
- Added strict metadata validation for contract version, input class, MXN currency, coverage keys and states, local cutoff windows, and IANA timezone/offset agreement while keeping BLANK templates non-buildable.
- Published byte-reproducible blank and synthetic packs. The synthetic pack links 20 ordered units to 18 received, 2 inspected, 16 accepted, stock movements, reservations, availability, unmet demand, purchase and expense allocations, observed cash balances, delivery-cohort quality, and one forecast-to-observed cash supersession chain.
- Added overwrite and public-input protections plus literal scans for bounded non-PII fields and values.

## Task Commits

Each task was committed atomically with its TDD gates:

1. **Task 1 RED: Define the versioned source registry and metadata contract** - `fbc1be8` (test)
2. **Task 1 GREEN: Define the versioned source registry and metadata contract** - `70fe55f` (feat)
3. **Task 2 RED: Generate public blank and synthetic source packs** - `e92c843` (test)
4. **Task 2 GREEN: Generate public blank and synthetic source packs** - `a448cbc` (feat)

## Files Created/Modified

- `alma/operating_contracts.py` - Sole ordered registry, canonical JSON function, stable error type, and metadata validator.
- `scripts/operating_pack.py` - Guarded `init --kind blank|synthetic --output PATH` command and linked fixture definitions.
- `tests/test_operating_contracts.py` - Literal contract, metadata, deterministic pack, privacy, refusal, and linked-evidence tests.
- `client/source-packs/v1/blank/` - Metadata plus 22 header-only CSV templates.
- `client/source-packs/v1/synthetic/` - Metadata plus 22 visibly synthetic, cross-domain CSV examples.

## Decisions Made

- JSON object member order is not treated as contract state; canonical serialization sorts it, while CSV column order remains exact and executable.
- Nullable unique values use `unique_non_null` declarations so multiple absent cohort/predecessor values do not conflict and present values remain unique.
- The only built-in timezone fallback is `America/Tijuana`, calculated with its border DST rule. Unknown IANA zones still fail closed when the host has no zone database.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Added deterministic Tijuana timezone validation for the Windows runtime**
- **Found during:** Task 1 GREEN
- **Issue:** The repository's Python 3.12 runtime has no system IANA database or `tzdata` package, so standard-library `ZoneInfo` rejected the required `America/Tijuana` zone.
- **Fix:** Added a narrow standard-library fallback that computes Tijuana's border DST offset and still rejects unknown zones or mismatched offsets.
- **Files modified:** `alma/operating_contracts.py`
- **Verification:** Valid Tijuana metadata passes; invalid zones and mismatched offsets fail with stable safe codes.
- **Committed in:** `70fe55f`

**2. [Rule 1 - Bug] Removed JSON insertion-order dependence from metadata validation**
- **Found during:** Task 2 GREEN
- **Issue:** Canonical sorted JSON reorders object members, but the first validator implementation also compared Python dictionary insertion order.
- **Fix:** Validation now requires the exact metadata and coverage key sets without assigning semantics to JSON member order.
- **Files modified:** `alma/operating_contracts.py`
- **Verification:** Checked-in canonical metadata reloads and validates, and both packs regenerate byte for byte.
- **Committed in:** `a448cbc`

---

**Total deviations:** 2 auto-fixed (1 blocking issue, 1 bug)
**Impact on plan:** Both fixes preserve fail-closed validation and deterministic output without adding dependencies or changing the published contract.

## Issues Encountered

- Concurrent agents updated plans in later phases while this plan executed. Those files were left untouched and excluded from every 01-01 commit.

## Authentication Gates

None.

## Known Stubs

None. Header-only blank CSVs are the intentional BLANK template output; the synthetic pack contains linked evidence in every source.

## Verification Evidence

- `.venv\Scripts\python.exe -m unittest discover -s tests -p 'test_operating_contracts.py' -v` — 13 tests passed in 2.158 seconds.
- `.venv\Scripts\python.exe -m compileall -q alma\operating_contracts.py scripts\operating_pack.py` — passed.
- The focused suite regenerates both packs in temporary destinations and compares all 46 generated files with checked-in bytes.
- The phase-wide v0.2/v0.3 regression gate remains assigned to plan 01-03 by `01-VALIDATION.md`.

## User Setup Required

None - no external service configuration or dependency installation is required.

## Next Phase Readiness

- Plans 01-02 and 01-03 can import ordered source definitions, metadata coverage states, identity preimage fields, and synthetic fixtures without duplicating the contract.
- Shared planning state files were intentionally left to the orchestrator because this executor's ownership was limited to 01-01 frontmatter files and this summary.

## Self-Check: PASSED

- All registry, generator, test, metadata, and pack paths exist.
- Both pack directories contain exactly 23 files: metadata plus 22 CSVs.
- All four RED/GREEN task commits are present in Git history.

---
*Phase: 01-versioned-operating-intake*
*Completed: 2026-09-22*
