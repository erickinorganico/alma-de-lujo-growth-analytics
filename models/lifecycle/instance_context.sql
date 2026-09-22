-- Canonical v0.2 lifecycle instance context.
-- One row per materialized instance. Fields that are not columns on
-- lifecycle_instances are reconstructed from immutable events and receipts.
SELECT
  i.process_id,
  i.process_contract_id,
  i.instance_id AS process_instance_id,
  i.definition_version,
  i.owner_role,
  i.scenario_id,
  i.run_id,
  i.current_state AS state,
  i.blocked_reason,
  i.last_event_hash,
  i.updated_at_utc,
  i.synthetic,
  COALESCE((
    SELECT json_group_array(source_ref)
    FROM (
      SELECT DISTINCT refs.value AS source_ref
      FROM lifecycle_events AS e, json_each(e.source_refs_json) AS refs
      WHERE e.process_id = i.process_id AND e.instance_id = i.instance_id
      ORDER BY source_ref
    )
  ), '[]') AS input_refs_json,
  json_object(
    'event_hashes', json(COALESCE((
      SELECT json_group_array(event_hash)
      FROM (
        SELECT e.event_hash
        FROM lifecycle_events AS e
        WHERE e.process_id = i.process_id AND e.instance_id = i.instance_id
        ORDER BY e.sequence
      )
    ), '[]')),
    'receipt_ids', json(COALESCE((
      SELECT json_group_array(receipt_id)
      FROM (
        SELECT r.receipt_id
        FROM lifecycle_receipts AS r
        WHERE r.process_id = i.process_id AND r.instance_id = i.instance_id
        ORDER BY r.recorded_at_utc, r.receipt_id
      )
    ), '[]'))
  ) AS output_refs_json,
  COALESCE((
    SELECT json_group_array(json(gate_result))
    FROM (
      SELECT json_object(
        'gate', json_extract(r.receipt_json, '$.details.gate'),
        'status', r.status,
        'exception_code', r.exception_code,
        'recorded_at_utc', r.recorded_at_utc,
        'receipt_id', r.receipt_id
      ) AS gate_result
      FROM lifecycle_receipts AS r
      WHERE r.process_id = i.process_id
        AND r.instance_id = i.instance_id
        AND json_extract(r.receipt_json, '$.details.gate') IS NOT NULL
      ORDER BY r.recorded_at_utc, r.receipt_id
    )
  ), '[]') AS gate_results_json,
  COALESCE((
    SELECT json_group_array(exception_code)
    FROM (
      SELECT DISTINCT r.exception_code
      FROM lifecycle_receipts AS r
      WHERE r.process_id = i.process_id
        AND r.instance_id = i.instance_id
        AND r.exception_code IS NOT NULL
      ORDER BY r.exception_code
    )
  ), '[]') AS exception_codes_json,
  (
    SELECT r.idempotency_key
    FROM lifecycle_receipts AS r
    WHERE r.process_id = i.process_id AND r.instance_id = i.instance_id
    ORDER BY r.recorded_at_utc DESC, r.receipt_id DESC
    LIMIT 1
  ) AS last_idempotency_key,
  COALESCE((
    SELECT json_group_array(json(event_record))
    FROM (
      SELECT json_object(
        'sequence', e.sequence,
        'event_id', e.event_id,
        'event_type', e.event_type,
        'from_state', e.from_state,
        'to_state', e.to_state,
        'occurred_at_utc', e.occurred_at_utc,
        'recorded_at_utc', e.recorded_at_utc,
        'payload', json(e.payload_json),
        'payload_hash', e.payload_hash,
        'source_refs', json(e.source_refs_json),
        'idempotency_key', e.idempotency_key,
        'previous_hash', e.previous_hash,
        'event_hash', e.event_hash
      ) AS event_record
      FROM lifecycle_events AS e
      WHERE e.process_id = i.process_id AND e.instance_id = i.instance_id
      ORDER BY e.sequence
    )
  ), '[]') AS events_json,
  COALESCE((
    SELECT json_group_array(json(r.receipt_json))
    FROM lifecycle_receipts AS r
    WHERE r.process_id = i.process_id AND r.instance_id = i.instance_id
    ORDER BY r.recorded_at_utc, r.receipt_id
  ), '[]') AS receipts_json
FROM lifecycle_instances AS i
ORDER BY i.process_id, i.instance_id;
