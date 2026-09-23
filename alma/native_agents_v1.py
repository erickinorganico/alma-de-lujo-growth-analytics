"""Validate untrusted native Codex outputs against a frozen operating-v1 request.

Validation establishes local contract and parent-receipt consistency. It cannot
cryptographically attest that a model ran; the parent records actual dispatch.
"""
from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from typing import Any

from .operating_contracts import canonical_json
from .weekly_cycle import QUERY_REGISTRY, ROLE_MODELS, VERSION, resolve_pointer

MODEL_IDS = {
    "terra": frozenset({"gpt-5.6-terra"}),
    "luna": frozenset({"gpt-5.6-luna", "gpt-6-luna"}),
    "sol": frozenset({"gpt-5.6-sol", "gpt-6-sol"}),
    "astra": frozenset({"gpt-6-astra"}),
}
REVIEWER_ROLE = "evidence_reviewer"
PARENT_SCOPE = "schema,evidence,typed-values,registered-query,hashes,authority"
MAX_BYTES = 1024 * 1024
MAX_REQUEST_BYTES = 8 * MAX_BYTES


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_json(value)).hexdigest()


def _keys(value: Any, expected: set[str], label: str) -> None:
    if not isinstance(value, dict) or set(value) != expected:
        raise ValueError(f"invalid {label} fields")


def _text(value: Any, label: str, *, limit: int = 12000) -> None:
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise ValueError(f"invalid {label} text")


def _strings(value: Any, label: str, *, minimum: int = 0, maximum: int = 30) -> None:
    if not isinstance(value, list) or not minimum <= len(value) <= maximum:
        raise ValueError(f"invalid {label} list")
    for item in value:
        _text(item, label, limit=4000)


def _refs(evidence: Any, refs: Any, label: str) -> list[Any]:
    if not isinstance(refs, list) or not 1 <= len(refs) <= 20 or \
            any(not isinstance(ref, str) for ref in refs) or len(set(refs)) != len(refs):
        raise ValueError(f"invalid {label} references")
    return [resolve_pointer(evidence, ref) for ref in refs]


def validate_request(request: Any) -> bool:
    """Check canonical request identity, role routing and frozen evidence binding."""
    keys = {"version", "request_id", "cut_id", "run_id", "role", "expected_model_family",
            "execution_mode", "synthetic_business_data", "evidence_status", "blocked_sources",
            "current_cut_sha256", "manifest_sha256", "mart_bundle_sha256",
            "metric_contract_sha256", "evidence_hash", "evidence", "evidence_refs",
            "registered_queries", "response_contract", "write_scope"}
    _keys(request, keys, "request")
    role = request["role"]
    expected_family = "astra" if role == REVIEWER_ROLE else ROLE_MODELS.get(role)
    if expected_family is None or request["expected_model_family"] != expected_family:
        raise ValueError("role/model family mismatch")
    if request["version"] != VERSION or request["execution_mode"] != "native-codex-task-bridge":
        raise ValueError("invalid native request mode")
    if request["registered_queries"] != QUERY_REGISTRY:
        raise ValueError("unregistered query definition")
    if request["write_scope"] != [f"tasks/{role}.response.json",
                                  f"tasks/{role}.query-trace.json"]:
        raise ValueError("request write authority changed")
    if request["response_contract"] != "contracts/weekly-cycle-v1.schema.json#/$defs/response":
        raise ValueError("response contract changed")
    if request["evidence_status"] not in {"READY_FOR_ANALYSIS", "REVIEW", "BLOCKED_EVIDENCE"} or \
            not isinstance(request["blocked_sources"], list):
        raise ValueError("invalid request evidence gate")
    evidence = request["evidence"]
    if not isinstance(evidence, dict) or not isinstance(evidence.get("metric_rows"), list):
        raise ValueError("request evidence lacks local mart")
    if role == REVIEWER_ROLE and (not isinstance(evidence.get("analyses"), dict) or
                                  not isinstance(evidence.get("accepted_hashes"), dict)):
        raise ValueError("reviewer request lacks accepted analyses")
    cut = evidence.get("cut")
    if not isinstance(cut, dict) or any(cut.get(key) != request[key] for key in
            ("cut_id", "manifest_sha256", "mart_bundle_sha256", "metric_contract_sha256",
             "synthetic_business_data")):
        raise ValueError("request cut fields differ from evidence")
    if (cut.get("synthetic_business_data") is not
            (cut.get("input_class") == "SYNTHETIC_EXAMPLE")):
        raise ValueError("synthetic provenance differs from input class")
    if (digest(evidence) != request["evidence_hash"] or
        digest({key: value for key, value in request.items() if key != "request_id"}) !=
            request["request_id"]):
        raise ValueError("request or evidence digest changed")
    if not isinstance(request["evidence_refs"], list) or not request["evidence_refs"]:
        raise ValueError("missing request evidence references")
    _refs(evidence, request["evidence_refs"], "request")
    if len(canonical_json(request)) > MAX_REQUEST_BYTES:
        raise ValueError("oversized native request")
    return True


