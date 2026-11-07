from dataclasses import replace
import json
import unittest

from experiment import Authorization as A, State as S, MAX_NONCE, execute, run, evidence


class ExperimentTests(unittest.TestCase):
    def test_delegation_survives_revert(self):
        r = execute(S(), [A()], False, -7)
        self.assertEqual(r["after"], {"delegate": "A", "nonce": 1, "assets": 100, "ordinary_code": False})
        self.assertEqual(r["after_authorizations"], r["after"])

    def test_report_inspects_failed_execution(self):
        r = execute(S(), [A()], False, -7)
        self.assertEqual(r["reports"]["balance_only"], {"asset_delta": 0})
        self.assertEqual(r["reports"]["success_only"], {"inspected": False, "net_delegate_changed": None})
        self.assertEqual(r["reports"]["authority_always"], {
            "inspected": True, "delegate_before": None, "delegate_after": "A", "net_delegate_changed": True,
            "ordered_pointer_changes": [{"tuple_index": 0, "from": None, "to": "A"}]})

    def test_invalid_twin_same_balance_different_authority(self):
        a = execute(S(), [A()], False, -7)
        b = execute(S(), [A(nonce=1)], False, -7)
        self.assertEqual(a["reports"]["balance_only"], b["reports"]["balance_only"])
        self.assertEqual(b["after"], {"delegate": None, "nonce": 0, "assets": 100, "ordinary_code": False})
        self.assertFalse(b["reports"]["authority_always"]["net_delegate_changed"])

    def test_success_commits_asset_delta(self):
        r = execute(S(), [A()], True, -7)
        self.assertEqual((r["after"]["delegate"], r["after"]["assets"], r["after"]["nonce"]), ("A", 93, 1))
        self.assertTrue(r["reports"]["success_only"]["net_delegate_changed"])

    def test_expected_fixture_states(self):
        # Explicit expected final states, not generated from the implementation's checks.
        expected = {
            "valid_revert": ("A", 1, 100), "valid_success": ("A", 1, 93),
            "invalid_nonce_twin": (None, 0, 100), "wrong_chain": (None, 0, 100),
            "chain_zero": ("A", 1, 100), "invalid_recovery": (None, 0, 100),
            "ordinary_code": (None, 0, 100), "same_delegate": ("A", 1, 100),
            "clear_delegate": (None, 1, 100), "last_valid_wins": ("B", 2, 100),
            "replayed_nonce": ("A", 1, 100), "invalid_then_valid": ("A", 1, 100),
            "net_equal": ("A", 2, 100), "nonce_at_limit": (None, MAX_NONCE, 100),
            "nonce_before_limit": ("A", MAX_NONCE, 100),
        }
        rows = run()["rows"]
        self.assertEqual(set(expected), {r["case"] for r in rows})
        for row in rows:
            with self.subTest(case=row["case"]):
                a = row["after"]
                self.assertEqual((a["delegate"], a["nonce"], a["assets"]), expected[row["case"]])

    def test_failed_tuple_does_not_stop_later_valid_tuple(self):
        r = execute(S(), [A(chain_id=8), A()], False)
        self.assertEqual([x["reason"] for x in r["authorization_trace"]], ["wrong_chain", None])
        self.assertEqual(r["after"]["delegate"], "A")

    def test_duplicate_nonce_rejected_after_first_use(self):
        r = execute(S(), [A(), A("B")], False)
        self.assertEqual(r["authorization_trace"][1]["reason"], "nonce_mismatch")
        self.assertEqual(r["after"]["delegate"], "A")

    def test_same_delegate_updates_nonce_without_pointer_change(self):
        r = execute(S(delegate="A"), [A()], False)
        self.assertEqual(r["after"]["nonce"], 1)
        self.assertFalse(r["reports"]["authority_always"]["net_delegate_changed"])
        self.assertEqual(r["reports"]["authority_always"]["ordered_pointer_changes"], [])

    def test_net_equal_keeps_ordered_changes(self):
        r = execute(S(delegate="A"), [A("B"), A("A", 1)], False)
        self.assertFalse(r["reports"]["authority_always"]["net_delegate_changed"])
        self.assertEqual(r["reports"]["authority_always"]["ordered_pointer_changes"], [
            {"tuple_index": 0, "from": "A", "to": "B"}, {"tuple_index": 1, "from": "B", "to": "A"}])
        self.assertEqual(r["after_authorizations"]["delegate"], "A")

    def test_invalid_schema_rejected_before_processing(self):
        for auths in [[], [A(), A(nonce=2**64)], [A(chain_id=-1)], [A(nonce=True)],
                      [A(signature_valid=1)], [A(delegate="unknown")]]:
            with self.subTest(auths=auths), self.assertRaises(ValueError):
                execute(S(), auths)
        for state in [S(nonce=-1), S(assets=-1), S(delegate="A", ordinary_code=True)]:
            with self.subTest(state=state), self.assertRaises(ValueError):
                execute(state, [A()])

    def test_nonce_limit_is_skip_not_whole_transaction_rejection(self):
        r = execute(S(), [A(nonce=MAX_NONCE), A()], False)
        self.assertEqual([x["reason"] for x in r["authorization_trace"]], ["nonce_limit", None])
        self.assertEqual(r["after"]["nonce"], 1)

    def test_inputs_immutable_and_repeatable(self):
        state, auths = S(), [A()]
        execute(state, auths, False, -7)
        self.assertEqual(state, S())
        self.assertEqual(auths, [A()])
        first, second = run(), run()
        self.assertEqual(json.dumps(first, sort_keys=True), json.dumps(second, sort_keys=True))
        self.assertEqual(evidence(first), evidence(second))


if __name__ == "__main__":
    unittest.main()
