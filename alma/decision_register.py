"""Private, append-only and tamper-evident owner decision register."""
from __future__ import annotations

import csv
import hashlib
import json
import os
import re
import tempfile
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from .native_agents_v1 import digest, validate_terminal_packet
from .operating_contracts import canonical_json
from .weekly_cycle import read_terminal_packet, verify_cycle

VERSION = "decision-register-v1"
GENESIS = "GENESIS"
MAX_EVENTS = 10_000
MAX_TEXT = 4_000
OWNER_RE = re.compile(r"^[a-z][a-z0-9_]{2,63}$")
CODE_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_.:-]{0,127}$")
HASH_RE = re.compile(r"^[0-9a-f]{64}$")
FORMULA_PREFIXES = ("=", "+", "-", "@")
STATUSES = {"OPEN", "IN_PROGRESS", "REVIEW", "STALE", "CLOSED", "REJECTED"}
TRANSITIONS = {
    "OPEN": {"IN_PROGRESS", "REVIEW", "REJECTED"},
    "IN_PROGRESS": {"REVIEW", "REJECTED"},
    "REVIEW": {"IN_PROGRESS", "REJECTED"},
    "STALE": {"IN_PROGRESS", "REVIEW", "REJECTED"},
    "CLOSED": set(),
    "REJECTED": set(),
}
PROPOSAL_COLUMNS = ("decision_id", "proposed_status", "owner", "note_code", "new_due_date")
PROJECTION_COLUMNS = ("decision_id", "recommendation_id", "owner", "due_date", "status",
                      "cut_id", "source_hash", "packet_hash", "event_count", "terminal_hash")


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _json(path: Path) -> Any:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 32 * 1024 * 1024:
        raise ValueError("missing, linked or oversized register artifact")
    raw = path.read_bytes()
    value = json.loads(raw)
    if raw != canonical_json(value):
        raise ValueError("noncanonical register artifact")
    return value


def _atomic(path: Path, value: Any) -> None:
    if path.is_symlink():
        raise ValueError("linked register artifact")
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(handle, "wb") as stream:
            stream.write(canonical_json(value))
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def _register_path(value: str | Path, *, existing: bool = True) -> Path:
    raw = Path(value)
    if ".." in raw.parts:
        raise ValueError("path traversal")
    for part in (raw, *raw.parents):
        if part.exists() and (part.is_symlink() or
                              (hasattr(part, "is_junction") and part.is_junction())):
            raise ValueError("linked register path")
    path = raw.resolve(strict=False)
    parts = tuple(piece.lower() for piece in path.parts)
    if ".local" not in parts or "decision-register" not in parts:
        raise ValueError("register must remain under .local/decision-register")
    if existing and not path.is_dir():
        raise ValueError("register does not exist")
    return path


def _owner(value: str, allowed: set[str] | None = None) -> str:
    if not isinstance(value, str) or not OWNER_RE.fullmatch(value) or not value.endswith(
            ("_owner", "_lead", "_reviewer", "_analyst")):
        raise ValueError("owner must be a non-PII role token")
    if allowed is not None and value not in allowed:
        raise ValueError("owner role is not allowlisted")
    return value


def _code(value: Any, label: str) -> str:
    if not isinstance(value, str) or not CODE_RE.fullmatch(value):
        raise ValueError(f"invalid {label}")
    return value


def _date(value: Any, label: str = "date") -> str:
    if not isinstance(value, str):
        raise ValueError(f"invalid {label}")
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"invalid {label}") from exc
    if parsed.isoformat() != value:
        raise ValueError(f"invalid {label}")
    return value


def _no_floats(value: Any) -> None:
    if isinstance(value, float):
        raise ValueError("binary floats are prohibited")
    if isinstance(value, dict):
        for item in value.values():
            _no_floats(item)
    elif isinstance(value, list):
        for item in value:
            _no_floats(item)


