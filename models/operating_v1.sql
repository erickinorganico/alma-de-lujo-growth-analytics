CREATE TABLE sku_catalog (
  sku_id TEXT PRIMARY KEY,
  product_code TEXT NOT NULL,
  variant_code TEXT NOT NULL,
  category_code TEXT NOT NULL,
  color_code TEXT NOT NULL,
  size_code TEXT NOT NULL,
  lifecycle_status TEXT NOT NULL CHECK (lifecycle_status IN ('DRAFT','ACTIVE','RETIRED')),
  effective_date TEXT NOT NULL,
  source_ref TEXT NOT NULL
) STRICT;

CREATE TABLE sales_aggregates (
  sales_date TEXT NOT NULL,
  sku_id TEXT NOT NULL REFERENCES sku_catalog(sku_id),
  channel_code TEXT NOT NULL,
  delivery_cohort_id TEXT UNIQUE,
  delivered_units INTEGER NOT NULL CHECK (delivered_units >= 0),
  returned_units INTEGER NOT NULL CHECK (returned_units >= 0),
  restocked_units INTEGER NOT NULL CHECK (restocked_units >= 0 AND restocked_units <= returned_units),
  net_revenue_cents INTEGER NOT NULL,
  variable_cost_cents INTEGER,
  coverage_status TEXT NOT NULL CHECK (coverage_status IN ('COMPLETE','PARTIAL','ESTIMATED')),
  source_ref TEXT NOT NULL,
  PRIMARY KEY (sales_date, sku_id, channel_code)
) STRICT;

CREATE TABLE availability_daily (
  availability_date TEXT NOT NULL,
  sku_id TEXT NOT NULL REFERENCES sku_catalog(sku_id),
  observed_minutes INTEGER NOT NULL CHECK (observed_minutes BETWEEN 0 AND 1440),
  sellable_minutes INTEGER NOT NULL CHECK (sellable_minutes >= 0),
  stockout_minutes INTEGER NOT NULL CHECK (stockout_minutes >= 0),
  coverage_status TEXT NOT NULL CHECK (coverage_status IN ('COMPLETE','PARTIAL','ESTIMATED')),
  source_ref TEXT NOT NULL,
  PRIMARY KEY (availability_date, sku_id),
  CHECK (sellable_minutes + stockout_minutes <= observed_minutes)
) STRICT;

CREATE TABLE unmet_demand (
  demand_event_id TEXT PRIMARY KEY,
  event_date TEXT NOT NULL,
  sku_id TEXT NOT NULL REFERENCES sku_catalog(sku_id),
  channel_code TEXT NOT NULL,
  requested_units INTEGER NOT NULL CHECK (requested_units >= 0),
  reason_code TEXT NOT NULL CHECK (reason_code IN ('STOCKOUT','SIZE_UNAVAILABLE','OTHER_RECORDED')),
  source_ref TEXT NOT NULL
) STRICT;

CREATE TABLE inventory_counts (
  count_id TEXT PRIMARY KEY,
  sku_id TEXT NOT NULL REFERENCES sku_catalog(sku_id),
  cutoff_date TEXT NOT NULL,
  on_hand_units INTEGER NOT NULL CHECK (on_hand_units >= 0),
  reserved_units INTEGER NOT NULL CHECK (reserved_units >= 0),
  in_transit_units INTEGER NOT NULL CHECK (in_transit_units >= 0),
  non_sellable_units INTEGER NOT NULL CHECK (non_sellable_units >= 0),
  source_ref TEXT NOT NULL,
  UNIQUE (sku_id, cutoff_date),
  CHECK (reserved_units + non_sellable_units <= on_hand_units)
) STRICT;

