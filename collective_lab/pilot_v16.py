"""Signed pilot permissions, durable request reservations, and fail-closed execution."""
from __future__ import annotations

import argparse
from decimal import Decimal, InvalidOperation, ROUND_CEILING
import hashlib
import json
import os
from pathlib import Path
import subprocess
import urllib.request

from .causal_generator_v16 import generate_causal_case_v16
from .causal_generator import CAUSAL_TASK_CLASSES, DIFFICULTIES
from .freeze_v12 import _canonical, _sha256_file, _sign, _write_manifest
from .ledger import ExclusiveRunLedger
from .openrouter import Completion
from .protocol_v16 import ACQUISITION_CONDITIONS, REASONING_CONDITIONS, ComputePlanV16
from .runner_v16 import HarnessV16

ROOT = Path(__file__).resolve().parents[1]
EXTRA_SOURCES = ("collective_lab/pilot_v16.py", "collective_lab/precision_v16.py",
                 "tests/test_pilot_v16.py", "tests/test_precision_v16.py",
                 "CAUSAL_1_6_PILOT_OPERATIONS.md", "CAUSAL_1_6_EVALUATION_ANALYSIS_PLAN.md",
                 "requirements-evaluation-v16.txt")


class PilotStop(RuntimeError):
    pass


def money(value):
    if isinstance(value, bool):
        raise PilotStop("INVALID_DOLLAR_AMOUNT")
    try:
        amount = Decimal(str(value))
    except InvalidOperation as exc:
        raise PilotStop("INVALID_DOLLAR_AMOUNT") from exc
    if not amount.is_finite() or amount < 0:
        raise PilotStop("INVALID_DOLLAR_AMOUNT")
    return amount


def within_root(name):
    path = (ROOT/name).resolve()
    if not path.is_relative_to(ROOT):
        raise PilotStop("PATH_OUTSIDE_PROJECT")
    return path


def check_sources(hashes):
    if not hashes:
        raise PilotStop("SOURCE_HASHES_MISSING")
    for name, expected in hashes.items():
        path = within_root(name)
        if not path.is_file() or _sha256_file(path) != expected:
            raise PilotStop(f"SOURCE_CHANGED:{name}")