def make_reviewer_request(cycle: dict[str, Any], accepted: dict[str, Any]) -> dict[str, Any]:
    """Freeze all accepted analyst artifacts into one distinct Astra request."""
    state, report = cycle["state"], cycle["report"]
    roles = set(state["expected_roles"])
    if set(accepted) != roles or not roles:
        raise ValueError("review requires every expected analyst")
    for role, item in accepted.items():
        if item["entry"] != state["accepted_roles"][role]:
            raise ValueError("accepted analysis differs from cycle checkpoint")
    evidence = {"cut": {key: report[key] for key in ("cut_id", "cutoff_at", "timezone",
                "input_class", "synthetic_business_data", "manifest_sha256",
                "mart_bundle_sha256", "metric_contract_sha256")},
        "source_sha256": report["source_sha256"], "coverage": report["coverage"],
        "quality": report["quality"], "reconciliation": report["reconciliation"],
        "metric_rows": report["metric_rows"], "metric_definitions": report["metric_definitions"],
        "analyses": {role: accepted[role]["response"] for role in sorted(roles)},
        "analyst_evidence": {role: accepted[role]["request"]["evidence"]
                             for role in sorted(roles)},
        "accepted_hashes": {role: accepted[role]["entry"] for role in sorted(roles)}}
    refs = ["/cut/cut_id", "/quality/workspace"]
    if evidence["metric_rows"]:
        refs.append("/metric_rows/0/value")
    for role in sorted(roles):
        refs.append(f"/accepted_hashes/{role}/response_sha256")
    request = {"version": VERSION, "cut_id": state["cut_id"], "run_id": state["run_id"],
        "role": REVIEWER_ROLE, "expected_model_family": "astra",
        "execution_mode": "native-codex-task-bridge",
        "synthetic_business_data": report["synthetic_business_data"],
        "evidence_status": "REVIEW", "blocked_sources": [],
        "current_cut_sha256": state["current_cut_sha256"],
        "manifest_sha256": state["manifest_sha256"],
        "mart_bundle_sha256": state["mart_bundle_sha256"],
        "metric_contract_sha256": report["metric_contract_sha256"],
        "evidence_hash": digest(evidence), "evidence": evidence,
        "evidence_refs": refs, "registered_queries": QUERY_REGISTRY,
        "response_contract": "contracts/weekly-cycle-v1.schema.json#/$defs/response",
        "write_scope": ["tasks/evidence_reviewer.response.json",
                        "tasks/evidence_reviewer.query-trace.json"]}
    request["request_id"] = digest(request)
    validate_request(request)
    return request


def build_terminal_packet(cycle: dict[str, Any], accepted: dict[str, Any],
                          review: dict[str, Any]) -> dict[str, Any]:
    """Project validated native statements; never compute or invent business facts."""
    state, report = cycle["state"], cycle["report"]
    if set(accepted) != set(state["expected_roles"]):
        raise ValueError("terminal packet lacks expected analysts")
    reviewer = review["response"]
    if reviewer["verdict"] == "BLOCKED" or any(
            item["response"]["verdict"] == "BLOCKED" for item in accepted.values()):
        status = "BLOCKED"
    elif reviewer["verdict"] == "READY_FOR_OWNER":
        status = "READY_FOR_OWNER"
    else:
        status = "REVIEW"
    def collected(field: str) -> list[dict[str, Any]]:
        return [{"role": role, "item": item} for role, result in sorted(accepted.items())
                for item in result["response"][field]]
    packet = {"version": VERSION, "cut_id": state["cut_id"], "run_id": state["run_id"],
        "status": status, "synthetic_business_data": report["synthetic_business_data"],
        "current_cut_sha256": state["current_cut_sha256"],
        "facts": collected("facts"), "unknowns": collected("unknowns"),
        "hypotheses": collected("hypotheses"),
        "recommendations": collected("recommendations"),
        "challenges": collected("challenges") +
            [{"role": REVIEWER_ROLE, "item": item} for item in reviewer["challenges"]],
        "analyses": [{"role": role, "summary": item["response"]["summary"],
                      "verdict": item["response"]["verdict"], **item["entry"]}
                     for role, item in sorted(accepted.items())],
        "review": {"summary": reviewer["summary"], "verdict": reviewer["verdict"],
                   "facts": reviewer["facts"], "unknowns": reviewer["unknowns"],
                   "hypotheses": reviewer["hypotheses"],
                   "recommendations": reviewer["recommendations"],
                   "challenges": reviewer["challenges"], **review["entry"]},
        "provenance": {"manifest_sha256": state["manifest_sha256"],
                       "mart_bundle_sha256": state["mart_bundle_sha256"],
                       "metric_contract_sha256": report["metric_contract_sha256"],
                       "source_sha256": report["source_sha256"],
                       "accepted_hashes": {role: item["entry"] for role, item in sorted(accepted.items())},
                       "review_hashes": review["entry"]},
        "external_execution": "PROHIBITED"}
    return packet


