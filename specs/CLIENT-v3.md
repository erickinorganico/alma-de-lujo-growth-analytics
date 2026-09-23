# Client delivery v0.3

The customer should be able to enter their own non-personal business aggregates,
evaluate stock and pricing, and discuss the next week's choices without Python,
GitHub, database knowledge or an AI subscription. This supplements the v0.2
warehouse and native-agent evidence; it does not turn aggregates into fabricated
orders, customers or accounting events.

## Delivered working materials

- A blank Excel workbook ready for the client's inputs, plus a clearly synthetic
  worked example using Pilates socks and sportswear. Formula cells calculate in
  Excel; blue input cells, validation, filters, frozen headers, print areas and
  obvious missing-input states help prevent accidental misuse.
- INICIO instructions, CONFIG assumptions, CATALOGO unit economics, VENTAS daily
  SKU aggregates, STOCK snapshot and purchase scenarios, CAJA existing planned
  cash flows, DECISIONES SKU review and FLUJO_13_SEMANAS cash forecast. No macros,
  external workbook links, embedded credentials or customer identities.
- Short customer guide, first-week walkthrough and a 30-minute weekly meeting
  agenda. Include realistic example decisions and limitations, not a list of
  engineering components. Deliver a compact client ZIP separate from the repo.
- Optional analyst command validates workbook inputs and creates a private
  report, discrepancy list and native-agent briefing. It does not require the
  30-table synthetic import contract and does not upload customer data.

## Interfaces and decisions

[client/contract.json](../client/contract.json) defines exact sheet names, input
columns, capacities, parameter cells, units, formulas and treatment of missing
data. The 13-week projection groups 91 daily closings into weeks, exposes each week's
minimum daily cash, and warns that intraday timing remains unobserved. Planned purchases assume full payment on one
chosen date; split installments need a separately reconciled plan.

The workbook answers: which SKUs need evidence before a purchase; which fully
observed SKUs warrant a conditional quantity proposal; what price meets an
editable contribution-margin target; how much stock the chosen quantities tie
up in cash; and whether the plan breaches a protected cash floor. Unknown costs,
unobserved availability, incomplete sales, stale counts and unconfirmed policy
withhold the corresponding recommendation. No real stock, demand, price or
policy is asserted by the synthetic example.

## Acceptance

1. Open and navigate the example and blank workbooks without code or network.
2. Edit price/cost and see contribution/target price change; infeasible margin
   assumptions show a readable state and no spreadsheet error.
3. Edit stock and a full observed sales window; verify MOQ/pack-rounded proposal
   by hand. Partial availability, missing cost, late transit and stale counts
   must not silently become a confident purchase suggestion.
4. Plan a purchase and see its cash effect on the correct week; verify budget
   and protected-floor breach using independent arithmetic.
5. Preserve unknown vs zero, returns vs restock vs refund cash, and optional
   variable-cost coverage. Reject duplicate SKUs/date-SKU aggregates and invalid
   pasted inputs in the analyst validator.
6. Verify every formula after recalculation in an actual spreadsheet engine and
   inspect print/export layout. Cached initial values must agree with formulas.
7. Validate privacy boundaries and public release artifacts. Filled client
   workbooks and reports belong in an ignored local directory and are excluded
   from the public repository and client example package.
8. Keep v0.2 evidence immutable and rerun affected regression/CI gates. A native
   reviewer must challenge the new workbook's financial and inventory semantics.

Real client adoption and correctness of supplied business records remain
unverified until the client uses the material. This release measures the working
workflow and deterministic acceptance scenarios, not business impact.
