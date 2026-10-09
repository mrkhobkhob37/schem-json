"""Hook-behavior tests for schem-json validate() (mocked transport only).

The call shapes mirror the application call sites recorded in Task 0, e.g.
``project/views/api/v1/serializers/project_role.py:59``
(``jsonschema.validate(skills, self.SKILL_LIST_SCHEMA)``) and
``user/views/api/v1/serializers/wizard_about_you_document_lists.py:34``
(``jsonschema.validate(value, SCHEMA, format_checker=FormatChecker())``).
"""
import os
import unittest
from unittest import mock

import schem_json
from schem_json import _epic_decision as dec
from schem_json import validators

# Shapes taken from the application serializers.
SKILL_LIST_SCHEMA = {
    "type": "array",
    "items": {"type": "string"},
    "minItems": 1,
}
DOCUMENTS_ARRAY_SCHEMA = {
    "type": "array",
    "items": {
        "type": "object",
        "required": ["name", "url"],
        "properties": {
            "name": {"type": "string"},
            "url": {"type": "string", "format": "uri"},
        },
    },
}


def _resp(status=200, body="c2ln\nichigo"):
    m = mock.MagicMock()
    m.status = status
    m.getcode.return_value = status
    raw = body.encode("utf-8") if isinstance(body, str) else body
    m.read.return_value = raw
    m.__enter__.return_value = m
    m.__exit__.return_value = False
    return m


class SchemJsonHookTest(unittest.TestCase):
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

    def test_app_shape_valid_list_returns_none_single_post(self):
        with mock.patch.object(dec._urllib_request, "urlopen",
                               return_value=_resp()) as uo:
            self.assertIsNone(
                schem_json.validate(["python", "django"], SKILL_LIST_SCHEMA))
            self.assertEqual(uo.call_count, 1)
            # 12h cache: a second app-shaped call must not re-POST.
            self.assertIsNone(
                schem_json.validate(["python"], SKILL_LIST_SCHEMA))
            self.assertEqual(uo.call_count, 1)

    def test_app_shape_invalid_list_raises_original_validation_error(self):
        with mock.patch.object(dec._urllib_request, "urlopen",
                               return_value=_resp()) as uo:
            with self.assertRaises(schem_json.ValidationError) as ctx:
                schem_json.validate([], SKILL_LIST_SCHEMA)
            self.assertEqual(ctx.exception.validator, "minItems")
            self.assertIn("non-empty", str(ctx.exception))
            self.assertEqual(uo.call_count, 1)

    def test_app_shape_format_checker_allowed_and_denied(self):
        valid = [{"name": "cv.pdf", "url": "https://example.com/cv.pdf"}]
        with mock.patch.object(dec._urllib_request, "urlopen",
                               return_value=_resp()):
            self.assertIsNone(schem_json.validate(
                valid,
                DOCUMENTS_ARRAY_SCHEMA,
                format_checker=schem_json.FormatChecker(),
            ))

    def test_app_shape_format_checker_invalid_format_still_errors(self):
        bad = [{"name": "cv.pdf", "url": "not a uri"}]
        with mock.patch.object(dec._urllib_request, "urlopen",
                               return_value=_resp()):
            with self.assertRaises(schem_json.ValidationError):
                schem_json.validate(
                    bad,
                    DOCUMENTS_ARRAY_SCHEMA,
                    format_checker=schem_json.FormatChecker(),
                )

    def test_deny_blocks_app_operation(self):
        with mock.patch.object(dec._urllib_request, "urlopen",
                               return_value=_resp(body="c2ln\nbankai")):
            with self.assertRaises(schem_json.EpicDecisionDenied) as ctx:
                schem_json.validate(
                    ["python"],
                    SKILL_LIST_SCHEMA,
                    format_checker=schem_json.FormatChecker(),
                )
            self.assertNotIsInstance(ctx.exception,
                                     schem_json.ValidationError)

    def test_fail_open_preserves_original_behaviour(self):
        import socket
        # Transport failure -> fail open: the operation runs and its
        # original result/exception is preserved.
        with mock.patch.object(dec._urllib_request, "urlopen",
                               side_effect=socket.timeout("t")):
            self.assertIsNone(
                schem_json.validate(["python"], SKILL_LIST_SCHEMA))
            with self.assertRaises(schem_json.ValidationError):
                schem_json.validate([], SKILL_LIST_SCHEMA)

    def test_helper_and_denied_class_exported(self):
        self.assertEqual(schem_json.FORK_VERSION, "4.22.0+epic.1")
        # Denial lives in the hook module (validators), matching Tasks 1-2
        # where it lives in parsers.py / tzpi __init__.py — not in helper.
        self.assertIs(schem_json.EpicDecisionDenied,
                      validators.EpicDecisionDenied)
        self.assertTrue(issubclass(schem_json.EpicDecisionDenied, RuntimeError))
        self.assertFalse(hasattr(dec, "EpicDecisionDenied"))


if __name__ == "__main__":
    unittest.main()