def validate_terminal_packet(cycle: dict[str, Any], packet: Any) -> bool:
    if not isinstance(packet, dict) or packet.get("external_execution") != "PROHIBITED":
        raise ValueError("terminal packet authority invalid")
    from .weekly_cycle import _verified_cycle_context

    context = _verified_cycle_context(cycle["cycle_dir"])
    if context["state"]["status"] not in {"READY_FOR_OWNER", "REVIEW", "BLOCKED"}:
        raise ValueError("cycle is not terminal")
    expected = build_terminal_packet(context, context["accepted"], context["review"])
    if packet != expected or digest(packet) != context["state"].get("packet_sha256"):
        raise ValueError("terminal packet differs from accepted evidence")
    return True


def validate_response(request: dict[str, Any], response: Any) -> bool:
    """Validate exact typed observations; narrative meaning remains reviewer work."""
    validate_request(request)
    keys = {"version", "request_id", "role", "cut_id", "run_id", "evidence_hash",
            "current_cut_sha256", "manifest_sha256", "mart_bundle_sha256",
            "metric_contract_sha256", "summary", "facts", "unknowns", "hypotheses",
            "recommendations", "challenges", "verdict"}
    _keys(response, keys, "response")
    for key in ("version", "request_id", "role", "cut_id", "run_id", "evidence_hash",
                "current_cut_sha256", "manifest_sha256", "mart_bundle_sha256",
                "metric_contract_sha256"):
        if response[key] != request[key]:
            raise ValueError("stale response identity")
    if response["verdict"] not in {"READY_FOR_OWNER", "REVIEW", "BLOCKED"}:
        raise ValueError("invalid advisory verdict")
    _text(response["summary"], "summary")
    facts = response["facts"]
    if not isinstance(facts, list) or not 2 <= len(facts) <= 30:
        raise ValueError("two to thirty evidenced facts required")
    ids: set[str] = set()
    for fact in facts:
        _keys(fact, {"id", "statement", "kind", "evidence_refs", "value"}, "fact")
        _text(fact["id"], "fact ID", limit=80)
        _text(fact["statement"], "fact statement", limit=4000)
        if fact["id"] in ids:
            raise ValueError("duplicate fact ID")
        ids.add(fact["id"])
        if fact["kind"] not in {"observation", "inference"}:
            raise ValueError("invalid fact kind")
        values = _refs(request["evidence"], fact["evidence_refs"], "fact")
        if fact["kind"] == "observation":
            if not any(type(value) is type(fact["value"]) and value == fact["value"]
                       for value in values):
                raise ValueError("observation value differs from frozen evidence")
        elif fact["value"] is not None:
            raise ValueError("inference cannot claim a measured value")
    _strings(response["unknowns"], "unknown", minimum=1)
    _strings(response["hypotheses"], "hypothesis")
    _strings(response["challenges"], "challenge",
             minimum=1 if request["role"] == REVIEWER_ROLE else 0)
    recommendations = response["recommendations"]
    if not isinstance(recommendations, list) or len(recommendations) > 12:
        raise ValueError("invalid recommendations")
    recommendation_ids: set[str] = set()
    for item in recommendations:
        _keys(item, {"id", "action", "evidence_refs", "primary_metric", "guardrail",
                     "population", "window", "closure_rule", "approval_required", "execution"},
              "recommendation")
        for key in ("id", "action", "primary_metric", "guardrail", "population",
                    "window", "closure_rule"):
            _text(item[key], key, limit=4000)
        if item["id"] in recommendation_ids:
            raise ValueError("duplicate recommendation ID")
        recommendation_ids.add(item["id"])
        _refs(request["evidence"], item["evidence_refs"], "recommendation")
        if item["approval_required"] is not True or item["execution"] != "PROHIBITED":
            raise ValueError("external business execution prohibited")
    if len(canonical_json(response)) > MAX_BYTES:
        raise ValueError("oversized native response")
    return True


