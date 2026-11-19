from decimal import Decimal
from dataclasses import replace
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from collective_lab import pilot_v16 as pilot
from collective_lab.protocol_v16 import ComputePlanV16
from evolutionary_lab.evidence import verify_ledger


def plan_fixture():
    return {"model": "openai/gpt-6.1-sol", "provider": "openai", "max_completion_tokens": 1800,
            "max_serialized_prompt_bytes": 100000, "framing_token_allowance": 4096,
            "prompt_usd_per_million": "2", "completion_usd_per_million": "10",
            "input_including_cache_usd_per_million": "2.5"}


class FakeTransport:
    def __init__(self, *_):
        self.posts = []
        self.cost = "0.001"
        self.fail = False
        self.remaining = None
        self.price = "0.000002"
        self.reset = None
        self.limit = 5

    def request(self, path, payload=None):
        if path == "key":
            return {"data": {"limit": self.limit, "limit_reset": self.reset,
                             "limit_remaining": self.remaining if self.remaining is not None else str(Decimal(5)-Decimal('.001')*len(self.posts)),
                             "include_byok_in_limit": True}}
        if path.endswith("endpoints"):
            return {"data": {"endpoints": [{"tag": "openai", "pricing": {
                "prompt": self.price, "completion": ".00001", "input_cache_write": ".0000025"}}]}}
        assert path == "chat/completions"
        self.posts.append(payload)
        if self.fail:
            raise TimeoutError("offline timeout")
        public = json.loads(payload["messages"][-1]["content"])
        if payload["response_format"]["json_schema"]["name"] == "acquisition_decision":
            value = {"action": "finish", "evidence_ids": [], "remaining_bundle": [],
                     "remaining_uncertainty": "Offline.", "reason": "Offline.", "accept_early_stop": True}
        else:
            candidates = public["task"]["candidates"]
            value = {"diagnosis": candidates[0], "probabilities": {c: .2 for c in candidates},
                     "rationale": "Offline.", "cited_evidence": [], "strongest_alternative": candidates[1],
                     "recommended_verification": []}
        return {"id": f"offline-{len(self.posts)}", "model": payload["model"], "provider": "OpenAI",
                "usage": {"cost": self.cost, "prompt_tokens": 100, "completion_tokens": 100, "total_tokens": 200},
                "choices": [{"message": {"role": "assistant", "content": json.dumps(value)}, "finish_reason": "stop"}]}


class PilotWalletTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name)/"ledger.jsonl"
        self.ledger = pilot.DurableLedger(self.path)
        self.addCleanup(self.ledger.close)

    def client(self, transport=None, source_check=lambda: None):
        wallet = pilot.Wallet(self.ledger, ceiling_usd=5, max_requests=297)
        client = pilot.BoundedClient(transport or FakeTransport(), wallet, plan_fixture(), source_check=source_check)
        return client, wallet

    def request(self, client):
        return client.complete([{"role": "user", "content": json.dumps({"task": {"candidates": list('abcde')}})}],
                               response_format={"json_schema": {"name": "report"}})

    def test_budget_checked_before_request_and_persists(self):
        wallet = pilot.Wallet(self.ledger, ceiling_usd=1, max_requests=2)
        number = wallet.reserve('.6')
        wallet.settle(number, '.4', 'one')
        with self.assertRaisesRegex(pilot.PilotStop, "BUDGET_EXHAUSTED"):
            wallet.reserve('.7')
        restored = pilot.Wallet(self.ledger, ceiling_usd=1, max_requests=2)
        self.assertEqual(restored.spent, Decimal('.4'))
        self.assertEqual(restored.requests, 1)
        self.assertTrue(verify_ledger(self.path)["valid"])

    def test_crash_after_reservation_cannot_restart_as_free(self):
        pilot.Wallet(self.ledger, ceiling_usd=1, max_requests=2).reserve('.6')
        with self.assertRaisesRegex(pilot.PilotStop, "UNRESOLVED_CHARGE"):
            pilot.Wallet(self.ledger, ceiling_usd=1, max_requests=2)

    def test_record_is_durable_before_transport(self):
        transport = FakeTransport()
        original = transport.request
        def inspect(path, payload=None):
            if payload is not None:
                self.assertEqual(self.ledger.records()[-1]["kind"], "request_reserved")
            response = original(path, payload)
            if path.endswith('endpoints'):
                response['data']['endpoints'].append({'tag': 'openai/flex'})
            return response
        transport.request = inspect
        client, wallet = self.client(transport)
        self.request(client)
        self.assertEqual(wallet.spent, Decimal('.001'))
        self.assertFalse(wallet.pending)
        self.assertFalse(transport.posts[0]["provider"]["allow_fallbacks"])
        self.assertEqual(transport.posts[0]['provider']['ignore'], ['openai/flex'])
        self.assertEqual(transport.posts[0]["provider"]["max_price"], {"prompt": 2.0, "completion": 10.0, "request": 0})

    def test_timeout_and_missing_cost_keep_reservation(self):
        transport = FakeTransport(); transport.fail = True
        client, wallet = self.client(transport)
        with self.assertRaises(TimeoutError):
            self.request(client)
        self.assertTrue(wallet.pending)
        self.assertEqual(wallet.spent, 0)

    def test_missing_cost_is_not_free(self):
        transport = FakeTransport(); transport.cost = None
        client, wallet = self.client(transport)
        with self.assertRaises(pilot.PilotStop):
            self.request(client)
        self.assertTrue(wallet.pending)

    def test_charge_above_reservation_stops_and_preserves_actual_amount(self):
        wallet = pilot.Wallet(self.ledger, ceiling_usd=1, max_requests=2)
        number = wallet.reserve('.1')
        with self.assertRaisesRegex(pilot.PilotStop, "CHARGE_EXCEEDED"):
            wallet.settle(number, '.2', 'overrun')
        self.assertEqual(self.ledger.records()[-1]["reported_cost_usd"], '0.2')
        self.assertTrue(wallet.pending)

    def test_price_increase_and_unbounded_or_resetting_key_prevent_paid_call(self):
        for option, value in (("price", ".000003"), ("remaining", 10), ("reset", "daily"), ("limit", None)):
            with self.subTest(option=option):
                transport = FakeTransport(); setattr(transport, option, value)
                client, wallet = self.client(transport)
                with self.assertRaises(pilot.PilotStop):
                    self.request(client)
                self.assertEqual(transport.posts, [])
                self.assertEqual(wallet.requests, 0)

    def test_source_drift_stops_before_any_provider_contact(self):
        transport = FakeTransport()
        transport.request = lambda *_: self.fail("provider must not be contacted")
        def changed():
            raise pilot.PilotStop("SOURCE_CHANGED")
        client, _ = self.client(transport, changed)
        with self.assertRaisesRegex(pilot.PilotStop, "SOURCE_CHANGED"):
            self.request(client)

    def test_decimal_and_request_count_guards(self):
        for value in (None, True, -1, 'NaN', 'Infinity'):
            with self.assertRaises(pilot.PilotStop):
                pilot.money(value)
        wallet = pilot.Wallet(self.ledger, ceiling_usd=1, max_requests=1)
        wallet.settle(wallet.reserve('.1'), '.01', 'one')
        with self.assertRaisesRegex(pilot.PilotStop, "BUDGET_EXHAUSTED"):
            wallet.reserve('.1')

    def test_concurrent_campaign_writer_is_rejected(self):
        with self.assertRaisesRegex(RuntimeError, "ALREADY_LOCKED"):
            pilot.DurableLedger(self.path)


class PilotLaunchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Reuse the prepared experiment; only signatures/ledger location are fixtures.
        cls.prepared = json.loads((pilot.ROOT/'collective_runs/FROZEN_DEVELOPMENT_MANIFEST_CAUSAL_1_6_PREPARED.json').read_text())["payload"]
        cls.cases = {}
        for spec in cls.prepared["tasks"]:
            cls.cases[spec["layout_seed"]] = pilot.generate_causal_case_v16(
                spec["layout_seed"], spec["task_class"], spec["difficulty"], world_seed=spec["world_seed"])

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        patcher = patch.object(pilot, "ROOT", self.root); patcher.start(); self.addCleanup(patcher.stop)
        self.private, self.public = self.root/'key.pem', self.root/'key.pub'
        subprocess.run(['openssl','genpkey','-algorithm','ED25519','-out',str(self.private)], check=True, capture_output=True)
        subprocess.run(['openssl','pkey','-in',str(self.private),'-pubout','-out',str(self.public)], check=True, capture_output=True)
        (self.root/'source.py').write_text('frozen')
        self.audit = self.root/'audit.json'; self.audit.write_text('{}')
        for name in pilot.EXTRA_SOURCES:
            path = self.root/name; path.parent.mkdir(parents=True, exist_ok=True); path.write_text('fixture')
        self.manifest = self.root/'manifest.json'
        payload = {**self.prepared, "source_sha256": {'source.py': pilot._sha256_file(self.root/'source.py')},
                   "audit_sha256": pilot._sha256_file(self.audit)}
        pilot.write_signed(self.manifest, payload, self.private)
        self.plan = self.root/'plan.json'; self.permission = self.root/'permission.json'
        pilot.prepare_plan(self.manifest, self.audit, self.public, self.private, self.plan,
                           ceiling_usd=5, ledger_path='run.jsonl')
        self.transport = FakeTransport()
        generator = patch.object(pilot, 'generate_causal_case_v16', side_effect=lambda seed, *a, **kw: self.cases[seed])
        generator.start(); self.addCleanup(generator.stop)

    def authorize(self):
        pilot.authorize(self.plan, self.public, self.private, self.permission, approved_ceiling_usd=5)

    def launch(self):
        return pilot.launch(self.permission, self.public, transport_factory=lambda *_: self.transport)

    def test_unsigned_or_unapproved_plan_cannot_launch(self):
        with self.assertRaisesRegex(pilot.PilotStop, 'SIGNED_EXECUTION_PERMISSION'):
            pilot.launch(self.plan, self.public, transport_factory=lambda *_: self.fail('no transport'))
        with self.assertRaisesRegex(pilot.PilotStop, 'MATCHING_APPROVAL'):
            pilot.authorize(self.plan, self.public, self.private, self.permission, approved_ceiling_usd=6)

    def test_full_offline_campaign_and_completed_restart_make_no_extra_calls(self):
        self.authorize()
        result = self.launch()
        self.assertTrue(result['complete'])
        self.assertEqual(result['requests'], 207)
        self.assertEqual(result['confirmed_cost_usd'], '0.207')
        self.assertTrue(self.launch()['already_complete'])
        self.assertEqual(len(self.transport.posts), 207)
        rows = [json.loads(s)['payload'] for s in (self.root/'run.jsonl').read_text().splitlines()]
        self.assertEqual(sum(r['kind'] == 'causal_v16_condition_complete' for r in rows), 54)

    def test_source_tamper_or_task_tamper_prevents_launch(self):
        self.authorize()
        (self.root/'source.py').write_text('changed')
        with self.assertRaisesRegex(pilot.PilotStop, 'SOURCE_CHANGED'):
            self.launch()
        self.assertEqual(self.transport.posts, [])

    def test_regenerated_fingerprint_mismatch_stops_before_transport(self):
        self.authorize()
        case = next(iter(self.cases.values()))
        bad_case = replace(case, causal_task=replace(case.causal_task, briefing='changed'))
        with patch.object(pilot, 'generate_causal_case_v16', return_value=bad_case):
            with self.assertRaisesRegex(pilot.PilotStop, 'TASK_FINGERPRINT_CHANGED'):
                self.launch()
        self.assertEqual(self.transport.posts, [])

    def test_existing_prepared_plan_cannot_be_overwritten(self):
        with self.assertRaises(FileExistsError):
            pilot.prepare_plan(self.manifest, self.audit, self.public, self.private, self.plan,
                               ceiling_usd=6, ledger_path='another.jsonl')

    def test_timeout_cannot_be_retried_on_restart(self):
        self.authorize(); self.transport.fail = True
        with self.assertRaises(TimeoutError):
            self.launch()
        self.transport.fail = False
        with self.assertRaisesRegex(pilot.PilotStop, 'UNRESOLVED_CHARGE'):
            self.launch()
        self.assertEqual(len(self.transport.posts), 1)

    def test_signature_tampering_rejected(self):
        self.authorize()
        Path(str(self.permission)+'.sig').write_bytes(b'bad signature')
        with self.assertRaises(subprocess.CalledProcessError):
            self.launch()
        self.assertEqual(self.transport.posts, [])