def _closure_check(value: Any) -> dict[str, Any]:
    _no_floats(value)
    if not isinstance(value, dict) or value.get("requires_later_cut") is not True:
        raise ValueError("closure check must require a later cut")
    kind = value.get("kind")
    if kind == "human_judgment":
        if set(value) != {"kind", "criterion", "requires_later_cut"}:
            raise ValueError("invalid human judgment closure check")
        criterion = value.get("criterion")
        if not isinstance(criterion, str) or not criterion.strip() or len(criterion) > MAX_TEXT:
            raise ValueError("invalid human judgment criterion")
        return dict(value)
    required = {"kind", "pointer", "operator", "expected", "value_type", "unit",
                "requires_later_cut"}
    if kind != "machine" or set(value) != required:
        raise ValueError("invalid machine closure check")
    pointer = value["pointer"]
    if not isinstance(pointer, str) or not pointer.startswith("/") or len(pointer) > 500:
        raise ValueError("closure pointer must be a local JSON Pointer")
    value_type = value["value_type"]
    operator = value["operator"]
    allowed = {
        "existence": {"exists", "not_exists"},
        "string": {"eq", "ne"}, "status": {"eq", "ne"},
        "integer": {"eq", "ne", "gt", "gte", "lt", "lte"},
        "decimal": {"eq", "ne", "gt", "gte", "lt", "lte"},
        "boolean": {"eq", "ne"},
    }
    if value_type not in allowed or operator not in allowed[value_type]:
        raise ValueError("invalid typed closure operator")
    if not isinstance(value["unit"], str) or not value["unit"] or len(value["unit"]) > 64:
        raise ValueError("invalid closure unit")
    expected = value["expected"]
    if value_type == "existence":
        if expected is not None:
            raise ValueError("existence checks use null expected value")
    elif value_type == "integer":
        if type(expected) is not int:
            raise ValueError("integer closure expected value required")
    elif value_type == "decimal":
        if not isinstance(expected, str):
            raise ValueError("decimal expected value must be text")
        try:
            Decimal(expected)
        except InvalidOperation as exc:
            raise ValueError("invalid decimal expected value") from exc
    elif value_type == "boolean":
        if type(expected) is not bool:
            raise ValueError("boolean expected value required")
    elif not isinstance(expected, str) or len(expected) > MAX_TEXT:
        raise ValueError("string expected value required")
    return dict(value)


def _config(register: Path) -> dict[str, Any]:
    config = _json(register / "config.json")
    if (not isinstance(config, dict) or config.get("version") != VERSION or
            not isinstance(config.get("owner_roles"), list)):
        raise ValueError("invalid register configuration")
    roles = [_owner(item) for item in config["owner_roles"]]
    if len(set(roles)) != len(roles) or not roles:
        raise ValueError("invalid owner role allowlist")
    return config


def _anchor(register_id: str, events: list[dict[str, Any]], origins: dict[str, str]) -> dict[str, Any]:
    return {"version": VERSION, "register_id": register_id,
            "terminal_hash": events[-1]["hash"] if events else GENESIS,
            "event_count": len(events), "origins_hash": digest(origins)}


def create_register(path: str | Path, register_id: str,
                    owner_roles: list[str] | tuple[str, ...]) -> str:
    register = _register_path(path, existing=False)
    register_id = _code(register_id, "register ID")
    roles = sorted({_owner(role) for role in owner_roles})
    if not roles or len(roles) != len(owner_roles):
        raise ValueError("owner roles must be nonempty and unique")
    if register.exists() and any(register.iterdir()):
        raise ValueError("register already exists")
    register.mkdir(parents=True, exist_ok=True)
    _atomic(register / "config.json", {"version": VERSION, "register_id": register_id,
        "owner_roles": roles, "external_execution": "PROHIBITED"})
    _atomic(register / "events.json", [])
    _atomic(register / "origins.json", {})
    _atomic(register / "anchor.json", _anchor(register_id, [], {}))
    return str(register)


def _event(body: dict[str, Any], sequence: int) -> dict[str, Any]:
    event = dict(body)
    event["event_id"] = "evt-" + digest({"sequence": sequence, **event})[:24]
    event["hash"] = digest(event)
    return event


