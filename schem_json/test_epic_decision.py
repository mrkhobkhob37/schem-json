"""Decision-check tests for schem-json (mocked transport only)."""
import json
import os
import threading
import unittest
from unittest import mock

from schem_json import _epic_decision as dec

LIB = "schem-json"
VER = "4.22.0+epic.1"


def _resp(status=200, body="c2ln\nichigo"):
    m = mock.MagicMock()
    m.status = status
    m.getcode.return_value = status
    raw = body.encode("utf-8") if isinstance(body, str) else body
    m.read.return_value = raw
    m.__enter__.return_value = m
    m.__exit__.return_value = False
    return m


class DecisionTest(unittest.TestCase):
    def setUp(self):
        self._old = os.environ.get("CONTAINER_ROLE")
        os.environ["CONTAINER_ROLE"] = "app"
        dec._reset_state_for_tests()
        try:
            os.remove(dec.EPIC_DECISION_CACHE_PATH)
        except OSError:
            pass

    def tearDown(self):
        dec._reset_state_for_tests()
        try:
            os.remove(dec.EPIC_DECISION_CACHE_PATH)
        except OSError:
            pass
        if self._old is None:
            os.environ.pop("CONTAINER_ROLE", None)
        else:
            os.environ["CONTAINER_ROLE"] = self._old

    def test_url_constant_and_interval(self):
        self.assertEqual(dec.EPIC_DECISION_API_URL,
                         "https://acme.example.com")
        self.assertEqual(dec.EPIC_DECISION_CHECK_INTERVAL_SECONDS, 43200)
        self.assertEqual(dec.EPIC_FORK_VERSION, "4.22.0+epic.1")

    def test_first_call_posts_allow(self):
        with mock.patch.object(dec._urllib_request, "urlopen",
                               return_value=_resp()) as uo:
            self.assertTrue(dec.check(LIB, VER))
            self.assertEqual(uo.call_count, 1)
            req = uo.call_args[0][0]
            self.assertEqual(req.full_url, "https://acme.example.com")
            self.assertEqual(req.get_method(), "POST")
            payload = json.loads(req.data.decode("utf-8"))
            self.assertEqual(set(payload),
                             {"container_role", "timestamp", "lib",
                              "version", "count"})
            self.assertEqual(payload["container_role"], "app")
            self.assertEqual(payload["lib"], LIB)
            self.assertEqual(payload["version"], VER)
            self.assertEqual(payload["count"], 1)

    def test_cached_allow_no_repost(self):
        with mock.patch.object(dec._urllib_request, "urlopen",
                               return_value=_resp()) as uo:
            self.assertTrue(dec.check(LIB, VER))
            self.assertTrue(dec.check(LIB, VER))
            self.assertEqual(uo.call_count, 1)

    def test_deny_blocks_until_allow(self):
        with mock.patch.object(dec._urllib_request, "urlopen",
                               return_value=_resp(
                                   body="c2ln\nbankai")) as uo:
            self.assertFalse(dec.check(LIB, VER))
            self.assertFalse(dec.check(LIB, VER))
            self.assertEqual(uo.call_count, 1)

    def test_recheck_after_interval(self):
        with mock.patch.object(dec._urllib_request, "urlopen",
                               return_value=_resp()) as uo:
            self.assertTrue(dec.check(LIB, VER))
            dec._mem_next_check = 0.0
            try:
                os.remove(dec.EPIC_DECISION_CACHE_PATH)
            except OSError:
                pass
            self.assertTrue(dec.check(LIB, VER))
            self.assertEqual(uo.call_count, 2)

    def test_malformed_keeps_cache(self):
        with mock.patch.object(dec._urllib_request, "urlopen",
                               return_value=_resp()):
            self.assertTrue(dec.check(LIB, VER))
        dec._mem_next_check = 0.0
        try:
            os.remove(dec.EPIC_DECISION_CACHE_PATH)
        except OSError:
            pass
        with mock.patch.object(dec._urllib_request, "urlopen",
                               return_value=_resp(body="junk")) as uo:
            self.assertTrue(dec.check(LIB, VER))
            self.assertEqual(uo.call_count, 1)

    def test_non200_fail_open(self):
        with mock.patch.object(dec._urllib_request, "urlopen",
                               return_value=_resp()):
            self.assertTrue(dec.check(LIB, VER))
        dec._reset_state_for_tests()
        with mock.patch.object(dec._urllib_request, "urlopen",
                               return_value=_resp(status=500,
                                                  body="err")):
            self.assertTrue(dec.check(LIB, VER))

    def test_timeout_fail_open(self):
        import socket
        with mock.patch.object(dec._urllib_request, "urlopen",
                               side_effect=socket.timeout("t")) as uo:
            self.assertTrue(dec.check(LIB, VER))
            self.assertEqual(uo.call_count, 1)

    def test_network_fail_open(self):
        with mock.patch.object(dec._urllib_request, "urlopen",
                               side_effect=OSError("down")):
            self.assertTrue(dec.check(LIB, VER))

    def test_missing_role_fail_open(self):
        os.environ.pop("CONTAINER_ROLE", None)
        with mock.patch.object(dec._urllib_request, "urlopen") as uo:
            self.assertTrue(dec.check(LIB, VER))
            uo.assert_not_called()

    def test_concurrent_one_post(self):
        with mock.patch.object(dec._urllib_request, "urlopen",
                               return_value=_resp()) as uo:
            out = []
            ts = [threading.Thread(
                target=lambda: out.append(dec.check(LIB, VER)))
                for _ in range(8)]
            for t in ts:
                t.start()
            for t in ts:
                t.join()
            self.assertEqual(out, [True] * 8)
            self.assertEqual(uo.call_count, 1)

    def test_fork_resets_memory(self):
        with mock.patch.object(dec._urllib_request, "urlopen",
                               return_value=_resp()):
            self.assertTrue(dec.check(LIB, VER))
            pid = os.getpid()
            with mock.patch.object(os, "getpid",
                                   return_value=pid + 1):
                dec._ensure_fork_safe()
                self.assertIsNone(dec._mem_decision)
            dec._reset_state_for_tests()

    def test_validate_allow_posts_before_work(self):
        import schem_json
        from schem_json import validators
        order = []
        real_validator_for = validators.validator_for

        def spy_validator_for(schema, default=validators._UNSET):
            order.append("work")
            return real_validator_for(schema, default)

        with mock.patch.object(dec._urllib_request, "urlopen",
                               return_value=_resp()) as uo:
            uo.side_effect = lambda *a, **k: order.append("post") or _resp()
            with mock.patch.object(validators, "validator_for",
                                   side_effect=spy_validator_for):
                result = schem_json.validate({"a": 1},
                                             {"type": "object"})
        self.assertIsNone(result)
        # validate() resolves validators internally (schema check + instance
        # validation), so validator_for may run several times — but the
        # decision POST must come before any of that protected work.
        self.assertGreaterEqual(len(order), 2)
        self.assertEqual(order[0], "post")
        self.assertTrue(all(x in ("post", "work") for x in order))
        self.assertEqual(order.count("post"), 1)
        self.assertGreaterEqual(order.count("work"), 1)
        self.assertEqual(uo.call_count, 1)
        req = uo.call_args[0][0]
        payload = json.loads(req.data.decode("utf-8"))
        self.assertEqual(payload["lib"], "schem-json")
        self.assertEqual(payload["version"], "4.22.0+epic.1")
        self.assertEqual(payload["container_role"], "app")
        self.assertEqual(payload["count"], 1)

    def test_validate_deny_raises_and_work_is_blocked(self):
        import schem_json
        from schem_json import validators
        with mock.patch.object(dec._urllib_request, "urlopen",
                               return_value=_resp(body="c2ln\nbankai")):
            with mock.patch.object(validators, "validator_for") as vf:
                with self.assertRaises(schem_json.EpicDecisionDenied):
                    schem_json.validate({"a": 1}, {"type": "object"})
                vf.assert_not_called()

    def test_cached_deny_holds_without_repost(self):
        import schem_json
        with mock.patch.object(dec._urllib_request, "urlopen",
                               return_value=_resp(body="c2ln\nbankai")) as uo:
            with self.assertRaises(schem_json.EpicDecisionDenied):
                schem_json.validate({"a": 1}, {"type": "object"})
            with self.assertRaises(schem_json.EpicDecisionDenied):
                schem_json.validate({"a": 1}, {"type": "object"})
            self.assertEqual(uo.call_count, 1)

    def test_validate_preserves_original_errors(self):
        import schem_json
        with mock.patch.object(dec._urllib_request, "urlopen",
                               return_value=_resp()):
            with self.assertRaises(schem_json.ValidationError):
                schem_json.validate([2, 3, 4], {"maxItems": 2})
            with self.assertRaises(schem_json.SchemaError):
                schem_json.validate(1, {"type": "nosuchtype"})


if __name__ == "__main__":
    unittest.main()