def verified_document(path, public_key):
    path, public_key = Path(path), Path(public_key)
    document = json.loads(path.read_text())
    if hashlib.sha256(_canonical(document["payload"])).hexdigest() != document["payload_sha256"]:
        raise PilotStop("PAYLOAD_HASH_INVALID")
    subprocess.run(["openssl", "pkeyutl", "-verify", "-pubin", "-inkey", str(public_key),
                    "-rawin", "-in", str(path), "-sigfile", str(path)+".sig"],
                   check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    check_sources(document["payload"]["source_sha256"])
    return document["payload"]


def write_signed(path, payload, private_key):
    path = Path(path)
    if path.exists() or Path(str(path)+".sig").exists():
        raise FileExistsError(path)
    _write_manifest(path, payload)
    _sign(path, Path(private_key))


def validate_prepared(payload):
    tasks = payload.get("tasks", [])
    if (payload.get("split") != "development" or payload.get("protocol_version") != "causal-1.6-dev"
            or payload.get("task_count") != 9 or len(tasks) != 9
            or payload.get("execution_authorized") is not False
            or len({t["task_id"] for t in tasks}) != 9
            or {t["task_index"] for t in tasks} != set(range(9))
            or {(t["task_class"], t["difficulty"]) for t in tasks} !=
               {(kind, band) for kind in CAUSAL_TASK_CLASSES for band in DIFFICULTIES}):
        raise PilotStop("PREPARED_V16_DEVELOPMENT_REQUIRED")
    for task in tasks:
        if (sorted(task["reasoning_order"]) != sorted(REASONING_CONDITIONS) or
                sorted(task["acquisition_order"]) != sorted(ACQUISITION_CONDITIONS)):
            raise PilotStop("CONDITION_SCHEDULE_CHANGED")


def prepare_plan(manifest, audit, public_key, private_key, output, *, ceiling_usd, ledger_path):
    payload = verified_document(manifest, public_key)
    validate_prepared(payload)
    if _sha256_file(Path(audit)) != payload["audit_sha256"]:
        raise PilotStop("AUDIT_CHANGED")
    ceiling = money(ceiling_usd)
    if not 0 < ceiling <= 100:
        raise PilotStop("EXPLICIT_CEILING_REQUIRED_MAX_100_USD")
    within_root(ledger_path)
    extra = {name: _sha256_file(ROOT/name) for name in EXTRA_SOURCES}
    plan = {
        "schema": "causal-v16-pilot-permission-v1", "execution_authorized": False,
        "ceiling_usd": str(ceiling), "ledger_path": ledger_path,
        "prepared_manifest": str(Path(manifest).resolve().relative_to(ROOT)),
        "prepared_manifest_sha256": _sha256_file(Path(manifest)),
        "audit_path": str(Path(audit).resolve().relative_to(ROOT)), "audit_sha256": payload["audit_sha256"],
        "public_key_sha256": _sha256_file(Path(public_key)),
        "source_sha256": {**payload["source_sha256"], **extra},
        "model": payload["model"], "provider": "openai", "max_requests": 297,
        "max_completion_tokens": 1800, "max_serialized_prompt_bytes": 100000,
        "framing_token_allowance": 4096, "timeout_seconds": 300,
        "prompt_usd_per_million": "2", "completion_usd_per_million": "10",
        "input_including_cache_usd_per_million": "2.5",
        "request_fee_usd": "0", "require_provider_key_cap": True,
        "evaluation_seed_generation_allowed": False, "automatic_promotion": False,
    }
    write_signed(output, plan, private_key)
    return plan


def authorize(plan_path, public_key, private_key, output, *, approved_ceiling_usd):
    plan = verified_document(plan_path, public_key)
    if plan.get("execution_authorized") is not False or money(approved_ceiling_usd) != money(plan["ceiling_usd"]):
        raise PilotStop("EXPLICIT_MATCHING_APPROVAL_REQUIRED")
    authorized = {**plan, "execution_authorized": True, "prepared_plan_sha256": _sha256_file(Path(plan_path))}
    write_signed(output, authorized, private_key)
    return authorized


class DurableLedger(ExclusiveRunLedger):
    def append(self, payload):
        record = super().append(payload)
        with self.path.open("rb") as handle:
            os.fsync(handle.fileno())
        # Persist a newly created directory entry as well as its contents.
        descriptor = os.open(self.path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
        return record

    def records(self):
        if not self.path.exists():
            return []
        return [json.loads(line)["payload"] for line in self.path.read_text().splitlines() if line.strip()]


class Wallet:
    def __init__(self, ledger, *, ceiling_usd, max_requests):
        self.ledger = ledger
        self.ceiling = money(ceiling_usd)
        self.max_requests = max_requests
        self.spent = Decimal(0)
        self.pending = {}
        self.requests = 0
        for row in ledger.records():
            if row["kind"] == "request_reserved":
                if row["request_number"] in self.pending:
                    raise PilotStop("DUPLICATE_RESERVATION")
                self.pending[row["request_number"]] = money(row["reserved_usd"])
                self.requests += 1
            elif row["kind"] == "request_settled":
                number = row["request_number"]
                if number not in self.pending or money(row["cost_usd"]) > self.pending[number]:
                    raise PilotStop("INVALID_SETTLEMENT")
                self.spent += money(row["cost_usd"])
                del self.pending[number]
        if self.pending:
            raise PilotStop("UNRESOLVED_CHARGE_NO_AUTOMATIC_RETRY")
        if self.spent > self.ceiling:
            raise PilotStop("DOLLAR_CEILING_EXCEEDED")

    def reserve(self, amount):
        amount = money(amount)
        if self.pending:
            raise PilotStop("UNRESOLVED_CHARGE_NO_AUTOMATIC_RETRY")
        if self.requests >= self.max_requests or self.spent + amount > self.ceiling:
            raise PilotStop("PILOT_BUDGET_EXHAUSTED")
        number = self.requests + 1
        self.ledger.append({"kind": "request_reserved", "request_number": number,
                            "reserved_usd": str(amount), "confirmed_spent_usd": str(self.spent)})
        self.pending[number] = amount
        self.requests = number
        return number

    def settle(self, number, cost, request_id):
        cost = money(cost)
        if cost > self.pending[number]:
            self.ledger.append({"kind": "charge_exceeded_reservation", "request_number": number,
                                "reported_cost_usd": str(cost), "request_id": request_id})
            raise PilotStop("CHARGE_EXCEEDED_RESERVATION")
        self.ledger.append({"kind": "request_settled", "request_number": number,
                            "cost_usd": str(cost), "request_id": request_id})
        self.spent += cost
        del self.pending[number]


class Transport:
    """No automatic retry; errors never include authorization headers or bodies."""
    def __init__(self, api_key, timeout):
        if not api_key:
            raise PilotStop("OPENROUTER_API_KEY_MISSING")
        self.key, self.timeout = api_key, timeout

    def request(self, path, payload=None):
        request = urllib.request.Request("https://openrouter.ai/api/v1/"+path,
            data=None if payload is None else json.dumps(payload).encode(),
            headers={"Authorization": "Bearer "+self.key, "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                return json.loads(response.read())
        except Exception as exc:
            raise PilotStop(f"OPENROUTER_REQUEST_FAILED:{type(exc).__name__}") from None


class BoundedClient:
    def __init__(self, transport, wallet, plan, *, source_check):
        self.transport, self.wallet, self.plan, self.source_check = transport, wallet, plan, source_check
        self.model = plan["model"]

    def preflight_provider(self, input_bound):
        key = self.transport.request("key")["data"]
        remaining = money(key.get("limit_remaining"))
        if (key.get("limit") is None or key.get("limit_reset") is not None or
                key.get("include_byok_in_limit") is not True or
                remaining > self.wallet.ceiling-self.wallet.spent or remaining <= 0):
            raise PilotStop("NONRESETTING_PROVIDER_KEY_CAP_REQUIRED")
        data = self.transport.request(f"models/{self.model}/endpoints")["data"]
        # A base provider slug can match variants. Explicitly exclude them so
        # the checked standard endpoint is also the one eligible for routing.
        self.ignored_endpoints = [e["tag"] for e in data["endpoints"]
                                  if e.get("tag", "").startswith(self.plan["provider"]+"/")]
        endpoints = [e for e in data["endpoints"] if e.get("tag") == self.plan["provider"]]
        if len(endpoints) != 1:
            raise PilotStop("PINNED_PROVIDER_ENDPOINT_UNAVAILABLE")
        prices = endpoints[0]["pricing"]
        applicable = [prices, *(p for p in prices.get("overrides", [])
                                 if p.get("min_prompt_tokens", 0) <= input_bound)]
        for price in applicable:
            for field, ceiling in (("prompt", "prompt_usd_per_million"),
                                   ("completion", "completion_usd_per_million"),
                                   ("input_cache_write", "input_including_cache_usd_per_million"),
                                   ("input_cache_read", "input_including_cache_usd_per_million"),
                                   ("internal_reasoning", "completion_usd_per_million")):
                if money(price.get(field, prices.get(field, 0)))*1000000 > money(self.plan[ceiling]):
                    raise PilotStop("PROVIDER_PRICE_INCREASE")
            if money(price.get("request", 0)) != 0:
                raise PilotStop("PROVIDER_REQUEST_FEE_NOT_ALLOWED")
        return remaining

    def complete(self, messages, *, tools=None, response_format=None, max_tokens=1800, seed=None):
        self.source_check()
        if tools is not None or not 0 < max_tokens <= self.plan["max_completion_tokens"]:
            raise PilotStop("UNSUPPORTED_REQUEST_SHAPE")
        raw = json.dumps({"messages": messages, "response_format": response_format}, ensure_ascii=False).encode()
        if len(raw) > self.plan["max_serialized_prompt_bytes"]:
            raise PilotStop("PROMPT_SIZE_LIMIT")
        # Byte-based conservative admission estimate, including schema and framing.
        # Provider key cap is an independent backstop; this is not a tokenizer proof.
        input_bound = len(raw) + self.plan["framing_token_allowance"]
        reserved = ((input_bound*money(self.plan["input_including_cache_usd_per_million"])
                     + max_tokens*money(self.plan["completion_usd_per_million"]))/1000000
                    ).quantize(Decimal("0.000001"), rounding=ROUND_CEILING)
        remaining = self.preflight_provider(input_bound)
        if reserved > remaining:
            raise PilotStop("PROVIDER_KEY_BUDGET_INSUFFICIENT")
        payload = {"model": self.model, "messages": messages, "max_tokens": max_tokens,
                   "reasoning": {"effort": "medium"}, "response_format": response_format,
                   "seed": seed, "usage": {"include": True}, "stream": False,
                   "provider": {"only": [self.plan["provider"]], "ignore": self.ignored_endpoints,
                                "allow_fallbacks": False,
                                "require_parameters": True, "max_price": {
                                    "prompt": float(self.plan["prompt_usd_per_million"]),
                                    "completion": float(self.plan["completion_usd_per_million"]), "request": 0}}}
        number = self.wallet.reserve(reserved)
        body = self.transport.request("chat/completions", payload)
        usage = body.get("usage", {})
        # Missing/invalid costs leave the reservation unresolved and halt the run.
        self.wallet.settle(number, usage.get("cost"), str(body.get("id", "")))
        if money(usage.get("prompt_tokens")) > input_bound or money(usage.get("completion_tokens")) > max_tokens:
            raise PilotStop("TOKEN_BOUND_VIOLATED")
        choice = body["choices"][0]
        if body.get("model") != self.model:
            raise PilotStop("MODEL_CHANGED")
        return Completion(str(body["id"]), body["model"], body.get("provider"),
                          choice["message"], usage, choice.get("finish_reason"))


def launch(permission, public_key, *, transport_factory=Transport):
    plan = verified_document(permission, public_key)
    if (plan.get("schema") != "causal-v16-pilot-permission-v1" or
            plan.get("execution_authorized") is not True or
            plan.get("evaluation_seed_generation_allowed") is not False):
        raise PilotStop("SIGNED_EXECUTION_PERMISSION_REQUIRED")
    if _sha256_file(Path(public_key)) != plan["public_key_sha256"]:
        raise PilotStop("SIGNING_KEY_CHANGED")
    manifest = within_root(plan["prepared_manifest"])
    if _sha256_file(manifest) != plan["prepared_manifest_sha256"] or _sha256_file(within_root(plan["audit_path"])) != plan["audit_sha256"]:
        raise PilotStop("PREPARED_INPUT_CHANGED")
    prepared = verified_document(manifest, public_key)
    validate_prepared(prepared)
    if prepared["model"] != plan["model"] or prepared["compute_plan"] != ComputePlanV16().mapping():
        raise PilotStop("EXPERIMENT_CONFIGURATION_CHANGED")
    # Verify every task before constructing any authenticated client.
    cases = []
    for spec in prepared["tasks"]:
        case = generate_causal_case_v16(spec["layout_seed"], spec["task_class"], spec["difficulty"], world_seed=spec["world_seed"])
        if (case.causal_task.fingerprint() != spec["task_fingerprint"] or
                list(case.packet_ids) != spec["packet_ids"] or case.acquisition_budget != spec["acquisition_budget"]):
            raise PilotStop("TASK_FINGERPRINT_CHANGED")
        cases.append((spec, case))
    digest = _sha256_file(Path(permission))
    with DurableLedger(within_root(plan["ledger_path"])) as ledger:
        records = ledger.records()
        if records and records[0] != {"kind": "pilot_started", "permission_sha256": digest}:
            raise PilotStop("CAMPAIGN_PERMISSION_CHANGED")
        if not records:
            ledger.append({"kind": "pilot_started", "permission_sha256": digest})
        wallet = Wallet(ledger, ceiling_usd=plan["ceiling_usd"], max_requests=plan["max_requests"])
        started = {(r["task_id"], r["condition"]) for r in records if r["kind"] == "causal_v16_condition_started"}
        completed = {(r["task_id"], r["condition"]) for r in records if r["kind"] == "causal_v16_condition_complete"}
        if started != completed or any(r["kind"] == "pilot_stopped" for r in records):
            raise PilotStop("INTERRUPTED_CAMPAIGN_REQUIRES_REVIEW_NO_RETRY")
        if any(r["kind"] == "pilot_complete" for r in records):
            return {"complete": True, "confirmed_cost_usd": str(wallet.spent), "already_complete": True}
        client = BoundedClient(transport_factory(os.environ.get("OPENROUTER_API_KEY"), plan["timeout_seconds"]),
                               wallet, plan, source_check=lambda: check_sources(plan["source_sha256"]))
        harness = HarnessV16(client, ledger)
        try:
            for spec, case in cases:
                for condition in spec["reasoning_order"] + spec["acquisition_order"]:
                    if (case.task.task_id, condition) in completed:
                        continue
                    result = harness.run_condition(case, condition)
                    if not result["eligible"]:
                        raise PilotStop("INELIGIBLE_CONDITION_REQUIRES_REVIEW")
        except Exception as exc:
            ledger.append({"kind": "pilot_stopped", "reason": str(exc),
                            "confirmed_cost_usd": str(wallet.spent),
                            "unresolved_reserved_usd": str(sum(wallet.pending.values()))})
            raise
        ledger.append({"kind": "pilot_complete", "confirmed_cost_usd": str(wallet.spent), "requests": wallet.requests})
        return {"complete": True, "confirmed_cost_usd": str(wallet.spent), "requests": wallet.requests}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    prep = sub.add_parser("prepare")
    for name in ("manifest", "audit", "public-key", "private-key", "output"):
        prep.add_argument("--"+name, type=Path, required=True)
    prep.add_argument("--ceiling-usd", required=True)
    prep.add_argument("--ledger-path", required=True)
    auth = sub.add_parser("authorize")
    for name in ("plan", "public-key", "private-key", "output"):
        auth.add_argument("--"+name, type=Path, required=True)
    auth.add_argument("--approved-ceiling-usd", required=True)
    run = sub.add_parser("run")
    run.add_argument("--permission", type=Path, required=True)
    run.add_argument("--public-key", type=Path, required=True)
    args = vars(parser.parse_args())
    command = args.pop("command")
    if command == "prepare":
        prepare_plan(**args)
        print(json.dumps({"prepared": True, "execution_authorized": False, "ceiling_usd": args["ceiling_usd"]}))
    elif command == "authorize":
        args["plan_path"] = args.pop("plan")
        authorize(**args)
        print(json.dumps({"signed_permission_created": True, "paid_requests": 0}))
    else:
        print(json.dumps(launch(**args)))


if __name__ == "__main__":
    main()