CREATE TABLE inventory_reservations (
  reservation_event_id TEXT PRIMARY KEY,
  reservation_id TEXT NOT NULL,
  sku_id TEXT NOT NULL REFERENCES sku_catalog(sku_id),
  event_date TEXT NOT NULL,
  event_type TEXT NOT NULL CHECK (event_type IN ('PLACE','RELEASE','CONSUME')),
  units INTEGER NOT NULL CHECK (units >= 0),
  source_ref TEXT NOT NULL
) STRICT;

CREATE TABLE cost_versions (
  cost_version_id TEXT PRIMARY KEY,
  sku_id TEXT NOT NULL REFERENCES sku_catalog(sku_id),
  effective_date TEXT NOT NULL,
  lifecycle_status TEXT NOT NULL CHECK (lifecycle_status IN ('DRAFT','ACTIVE','RETIRED')),
  quantity_basis INTEGER NOT NULL CHECK (quantity_basis >= 0),
  public_price_cents INTEGER NOT NULL CHECK (public_price_cents >= 0),
  selling_fee_bps INTEGER NOT NULL CHECK (selling_fee_bps BETWEEN 0 AND 10000),
  currency TEXT NOT NULL CHECK (currency = 'MXN'),
  source_ref TEXT NOT NULL,
  UNIQUE (sku_id, effective_date)
) STRICT;

CREATE TABLE cost_components (
  component_id TEXT PRIMARY KEY,
  cost_version_id TEXT NOT NULL REFERENCES cost_versions(cost_version_id),
  component_code TEXT NOT NULL,
  classification TEXT NOT NULL CHECK (classification IN ('DIRECT','ALLOCATED','EXCLUDED')),
  amount_cents INTEGER CHECK (amount_cents >= 0),
  required_flag INTEGER NOT NULL CHECK (required_flag IN (0,1)),
  quality_status TEXT NOT NULL CHECK (quality_status IN ('KNOWN','MISSING','ESTIMATED','NOT_APPLICABLE')),
  included_in_component_id TEXT REFERENCES cost_components(component_id),
  source_ref TEXT NOT NULL,
  UNIQUE (cost_version_id, component_code),
  CHECK (included_in_component_id IS NULL OR included_in_component_id <> component_id)
) STRICT;

CREATE TABLE cost_allocations (
  allocation_id TEXT PRIMARY KEY,
  component_id TEXT NOT NULL REFERENCES cost_components(component_id),
  sku_id TEXT NOT NULL REFERENCES sku_catalog(sku_id),
  method_code TEXT NOT NULL CHECK (method_code IN ('UNITS','WEIGHT','DIRECT')),
  allocated_cents INTEGER NOT NULL CHECK (allocated_cents >= 0),
  remainder_cents INTEGER NOT NULL CHECK (remainder_cents >= 0),
  source_ref TEXT NOT NULL,
  UNIQUE (component_id, sku_id)
) STRICT;

CREATE TABLE budgets (
  budget_id TEXT PRIMARY KEY,
  period_start TEXT NOT NULL,
  period_end TEXT NOT NULL,
  drop_code TEXT NOT NULL,
  channel_code TEXT NOT NULL,
  approved_cents INTEGER NOT NULL CHECK (approved_cents >= 0),
  source_ref TEXT NOT NULL,
  UNIQUE (period_start, period_end, drop_code, channel_code),
  CHECK (period_start <= period_end)
) STRICT;

CREATE TABLE purchase_orders (
  purchase_order_id TEXT PRIMARY KEY,
  sku_id TEXT NOT NULL REFERENCES sku_catalog(sku_id),
  budget_id TEXT REFERENCES budgets(budget_id),
  ordered_units INTEGER NOT NULL CHECK (ordered_units >= 0),
  agreed_unit_cents INTEGER NOT NULL CHECK (agreed_unit_cents >= 0),
  order_date TEXT NOT NULL,
  promised_date TEXT,
  status_code TEXT NOT NULL CHECK (status_code IN ('OPEN','PARTIAL','CLOSED','CANCELLED')),
  source_ref TEXT NOT NULL,
  CHECK (promised_date IS NULL OR promised_date >= order_date)
) STRICT;

