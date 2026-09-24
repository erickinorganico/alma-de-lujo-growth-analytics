"""One-command preparation and exact continuation of a private weekly v1 cut."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import tempfile
from pathlib import Path
from pathlib import PurePosixPath
from typing import Any, Sequence

from alma.decision_register import register_decision, verify_register
from alma.operating_archive import verify_cut
from alma.operating_contracts import canonical_json
from alma.operating_interchange import parse_pack
from alma.operating_mart_contracts import load_policy
from alma.operating_marts import build_operating_marts
from alma.operating_workbook import export_workbook_to_pack
from alma.operating_workspace import _cut_id, build_operating_workspace
from alma.weekly_cycle import (
    read_terminal_packet,
    record_dispatch,
    resume_cycle,
    start_cycle,
    submit_response,
    verify_cycle,
)
from scripts.package_client_v1 import audit_client_zip, build_client_kit


VERSION = "weekly-run-v1"
MAX_JSON_BYTES = 1024 * 1024
_ACTIONS = ("record", "submit", "resume", "packet", "register")
_PACKAGE_RELATIVE = "public-kit/Alma_OS_Client_v1.zip"
_PACKAGE_KEYS = {
    "version", "status", "path", "zip_sha256", "manifest_sha256",
    "member_count", "audit",
}
_PACKAGE_AUDIT_KEYS = {"allowlist", "privacy", "links"}


class WeeklyContractError(ValueError):
    """A bounded weekly command contract was rejected before unsafe mutation."""


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _extended(path: str | Path) -> Path:
    """Use the native Windows long-path form for deeply nested immutable evidence."""
    value = str(Path(path).resolve(strict=False))
    if os.name == "nt" and not value.startswith("\\\\?\\"):
        value = "\\\\?\\" + value
    return Path(value)


def _normal(path: str | Path) -> Path:
    value = str(path)
    if value.startswith("\\\\?\\"):
        value = value[4:]
    return Path(value)


def _write(path: Path, value: Any) -> str:
    raw = canonical_json(value) + b"\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() or path.is_symlink():
        raise WeeklyContractError("immutable weekly artifact already exists")
    path.write_bytes(raw)
    return hashlib.sha256(raw).hexdigest()


def _is_link(path: Path) -> bool:
    return path.is_symlink() or (hasattr(path, "is_junction") and path.is_junction())


def _no_links(path: Path) -> None:
    if _is_link(path) or any(_is_link(parent) for parent in path.parents if parent.exists()):
        raise WeeklyContractError("linked weekly path rejected")
    if path.is_dir() and any(_is_link(item) for item in path.rglob("*")):
        raise WeeklyContractError("linked source member rejected")


def _run_root(value: str | Path) -> Path:
    path = Path(value)
    if ".." in path.parts or tuple(part.lower() for part in path.parts[-2:]) != (
            ".local", "client-runs"):
        raise WeeklyContractError("output root must end in .local/client-runs")
    _no_links(path)
    return path.resolve(strict=False)


def _json_file(path: str | Path) -> dict[str, Any]:
    candidate = Path(path)
    if ".." in candidate.parts or _is_link(candidate) or not candidate.is_file() or \
            candidate.stat().st_size > MAX_JSON_BYTES:
        raise WeeklyContractError("invalid weekly JSON input")
    raw = candidate.read_bytes()
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise WeeklyContractError("invalid weekly JSON input") from exc
    if not isinstance(value, dict) or raw != canonical_json(value):
        raise WeeklyContractError("weekly JSON input must be a canonical object")
    return value


def _copy_pack(source: Path, destination: Path) -> Path:
    _no_links(source)
    if not source.is_dir():
        raise WeeklyContractError("source pack must be a directory")
    shutil.copytree(source, destination)
    return destination


def _package_identity(package: Path, built: dict[str, Any],
                      audited: dict[str, Any]) -> dict[str, Any]:
    """Project builder/auditor output to the exact public weekly boundary."""
    agreement = ("version", "status", "manifest_sha256", "member_count", "privacy", "links")
    if (any(built.get(key) != audited.get(key) for key in agreement) or
            built.get("status") != "PASS" or audited.get("status") != "PASS" or
            built.get("sha256") != _sha(package)):
        raise WeeklyContractError("public package build and audit disagree")
    return {
        "version": built["version"],
        "status": "PASS",
        "path": _PACKAGE_RELATIVE,
        "zip_sha256": built["sha256"],
        "manifest_sha256": built["manifest_sha256"],
        "member_count": built["member_count"],
        "audit": {
            "allowlist": audited["status"],
            "privacy": audited["privacy"],
            "links": audited["links"],
        },
    }


def _verify_package_identity(folder: Path, identity: Any) -> Path:
    """Rehash and freshly audit the exact run-relative public package."""
    if (not isinstance(identity, dict) or set(identity) != _PACKAGE_KEYS or
            not isinstance(identity.get("audit"), dict) or
            set(identity["audit"]) != _PACKAGE_AUDIT_KEYS or
            identity.get("status") != "PASS" or identity.get("path") != _PACKAGE_RELATIVE):
        raise WeeklyContractError("weekly public package identity invalid")
    relative = PurePosixPath(identity["path"])
    if (relative.is_absolute() or ".." in relative.parts or
            relative.as_posix() != identity["path"]):
        raise WeeklyContractError("weekly public package path escaped its run")
    package = (folder / Path(*relative.parts)).resolve(strict=True)
    if (not package.is_relative_to(folder) or _is_link(package) or not package.is_file() or
            _sha(package) != identity.get("zip_sha256")):
        raise WeeklyContractError("weekly public package bytes changed")
    _no_links(package)
    audited = audit_client_zip(package)
    if (identity.get("version") != audited.get("version") or
            identity.get("manifest_sha256") != audited.get("manifest_sha256") or
            identity.get("member_count") != audited.get("member_count") or
            identity["audit"] != {"allowlist": audited.get("status"),
                                  "privacy": audited.get("privacy"),
                                  "links": audited.get("links")}):
        raise WeeklyContractError("weekly public package audit binding changed")
    return package


def _safe_receipt(state: dict[str, Any], destination: Path,
                  input_route: str, public_package: dict[str, Any]) -> dict[str, Any]:
    cycle = _normal(str(state["destination"]))
    return {
        "version": VERSION,
        "status": state["status"],
        "cut_id": state["cut_id"],
        "run_id": state["run_id"],
        "run": str(destination),
        "cycle": cycle.relative_to(destination).as_posix(),
        "cycle_path": str(_extended(cycle)),
        "input_route": input_route,
        "current_cut_sha256": state["current_cut_sha256"],
        "manifest_sha256": state["manifest_sha256"],
        "mart_bundle_sha256": state["mart_bundle_sha256"],
        "task_bundle_sha256": state["task_bundle_sha256"],
        "public_package": public_package,
        "native_execution_claimed": False,
        "external_execution": "PROHIBITED",
    }


def create_weekly_run(source_pack: str | Path, policy: str | Path,
                      output_root: str | Path, *,
                      prior_register: str | Path | None = None,
                      prior_anchor: str | Path | None = None) -> dict[str, Any]:
    """Adapt, verify and freeze one cut without claiming native execution."""

    if (prior_register is None) != (prior_anchor is None):
        raise WeeklyContractError("prior register and anchor must be supplied together")
    root = _run_root(output_root)
    source = Path(source_pack).resolve(strict=True)
    policy_path = Path(policy).resolve(strict=True)
    _no_links(source)
    _no_links(policy_path)
    if prior_register is not None:
        try:
            verify_register(prior_register, prior_anchor)
        except (ValueError, OSError, KeyError, TypeError, json.JSONDecodeError) as exc:
            raise WeeklyContractError("prior register or anchor verification failed") from exc

    root.parent.mkdir(parents=True, exist_ok=True)
    prepare = Path(tempfile.mkdtemp(prefix=".weekly-prepare-", dir=root.parent))
    destination: Path | None = None
    created_destination = False
    try:
        if source.suffix.lower() == ".xlsx":
            copied = prepare / "source.xlsx"
            shutil.copyfile(source, copied)
            exported = export_workbook_to_pack(copied, prepare / "workbook-adapter",
                                               private_root=prepare)
            candidate_pack = Path(exported["pack_path"])
            input_route = "workbook"
            source_receipt = {
                "status": "PASS",
                "input_route": input_route,
                "workbook_sha256": exported["workbook_sha256"],
                "adapter_manifest_sha256": exported["manifest_sha256"],
            }
        else:
            candidate_pack = source
            input_route = "pack"
            source_receipt = {"status": "PASS", "input_route": input_route}

        parsed = parse_pack(candidate_pack, private_root=candidate_pack.parent)
        cut_id = _cut_id(parsed)
        real_cut = parsed["metadata"]["input_class"] != "SYNTHETIC_EXAMPLE"
        loaded_policy = load_policy(policy_path, as_of=parsed["metadata"]["cutoff_at"][:10],
                                    real_cut=real_cut)
        if real_cut and loaded_policy.status == "SYNTHETIC_EXAMPLE":
            raise WeeklyContractError("synthetic policy cannot authorize a real cut")
        destination = root / cut_id
        if destination.exists() or destination.is_symlink():
            raise WeeklyContractError("weekly cut already exists")
        destination.mkdir(parents=True)
        created_destination = True
        input_dir = destination / "input"
        input_dir.mkdir()
        if input_route == "workbook":
            shutil.move(str(prepare / "workbook-adapter"), str(input_dir / "workbook-adapter"))
            pack = input_dir / "workbook-adapter" / "source-pack"
        else:
            pack = _copy_pack(candidate_pack, input_dir / "source-pack")
        shutil.copyfile(policy_path, input_dir / "policy.json")
        source_receipt.update({
            "cut_id": cut_id,
            "input_class": parsed["metadata"]["input_class"],
            "metadata_sha256": parsed["metadata_sha256"],
            "normalized_rows_digest": parsed["normalized_rows_digest"],
        })

        built = build_operating_workspace(pack, private_root=destination)
        verified_cut = verify_cut(built["destination"], private_root=destination)
        mart_root = _extended(destination / ".local" / "operating-marts")
        mart = build_operating_marts(
            built["destination"], mart_root,
            policy_path=input_dir / "policy.json", private_root=mart_root,
        )
        state = start_cycle(
            built["destination"], mart["destination"],
            _extended(destination / ".local" / "weekly-cycles"),
            prior_register=prior_register, prior_anchor=prior_anchor,
        )
        if state["status"] != "WAITING_ANALYSTS":
            raise WeeklyContractError("new weekly run must remain waiting for analysts")
        cycle = _normal(str(state["destination"]))
        mart_manifest = Path(str(mart["destination"])) / "manifest.json"
        package = destination / Path(*PurePosixPath(_PACKAGE_RELATIVE).parts)
        built_package = build_client_kit(package)
        audited_package = audit_client_zip(package)
        public_package = _package_identity(package, built_package, audited_package)
        receipt_hashes = {
            "source.json": _write(destination / "receipts" / "source.json", source_receipt),
            "workspace.json": _write(destination / "receipts" / "workspace.json", {
                "status": verified_cut["status"], "cut_id": cut_id,
                "manifest_sha256": state["manifest_sha256"],
            }),
            "marts.json": _write(destination / "receipts" / "marts.json", {
                "status": "PASS", "cut_id": cut_id,
                "policy_sha256": loaded_policy.sha256,
                "policy_status": loaded_policy.status,
                "mart_manifest_sha256": _sha(mart_manifest),
                "mart_bundle_sha256": state["mart_bundle_sha256"],
            }),
            "native-waiting.json": _write(destination / "receipts" / "native-waiting.json", {
                "status": "WAITING_ANALYSTS", "cut_id": cut_id,
                "run_id": state["run_id"],
                "current_cut_sha256": state["current_cut_sha256"],
                "task_bundle_sha256": state["task_bundle_sha256"],
                "native_execution_claimed": False,
            }),
            "public-package.json": _write(
                destination / "receipts" / "public-package.json", public_package
            ),
        }
        index = {
            "version": VERSION,
            "cut_id": cut_id,
            "status": "WAITING_ANALYSTS",
            "input_route": input_route,
            "source_pack": pack.relative_to(destination).as_posix(),
            "workspace": Path(str(built["destination"])).relative_to(destination).as_posix(),
            "mart_bundle": _normal(str(mart["destination"])).relative_to(destination).as_posix(),
            "cycle": cycle.relative_to(destination).as_posix(),
            "policy": {"path": "input/policy.json", "status": loaded_policy.status,
                       "sha256": loaded_policy.sha256},
            "prior": {"supplied": prior_register is not None,
                      "anchor": state.get("decision_register_anchor")},
            "receipts": receipt_hashes,
            "public_package": public_package,
            "external_execution": "PROHIBITED",
        }
        _write(destination / "run-index.json", index)
        return _safe_receipt(state, destination, input_route, public_package)
    except WeeklyContractError:
        if created_destination and destination is not None and destination.exists():
            shutil.rmtree(_extended(destination), ignore_errors=True)
        raise
    except (ValueError, OSError, KeyError, TypeError, json.JSONDecodeError) as exc:
        if created_destination and destination is not None and destination.exists():
            shutil.rmtree(_extended(destination), ignore_errors=True)
        raise WeeklyContractError("weekly preparation failed verification") from exc
    finally:
        if prepare.exists():
            shutil.rmtree(prepare)


def _load_run(run: str | Path) -> tuple[Path, dict[str, Any], Path]:
    folder = Path(run).resolve(strict=True)
    _run_root(folder.parent)
    if _is_link(folder) or not folder.is_dir():
        raise WeeklyContractError("invalid weekly run")
    index_path = folder / "run-index.json"
    try:
        index = json.loads(index_path.read_bytes())
    except (OSError, json.JSONDecodeError) as exc:
        raise WeeklyContractError("weekly index unavailable") from exc
    if (index_path.read_bytes() != canonical_json(index) + b"\n" or
            index.get("version") != VERSION or index.get("cut_id") != folder.name):
        raise WeeklyContractError("weekly index verification failed")
    for name, expected in index.get("receipts", {}).items():
        path = folder / "receipts" / name
        if not path.is_file() or _sha(path) != expected:
            raise WeeklyContractError("weekly stage receipt changed")
    try:
        package_receipt_path = folder / "receipts" / "public-package.json"
        package_receipt_raw = package_receipt_path.read_bytes()
        package_receipt = json.loads(package_receipt_raw)
        if package_receipt_raw != canonical_json(package_receipt) + b"\n":
            raise WeeklyContractError("weekly public package receipt is not canonical")
        if index.get("public_package") != package_receipt:
            raise WeeklyContractError("weekly package receipt and index disagree")
        _verify_package_identity(folder, package_receipt)
    except WeeklyContractError:
        raise
    except (ValueError, OSError, KeyError, TypeError, json.JSONDecodeError) as exc:
        raise WeeklyContractError("weekly public package verification failed") from exc
    normal_cycle = (folder / index["cycle"]).resolve(strict=True)
    if not normal_cycle.is_relative_to(folder):
        raise WeeklyContractError("weekly cycle escaped its run")
    cycle = _extended(normal_cycle)
    verified = verify_cycle(cycle)
    if verified["cut_id"] != index["cut_id"]:
        raise WeeklyContractError("weekly cycle identity changed")
    return folder, index, cycle


def continue_weekly_run(run: str | Path, action: str, *, role: str | None = None,
                        response: str | Path | None = None,
                        query_trace: str | Path | None = None,
                        dispatch_receipt: str | Path | None = None,
                        register: str | Path | None = None,
                        decision_event: str | Path | None = None) -> dict[str, Any]:
    """Perform exactly one validated continuation action on an existing run."""

    if action not in _ACTIONS:
        raise WeeklyContractError("invalid weekly continuation action")
    _, _, cycle = _load_run(run)
    native = (role, response, query_trace, dispatch_receipt)
    owner = (register, decision_event)
    if action in {"record", "submit"}:
        if any(value is None for value in native) or any(value is not None for value in owner):
            raise WeeklyContractError("record and submit require only native evidence flags")
    elif action == "register":
        if any(value is not None for value in native) or any(value is None for value in owner):
            raise WeeklyContractError("register requires only register and decision-event")
    elif any(value is not None for value in (*native, *owner)):
        raise WeeklyContractError("resume and packet reject action-only flags")
    try:
        if action == "record":
            fields = _json_file(dispatch_receipt)  # type: ignore[arg-type]
            result = record_dispatch(cycle, role or "", response or "", query_trace or "", fields)
            return {"status": "RECORDED", "role": role, "request_id": result["request_id"],
                    "dispatch_sha256": _sha(cycle / "tasks" / f"{role}.dispatch.json")}
        if action == "submit":
            result = submit_response(cycle, role or "", response or "", query_trace or "",
                                     dispatch_receipt or "")
            return {"status": result["status"], "role": role,
                    "cut_id": result["cut_id"], "run_id": result["run_id"]}
        if action == "resume":
            result = resume_cycle(cycle)
            return {"status": result["status"], "cut_id": result["cut_id"],
                    "run_id": result["run_id"]}
        if action == "packet":
            return read_terminal_packet(cycle)
        event = _json_file(decision_event)  # type: ignore[arg-type]
        required = {"recommendation_id", "owner_role", "due_date", "owner_choice",
                    "closure_check"}
        if set(event) != required or not isinstance(event["closure_check"], dict):
            raise WeeklyContractError("invalid owner decision event")
        verify_register(register or "")
        result = register_decision(register or "", cycle, event["recommendation_id"],
            event["owner_role"], event["due_date"], event["owner_choice"],
            event["closure_check"])
        return {key: result[key] for key in ("decision_id", "event_id", "status", "anchor")}
    except WeeklyContractError:
        raise
    except (ValueError, OSError, KeyError, TypeError, json.JSONDecodeError) as exc:
        raise WeeklyContractError("weekly continuation failed verification") from exc


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    weekly = commands.add_parser("weekly", help="prepare one immutable private weekly cut")
    weekly.add_argument("--source-pack", required=True)
    weekly.add_argument("--policy", required=True)
    weekly.add_argument("--output-root", required=True)
    weekly.add_argument("--prior-register")
    weekly.add_argument("--prior-anchor")
    resume = commands.add_parser("weekly-resume", help="perform one exact continuation action")
    resume.add_argument("--run", required=True)
    resume.add_argument("--action", required=True, choices=_ACTIONS)
    resume.add_argument("--role")
    resume.add_argument("--response")
    resume.add_argument("--query-trace")
    resume.add_argument("--dispatch-receipt")
    resume.add_argument("--register")
    resume.add_argument("--decision-event")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "weekly":
            result = create_weekly_run(args.source_pack, args.policy, args.output_root,
                prior_register=args.prior_register, prior_anchor=args.prior_anchor)
        else:
            result = continue_weekly_run(args.run, args.action, role=args.role,
                response=args.response, query_trace=args.query_trace,
                dispatch_receipt=args.dispatch_receipt, register=args.register,
                decision_event=args.decision_event)
        print(json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
        return 0
    except WeeklyContractError as exc:
        print(json.dumps({"status": "ERROR", "code": "weekly_verification_failed",
                          "detail": str(exc)}, sort_keys=True), file=__import__("sys").stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