def _append(register: Path, body: dict[str, Any], origin: str | None = None) -> dict[str, Any]:
    verified = verify_register(register)
    events = list(verified["events"])
    if len(events) >= MAX_EVENTS:
        raise ValueError("register event cap reached")
    sequence = len(events) + 1
    body = {"version": VERSION, **body, "previous_hash": verified["anchor"]["terminal_hash"]}
    event = _event(body, sequence)
    if any(item["event_id"] == event["event_id"] for item in events):
        raise ValueError("duplicate event ID")
    origins = _json(register / "origins.json")
    if origin is not None:
        if event["decision_id"] in origins:
            raise ValueError("duplicate decision ID")
        origins[event["decision_id"]] = origin
    events.append(event)
    _atomic(register / "events.json", events)
    _atomic(register / "origins.json", origins)
    anchor = _anchor(verified["register_id"], events, origins)
    _atomic(register / "anchor.json", anchor)
    return {"decision_id": event["decision_id"], "event_id": event["event_id"],
            "status": event["status"], "anchor": anchor}


def register_decision(register: str | Path, cycle_dir: str | Path, recommendation_id: str,
                      owner_role: str, due_date: str, owner_choice: str,
                      closure_check: dict[str, Any]) -> dict[str, Any]:
    folder = _register_path(register)
    config = _config(folder)
    owner_role = _owner(owner_role, set(config["owner_roles"]))
    due_date = _date(due_date, "due date")
    if owner_choice not in {"ACCEPT", "DEFER", "REJECT"}:
        raise ValueError("invalid owner choice")
    recommendation_id = _code(recommendation_id, "recommendation ID")
    checked = _closure_check(closure_check)
    cycle_path = Path(cycle_dir).resolve(strict=True)
    cycle = verify_cycle(cycle_path)
    if cycle["status"] != "READY_FOR_OWNER":
        raise ValueError("packet is not READY_FOR_OWNER")
    packet_path = cycle_path / "decision-packet.json"
    packet_raw = packet_path.read_bytes()
    packet = read_terminal_packet(cycle_path)
    validate_terminal_packet({"cycle_dir": cycle_path}, packet)
    candidates = [item for item in packet["recommendations"]
                  if item.get("item", {}).get("id") == recommendation_id]
    if len(candidates) != 1:
        raise ValueError("recommendation is missing or ambiguous")
    recommendation = candidates[0]["item"]
    if (recommendation.get("approval_required") is not True or
            recommendation.get("execution") != "PROHIBITED"):
        raise ValueError("recommendation authority invalid")
    current_raw = (cycle_path / "current-cut.json").read_bytes()
    current = json.loads(current_raw)
    packet_hash = _sha(packet_raw)
    if packet_hash != cycle.get("packet_sha256"):
        raise ValueError("packet hash mismatch")
    if _sha(current_raw) != packet["current_cut_sha256"]:
        raise ValueError("current cut hash mismatch")
    source_hash = digest(packet["provenance"]["source_sha256"])
    decision_id = "dec-" + digest({"packet_hash": packet_hash,
                                    "recommendation_id": recommendation_id})[:24]
    status = {"ACCEPT": "OPEN", "DEFER": "REVIEW", "REJECT": "REJECTED"}[owner_choice]
    body = {"decision_id": decision_id, "event_type": "REGISTER",
        "recorded_at_utc": _utc_now(), "cut_id": packet["cut_id"],
        "cutoff": current["cutoff_at"], "source_hash": source_hash,
        "packet_hash": packet_hash, "recommendation_id": recommendation_id,
        "owner": owner_role, "due_date": due_date, "status": status,
        "closure_rule": recommendation["closure_rule"], "closure_check": checked,
        "closure_evidence": None, "owner_choice": owner_choice,
        "external_execution": "PROHIBITED", "note_code": None}
    return _append(folder, body, str(cycle_path))