CREATE TABLE purchase_receipts (
  receipt_id TEXT PRIMARY KEY,
  purchase_order_id TEXT NOT NULL REFERENCES purchase_orders(purchase_order_id),
  received_date TEXT NOT NULL,
  received_units INTEGER NOT NULL CHECK (received_units >= 0),
  inspection_units INTEGER NOT NULL CHECK (inspection_units >= 0),
  accepted_units INTEGER NOT NULL CHECK (accepted_units >= 0),
  rejected_units INTEGER NOT NULL CHECK (rejected_units >= 0),
  source_ref TEXT NOT NULL,
  CHECK (received_units = inspection_units + accepted_units + rejected_units)
) STRICT;

CREATE TABLE expenses (
  expense_id TEXT PRIMARY KEY,
  budget_id TEXT REFERENCES budgets(budget_id),
  incurred_date TEXT NOT NULL,
  category_code TEXT NOT NULL,
  amount_cents INTEGER NOT NULL CHECK (amount_cents >= 0),
  status_code TEXT NOT NULL CHECK (status_code IN ('INCURRED','VOID')),
  source_ref TEXT NOT NULL
) STRICT;

CREATE TABLE obligations (
  obligation_id TEXT PRIMARY KEY,
  origin_type TEXT NOT NULL CHECK (origin_type IN ('PURCHASE_ORDER','EXPENSE')),
  origin_id TEXT NOT NULL,
  due_date TEXT,
  original_cents INTEGER NOT NULL CHECK (original_cents >= 0),
  currency TEXT NOT NULL CHECK (currency = 'MXN'),
  status_code TEXT NOT NULL CHECK (status_code IN ('OPEN','PARTIAL','SETTLED','VOID')),
  source_ref TEXT NOT NULL,
  UNIQUE (origin_type, origin_id)
) STRICT;

CREATE TABLE obligation_payments (
  payment_id TEXT PRIMARY KEY,
  obligation_id TEXT NOT NULL REFERENCES obligations(obligation_id),
  paid_date TEXT NOT NULL,
  amount_cents INTEGER NOT NULL CHECK (amount_cents >= 0),
  source_ref TEXT NOT NULL
) STRICT;

CREATE TABLE quality_events (
  quality_event_id TEXT PRIMARY KEY,
  sku_id TEXT NOT NULL REFERENCES sku_catalog(sku_id),
  receipt_id TEXT REFERENCES purchase_receipts(receipt_id),
  delivery_cohort_id TEXT REFERENCES sales_aggregates(delivery_cohort_id),
  event_date TEXT NOT NULL,
  event_type TEXT NOT NULL CHECK (event_type IN ('RETURN_REPORTED','RETURN_RECEIVED','INSPECTED','RESTOCKED','REJECTED','REFUNDED')),
  units INTEGER NOT NULL CHECK (units >= 0),
  reason_code TEXT NOT NULL,
  resolution_code TEXT,
  source_ref TEXT NOT NULL
) STRICT;

CREATE TABLE sales_readiness (
  sku_id TEXT NOT NULL REFERENCES sku_catalog(sku_id),
  effective_date TEXT NOT NULL,
  readiness_status TEXT NOT NULL CHECK (readiness_status IN ('READY','BLOCKED','REVIEW')),
  missing_info_code TEXT,
  source_ref TEXT NOT NULL,
  PRIMARY KEY (sku_id, effective_date)
) STRICT;