def validate_query_trace(request: dict[str, Any], trace: Any) -> bool:
    """Require a registered, read-only metric lookup with complete exact row refs."""
    validate_request(request)
    _keys(trace, {"version", "request_id", "role", "queries", "unavailable_reason"},
          "query trace")
    if any(trace[key] != request[key] for key in ("version", "request_id", "role")):
        raise ValueError("query trace/request mismatch")
    queries = trace["queries"]
    rows = request["evidence"]["metric_rows"]
    if not isinstance(queries, list) or len(queries) > 12:
        raise ValueError("invalid query list")
    if rows:
        if not queries or trace["unavailable_reason"] is not None:
            raise ValueError("queryable local mart requires a registered query")
    elif queries or not isinstance(trace["unavailable_reason"], str) or \
            not trace["unavailable_reason"].strip():
        raise ValueError("unavailable query requires absent local rows")
    for query in queries:
        _keys(query, {"query_id", "question", "parameters", "result_refs", "row_count"},
              "registered query")
        if query["query_id"] != "metric_rows.by_reconciliation_id" or \
                query["query_id"] not in request["registered_queries"]:
            raise ValueError("unregistered query")
        _text(query["question"], "query question", limit=1000)
        _keys(query["parameters"], {"reconciliation_id"}, "query parameters")
        token = query["parameters"]["reconciliation_id"]
        _text(token, "reconciliation ID", limit=500)
        if any(not isinstance(row, dict) for row in rows):
            raise ValueError("invalid frozen metric rows")
        expected = [f"/metric_rows/{index}" for index, row in enumerate(rows)
                    if row.get("reconciliation_id") == token]
        if not expected or len(expected) > 100 or query["result_refs"] != expected or \
                type(query["row_count"]) is not int or query["row_count"] != len(expected):
            raise ValueError("query results differ from frozen metric rows")
        for ref in expected:
            resolve_pointer(request["evidence"], ref)
    if len(canonical_json(trace)) > MAX_BYTES:
        raise ValueError("oversized query trace")
    return True


def execute_registered_query(request: dict[str, Any], reconciliation_id: str) -> dict[str, Any]:
    """Read one registered frozen-mart selection for a native analyst or reviewer."""
    validate_request(request)
    _text(reconciliation_id, "reconciliation ID", limit=500)
    rows = request["evidence"]["metric_rows"]
    matches = [(index, row) for index, row in enumerate(rows)
               if isinstance(row, dict) and row.get("reconciliation_id") == reconciliation_id]
    if not matches or len(matches) > 100:
        raise ValueError("registered query has no bounded result")
    return {"query_id": "metric_rows.by_reconciliation_id",
            "parameters": {"reconciliation_id": reconciliation_id},
            "result_refs": [f"/metric_rows/{index}" for index, _ in matches],
            "row_count": len(matches), "rows": [row for _, row in matches]}


def _utc(value: Any) -> datetime:
    if not isinstance(value, str):
        raise ValueError("UTC dispatch timestamp required")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("UTC dispatch timestamp required") from exc
    if parsed.tzinfo is None or parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        raise ValueError("UTC dispatch timestamp required")
    return parsed


def validate_dispatch(request: dict[str, Any], response: dict[str, Any],
                      trace: dict[str, Any], receipt: Any) -> bool:
    """Check parent-attested native metadata and exact response/trace digests."""
    validate_response(request, response)
    validate_query_trace(request, trace)
    _keys(receipt, {"version", "request_id", "role", "provider", "model", "agent_id",
                    "effort", "started_at_utc", "completed_at_utc", "response_sha256",
                    "query_trace_sha256", "recorded_by", "mode", "parent_validation_scope"},
          "dispatch receipt")
    if any(receipt[key] != request[key] for key in ("version", "request_id", "role")):
        raise ValueError("dispatch/request mismatch")
    family = request["expected_model_family"]
    if receipt["model"] not in MODEL_IDS[family] or receipt["provider"] != "native-codex" or \
            receipt["mode"] != "live" or receipt["recorded_by"] != "parent-runtime":
        raise ValueError("native role/model dispatch mismatch")
    if not isinstance(receipt["agent_id"], str) or not re.fullmatch(
            r"/root/[a-z0-9_/-]{1,120}", receipt["agent_id"]):
        raise ValueError("native task identity required")
    if receipt["effort"] not in {"low", "medium", "high", "xhigh", "max", "ultra"}:
        raise ValueError("invalid native effort")
    if _utc(receipt["completed_at_utc"]) < _utc(receipt["started_at_utc"]):
        raise ValueError("dispatch completed before start")
    if receipt["response_sha256"] != digest(response) or \
            receipt["query_trace_sha256"] != digest(trace):
        raise ValueError("response or query-trace hash mismatch")
    if receipt["parent_validation_scope"] != PARENT_SCOPE:
        raise ValueError("parent validation scope missing")
    return True


__all__ = ["MODEL_IDS", "QUERY_REGISTRY", "PARENT_SCOPE", "digest", "validate_request",
           "validate_response", "validate_query_trace", "validate_dispatch", "execute_registered_query",
           "make_reviewer_request", "build_terminal_packet", "validate_terminal_packet"]