def append_status(register: str | Path, decision_id: str, status: str, owner_role: str,
                  note_code: str | None = None) -> dict[str, Any]:
    folder = _register_path(register)
    verified = verify_register(folder)
    owner_role = _owner(owner_role, set(verified["owner_roles"]))
    decision_id = _code(decision_id, "decision ID")
    current = next((row for row in verified["decisions"] if row["decision_id"] == decision_id), None)
    if current is None:
        raise ValueError("unknown decision")
    if status not in TRANSITIONS[current["status"]]:
        raise ValueError("invalid status transition")
    if note_code is not None:
        note_code = _code(note_code, "note code")
    body = {key: current[key] for key in ("decision_id", "cut_id", "cutoff", "source_hash",
        "packet_hash", "recommendation_id", "owner", "due_date", "closure_rule", "closure_check")}
    body.update({"event_type": "STATUS", "recorded_at_utc": _utc_now(),
        "owner": owner_role, "status": status, "closure_evidence": None,
        "owner_choice": current["owner_choice"], "external_execution": "PROHIBITED",
        "note_code": note_code})
    return _append(folder, body)


def _project(register_id: str, owner_roles: list[str], events: list[dict[str, Any]],
             anchor: dict[str, Any]) -> dict[str, Any]:
    decisions: dict[str, dict[str, Any]] = {}
    counts: dict[str, int] = {}
    for event in events:
        decision_id = event["decision_id"]
        counts[decision_id] = counts.get(decision_id, 0) + 1
        if event["event_type"] == "REGISTER":
            decisions[decision_id] = {key: event[key] for key in (
                "decision_id", "cut_id", "cutoff", "source_hash", "packet_hash",
                "recommendation_id", "owner", "due_date", "status", "closure_rule",
                "closure_check", "owner_choice")}
            decisions[decision_id]["closure_evidence"] = None
        else:
            current = decisions[decision_id]
            current.update({"status": event["status"], "owner": event["owner"],
                            "due_date": event["due_date"],
                            "closure_evidence": event["closure_evidence"]})
    for decision_id, row in decisions.items():
        row["event_count"] = counts[decision_id]
        row["terminal_hash"] = next(item["hash"] for item in reversed(events)
                                    if item["decision_id"] == decision_id)
    return {"version": VERSION, "register_id": register_id, "owner_roles": owner_roles,
            "events": events, "decisions": [decisions[key] for key in sorted(decisions)],
            "anchor": anchor}


