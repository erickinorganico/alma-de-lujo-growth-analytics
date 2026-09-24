# Integration Gaps Before v1.0

## Blockers

1. **Workbook cut to native review**: `alma/client_review.py` stops after writing a report and analyst brief. It does not produce a validated analyst response, independent review or decision packet.
2. **Current cut to marts**: `alma/workspace.py` and `scripts/build_client_system.py` are bound to the historical synthetic v0.2 workspace. A private client cut cannot create current aggregate marts without fabricating row-level data.
3. **Decision closure**: `client/REGISTRO_DECISIONES.csv` is intentionally blank and has no validator, source hash, carry-forward or closure rule.
4. **Operations extension**: the eight cost/operations sources are hardcoded examples and separate from the workbook and canonical warehouse.
5. **First-cut onboarding**: no reusable versioned operating data pack, quarantine workflow, backup/restore receipt or current-cut manifest exists.

## Warnings

- The v0.3 ZIP does not include the private validator/native-cycle procedure as a runnable analyst kit.
- Atlas labeling is clear but historical v0.2 packets can still be confused with a current private cut.
- CI verifies a recorded Excel receipt on Linux; changed formulas require a fresh Windows Excel recalculation.
- Tax, opening bank balance, content rights and business role assignments require owner-supplied evidence.

## Resolution strategy

Create a v1 aggregate operating workspace with explicit sources, SQLite, marts, quality, lineage and immutable manifest. Add a separate client-cycle bridge that binds report hashes to native responses, independent review, decision register and next-cut carry-forward. Regenerate the final portal and package from public synthetic example and blank template only.