CREATE TABLE loans (
  loan_id TEXT PRIMARY KEY,
  sku_id TEXT NOT NULL REFERENCES sku_catalog(sku_id),
  quantity INTEGER NOT NULL CHECK (quantity >= 0),
  recipient_ref TEXT NOT NULL,
  borrowed_date TEXT NOT NULL,
  due_date TEXT,
  returned_date TEXT,
  condition_code TEXT NOT NULL CHECK (condition_code IN ('GOOD','DAMAGED','UNKNOWN')),
  status_code TEXT NOT NULL CHECK (status_code IN ('OPEN','PARTIAL','RETURNED','LOST')),
  source_ref TEXT NOT NULL,
  CHECK (due_date IS NULL OR due_date >= borrowed_date),
  CHECK (returned_date IS NULL OR returned_date >= borrowed_date)
) STRICT;

CREATE TABLE inventory_movements (
  movement_id TEXT PRIMARY KEY,
  sku_id TEXT NOT NULL REFERENCES sku_catalog(sku_id),
  event_date TEXT NOT NULL,
  movement_type TEXT NOT NULL CHECK (movement_type IN ('OPENING','RECEIPT_ACCEPTED','SALE_OUT','RETURN_RESTOCK','LOAN_OUT','LOAN_IN','ADJUSTMENT_IN','ADJUSTMENT_OUT')),
  units INTEGER NOT NULL CHECK (units >= 0),
  receipt_id TEXT REFERENCES purchase_receipts(receipt_id),
  quality_event_id TEXT REFERENCES quality_events(quality_event_id),
  loan_id TEXT REFERENCES loans(loan_id),
  sales_date TEXT,
  sales_channel_code TEXT,
  source_ref TEXT NOT NULL,
  FOREIGN KEY (sales_date, sku_id, sales_channel_code)
    REFERENCES sales_aggregates(sales_date, sku_id, channel_code)
) STRICT;

CREATE TABLE cash_balance_evidence (
  balance_evidence_id TEXT PRIMARY KEY,
  scenario_id TEXT NOT NULL,
  period_start TEXT NOT NULL,
  period_end TEXT NOT NULL,
  opening_balance_cents INTEGER,
  closing_balance_cents INTEGER,
  opening_observed_at TEXT,
  closing_observed_at TEXT,
  evidence_status TEXT NOT NULL CHECK (evidence_status IN ('OBSERVED','PARTIAL','MISSING','ESTIMATED','ERROR')),
  source_ref TEXT NOT NULL,
  UNIQUE (scenario_id, period_start, period_end),
  CHECK (period_start <= period_end)
) STRICT;

CREATE TABLE cash_events (
  event_id TEXT PRIMARY KEY,
  economic_event_id TEXT NOT NULL,
  supersedes_event_id TEXT UNIQUE REFERENCES cash_events(event_id),
  scenario_id TEXT NOT NULL,
  event_date TEXT,
  level TEXT NOT NULL CHECK (level IN ('RECONCILED','COMMITTED','EXPECTED','UNDATED','SCENARIO')),
  direction TEXT NOT NULL CHECK (direction IN ('INFLOW','OUTFLOW')),
  amount_cents INTEGER NOT NULL CHECK (amount_cents >= 0),
  currency TEXT NOT NULL CHECK (currency = 'MXN'),
  obligation_id TEXT REFERENCES obligations(obligation_id),
  payment_id TEXT REFERENCES obligation_payments(payment_id),
  source_ref TEXT NOT NULL,
  CHECK (supersedes_event_id IS NULL OR supersedes_event_id <> event_id)
) STRICT;

CREATE TABLE budget_allocations (
  budget_allocation_id TEXT PRIMARY KEY,
  budget_id TEXT NOT NULL REFERENCES budgets(budget_id),
  origin_type TEXT NOT NULL CHECK (origin_type IN ('PURCHASE_ORDER','EXPENSE')),
  origin_id TEXT NOT NULL,
  drop_code TEXT NOT NULL,
  channel_code TEXT NOT NULL,
  allocated_cents INTEGER NOT NULL CHECK (allocated_cents >= 0),
  source_ref TEXT NOT NULL,
  UNIQUE (budget_id, origin_type, origin_id, drop_code, channel_code)
) STRICT;