def verify_register(register: str | Path, expected_anchor: dict[str, Any] | str | Path | None = None
                    ) -> dict[str, Any]:
    folder = _register_path(register)
    config = _config(folder)
    events = _json(folder / "events.json")
    origins = _json(folder / "origins.json")
    if not isinstance(events, list) or len(events) > MAX_EVENTS or not isinstance(origins, dict):
        raise ValueError("invalid register collections")
    previous = GENESIS
    decision_states: dict[str, str] = {}
    event_ids: set[str] = set()
    decision_ids: set[str] = set()
    allowed = set(config["owner_roles"])
    immutable: dict[str, dict[str, Any]] = {}
    required = {"version", "event_id", "decision_id", "event_type", "recorded_at_utc",
        "cut_id", "cutoff", "source_hash", "packet_hash", "recommendation_id", "owner",
        "due_date", "status", "closure_rule", "closure_check", "closure_evidence",
        "previous_hash", "hash", "owner_choice", "external_execution", "note_code"}
    for sequence, event in enumerate(events, 1):
        if not isinstance(event, dict) or set(event) != required or event["version"] != VERSION:
            raise ValueError("invalid event shape")
        _no_floats(event)
        if event["previous_hash"] != previous or event["event_id"] in event_ids:
            raise ValueError("event chain or identity invalid")
        unhashed = {key: value for key, value in event.items() if key != "hash"}
        expected_id = "evt-" + digest({"sequence": sequence,
            **{key: value for key, value in unhashed.items() if key != "event_id"}})[:24]
        if event["event_id"] != expected_id or event["hash"] != digest(unhashed):
            raise ValueError("event content hash invalid")
        if event["external_execution"] != "PROHIBITED":
            raise ValueError("external execution is prohibited")
        _owner(event["owner"], allowed)
        _date(event["due_date"], "due date")
        _closure_check(event["closure_check"])
        for name in ("source_hash", "packet_hash"):
            if not isinstance(event[name], str) or not HASH_RE.fullmatch(event[name]):
                raise ValueError("invalid evidence hash")
        decision_id = _code(event["decision_id"], "decision ID")
        if event["event_type"] == "REGISTER":
            if decision_id in decision_ids or event["status"] not in {"OPEN", "REVIEW", "REJECTED"}:
                raise ValueError("duplicate decision or invalid initial status")
            decision_ids.add(decision_id)
            immutable[decision_id] = {key: event[key] for key in ("cut_id", "cutoff", "source_hash",
                "packet_hash", "recommendation_id", "closure_rule", "closure_check", "owner_choice")}
        else:
            if decision_id not in decision_states:
                raise ValueError("event precedes decision")
            for key, value in immutable[decision_id].items():
                if event[key] != value:
                    raise ValueError("immutable decision evidence changed")
            if event["status"] not in TRANSITIONS[decision_states[decision_id]]:
                raise ValueError("invalid event transition")
        if event["status"] not in STATUSES:
            raise ValueError("invalid decision status")
        decision_states[decision_id] = event["status"]
        event_ids.add(event["event_id"])
        previous = event["hash"]
    if set(origins) != decision_ids or any(not isinstance(value, str) for value in origins.values()):
        raise ValueError("decision origins do not match history")
    anchor = _json(folder / "anchor.json")
    calculated = _anchor(config["register_id"], events, origins)
    if anchor != calculated:
        raise ValueError("register anchor mismatch")
    if expected_anchor is not None:
        supplied = _json(Path(expected_anchor)) if isinstance(expected_anchor, (str, Path)) else expected_anchor
        if supplied != anchor:
            raise ValueError("stale or forged expected anchor")
    return _project(config["register_id"], config["owner_roles"], events, anchor)


def export_csv(register: str | Path, destination: str | Path) -> dict[str, Any]:
    verified = verify_register(register)
    path = Path(destination)
    if path.is_symlink():
        raise ValueError("linked CSV destination")
    rows = []
    for decision in verified["decisions"]:
        rows.append({key: decision[key] for key in PROJECTION_COLUMNS})
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=PROJECTION_COLUMNS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    return {"status": "EXPORTED", "rows": len(rows), "sha256": _sha(path.read_bytes()),
            "anchor": verified["anchor"]}


def import_proposals(register: str | Path, csv_path: str | Path) -> list[dict[str, str]]:
    verified = verify_register(register)
    known = {item["decision_id"] for item in verified["decisions"]}
    path = Path(csv_path)
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 1024 * 1024:
        raise ValueError("invalid proposal CSV")
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if tuple(reader.fieldnames or ()) != PROPOSAL_COLUMNS:
            raise ValueError("proposal CSV columns differ from contract")
        rows = list(reader)
    if len(rows) > 1_000:
        raise ValueError("proposal row cap exceeded")
    seen: set[str] = set()
    for row in rows:
        for value in row.values():
            if value.startswith(FORMULA_PREFIXES):
                raise ValueError("spreadsheet formula prefixes are prohibited")
            if len(value) > MAX_TEXT:
                raise ValueError("proposal cell exceeds limit")
        decision_id = _code(row["decision_id"], "decision ID")
        if decision_id not in known or decision_id in seen:
            raise ValueError("unknown or duplicate proposed decision")
        seen.add(decision_id)
        if row["proposed_status"] not in STATUSES - {"CLOSED"}:
            raise ValueError("invalid proposed status")
        _owner(row["owner"], set(verified["owner_roles"]))
        if row["note_code"]:
            _code(row["note_code"], "note code")
        if row["new_due_date"]:
            _date(row["new_due_date"], "new due date")
    return rows

