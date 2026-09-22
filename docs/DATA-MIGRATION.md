> Historical v0.1 reference. Current implementation and acceptance: [v0.2 PRD](../specs/PRD.md), [runbook](RUNBOOK-v2.md), and [release evidence](RELEASE.md).

# Data migration and owner discovery

Confirmed by user: Alma de Lujo sells sportswear and will sell Pilates socks in multiple colors. The user believes socks may be the winning product. Instagram URL is recorded in the market register; latest garments could not be verified by the available public-page retrieval. No photo, price, customer information or post was imported. Product labels/colors/prices/costs and activity in this repository are invented examples.

Before real operation, resolve: own inventory vs preorder, actual SKU/color/size list, channel definitions, supplier lead times, minimum lots, cost and freight policy, returns policy, discounts, payment/fulfillment steps, opening stock/cash, and accountability. Confirm formulas in DOMAIN.md with the owner before approving metrics. The technical delivery is complete independently of these business choices; real-operation readiness remains pending.

## CSV preparation route

1. Run the demo. `build/demo/csv` contains one canonical CSV per table and `metadata.json` with explicit coverage and synthetic provenance.
2. Copy the whole directory to a disposable local folder. Keep headers exactly; IDs stable and unique; dates ISO YYYY-MM-DD; money integer MXN cents. Empty is only allowed for documented nullable fields. A missing input table must never be replaced by a falsely complete empty table.
3. Run `python -m alma demo --csv-input path/to/synthetic-csv --output build/import-review`. The input boundary rejects unknown columns, real provenance, malformed values and incomplete schemas. Quality failures produce a blocked report; structural errors withhold the report.
4. Review quality, packet and source receipts. This is a tested synthetic interchange, not authorization to ingest real customer data.
5. For real exports: new approved adapter/provenance, PII minimization (surrogate customer IDs), source coverage, monetary policy, raw-to-canonical mapping and replay/duplicate handling. Preserve source IDs and receipts, validate the real schema with synthetic edge fixtures first. Then reconcile against a separately approved authoritative source before use.

API integrations, Sheets accounts, Instagram/Meta access, messaging and live transactional operations are not implemented or connected. A human approval flag inside a dataset never enables external actions.
