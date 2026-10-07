import json
import unittest

import slack_broker


class FakeHelper:
    def __init__(self, blob):
        self._slack_broker_blob = blob
        self.session_key = "unused"
        self.logs = []

    def log_error(self, message):
        self.logs.append(message)


class FakeResponse:
    def __init__(self, status):
        self.status = status


def helper_with(settings=None, proxy=None, logging=None):
    blob = {}
    if settings is not None:
        blob["settings"] = settings
    if proxy is not None:
        blob["proxy"] = proxy
    if logging is not None:
        blob["logging"] = logging
    return FakeHelper(blob)


class AllowlistTests(unittest.TestCase):
    def test_allowlist_names_twelve_keys(self):
        names = [k for keys in slack_broker.ALLOWLIST.values() for k in keys]
        self.assertEqual(len(names), 12)

    def test_allowlist_excludes_framework_keys(self):
        names = [k for keys in slack_broker.ALLOWLIST.values() for k in keys]
        for unwanted in ("eai:acl", "eai:appName", "eai:userName", "disabled"):
            self.assertNotIn(unwanted, names)


class SettingTests(unittest.TestCase):
    def test_returns_value_for_allowlisted_key(self):
        helper = helper_with(settings={"webhook_url": "https://hooks.example.com/x"})
        self.assertEqual(
            slack_broker.setting(helper, "webhook_url"), "https://hooks.example.com/x"
        )

    def test_returns_none_for_absent_key(self):
        helper = helper_with(settings={})
        self.assertIsNone(slack_broker.setting(helper, "webhook_url"))

    def test_returns_none_when_stanza_absent(self):
        helper = helper_with()
        self.assertIsNone(slack_broker.setting(helper, "webhook_url"))

    def test_withholds_key_the_allowlist_does_not_name(self):
        helper = helper_with(
            settings={"proxy_password": "s3cret", "webhook_url": "https://h/x"}
        )
        self.assertIsNone(slack_broker.setting(helper, "proxy_password"))
        self.assertEqual(slack_broker.setting(helper, "webhook_url"), "https://h/x")


class ProxyTests(unittest.TestCase):
    def test_returns_empty_when_disabled(self):
        helper = helper_with(
            proxy={
                "proxy_enabled": "0",
                "proxy_url": "p.example.com",
                "proxy_port": "8080",
            }
        )
        self.assertEqual(slack_broker.proxy(helper), {})

    def test_returns_shape_when_enabled(self):
        helper = helper_with(
            proxy={
                "proxy_enabled": "1",
                "proxy_url": "p.example.com",
                "proxy_port": "8080",
            }
        )
        result = slack_broker.proxy(helper)
        self.assertEqual(result["proxy_url"], "p.example.com")
        self.assertEqual(result["proxy_port"], "8080")

    def test_returns_empty_when_stanza_absent(self):
        helper = helper_with()
        self.assertEqual(slack_broker.proxy(helper), {})

    def test_accepts_truthy_spellings(self):
        for enabled in ("1", "true", "True", "yes", "YES", "t", "y"):
            helper = helper_with(
                proxy={"proxy_enabled": enabled, "proxy_url": "p", "proxy_port": "1"}
            )
            self.assertNotEqual(slack_broker.proxy(helper), {}, enabled)

    def test_rejects_spellings_the_developer_kit_rejects(self):
        for disabled in ("on", "enabled", "0", "false", "no", "", "2"):
            helper = helper_with(
                proxy={"proxy_enabled": disabled, "proxy_url": "p", "proxy_port": "1"}
            )
            self.assertEqual(slack_broker.proxy(helper), {}, disabled)

    def test_surrounding_whitespace_is_stripped_like_the_developer_kit(self):
        helper = helper_with(
            proxy={"proxy_enabled": " 1 ", "proxy_url": "p", "proxy_port": "1"}
        )
        self.assertNotEqual(slack_broker.proxy(helper), {})

    def test_hand_written_credentials_pass_through(self):
        helper = helper_with(
            proxy={
                "proxy_enabled": "1",
                "proxy_url": "proxy.example.com",
                "proxy_port": "8080",
                "proxy_username": "puser",
                "proxy_password": "ppass",
            }
        )
        result = slack_broker.proxy(helper)
        self.assertEqual(result["proxy_username"], "puser")
        self.assertEqual(result["proxy_password"], "ppass")

    def test_hand_written_proxy_type_passes_through(self):
        helper = helper_with(
            proxy={
                "proxy_enabled": "1",
                "proxy_url": "proxy.example.com",
                "proxy_port": "8080",
                "proxy_type": "https",
            }
        )
        self.assertEqual(slack_broker.proxy(helper)["proxy_type"], "https")

    def test_hand_written_proxy_rdns_passes_through(self):
        helper = helper_with(
            proxy={
                "proxy_enabled": "1",
                "proxy_url": "proxy.example.com",
                "proxy_port": "8080",
                "proxy_rdns": "1",
            }
        )
        self.assertEqual(slack_broker.proxy(helper)["proxy_rdns"], "1")

    def test_stanza_without_the_optional_keys_keeps_the_shipped_defaults(self):
        helper = helper_with(proxy={"proxy_enabled": "1"})
        self.assertEqual(
            slack_broker.proxy(helper),
            {
                "proxy_url": "",
                "proxy_port": None,
                "proxy_username": "",
                "proxy_password": "",
                "proxy_type": "",
                "proxy_rdns": None,
            },
        )


class LogLevelTests(unittest.TestCase):
    def test_returns_configured_level(self):
        helper = helper_with(logging={"loglevel": "DEBUG"})
        self.assertEqual(slack_broker.log_level(helper), "DEBUG")

    def test_falls_back_to_info_when_absent(self):
        helper = helper_with()
        self.assertEqual(slack_broker.log_level(helper), "INFO")

    def test_falls_back_to_info_when_empty(self):
        helper = helper_with(logging={"loglevel": ""})
        self.assertEqual(slack_broker.log_level(helper), "INFO")


class CacheTests(unittest.TestCase):
    def setUp(self):
        self.real_fetch = slack_broker._fetch
        self.calls = []

    def tearDown(self):
        slack_broker._fetch = self.real_fetch

    def _seam(self, status, payload):
        def fetch(helper):
            self.calls.append(helper)
            return FakeResponse(status), json.dumps(payload)

        slack_broker._fetch = fetch

    def _raw_seam(self, status, content):
        def fetch(helper):
            self.calls.append(helper)
            return FakeResponse(status), content

        slack_broker._fetch = fetch

    def _failing_seam(self, exc):
        def fetch(helper):
            self.calls.append(helper)
            raise exc

        slack_broker._fetch = fetch

    def _unseeded_helper(self):
        helper = FakeHelper({})
        delattr(helper, "_slack_broker_blob")
        return helper

    def test_fetches_once_and_caches_on_the_helper(self):
        self._seam(200, {"stanzas": {"settings": {"webhook_url": "https://h/x"}}})
        helper = FakeHelper({})
        delattr(helper, "_slack_broker_blob")
        first = slack_broker.get_blob(helper)
        second = slack_broker.get_blob(helper)
        self.assertIs(first, second)
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(first["settings"]["webhook_url"], "https://h/x")

    def test_non_200_raises_broker_error_with_status_and_correlation_id(self):
        self._seam(403, {"error": "internal", "correlation_id": "abc123def456"})
        helper = FakeHelper({})
        delattr(helper, "_slack_broker_blob")
        with self.assertRaises(slack_broker.BrokerError) as caught:
            slack_broker.get_blob(helper)
        self.assertEqual(caught.exception.status, 403)
        self.assertEqual(caught.exception.correlation_id, "abc123def456")
        self.assertFalse(hasattr(helper, "_slack_broker_blob"))

    def test_broker_error_text_carries_no_payload(self):
        err = slack_broker.BrokerError(500, "deadbeef")
        self.assertEqual(str(err), "broker call failed")

    def test_unreachable_management_port_raises_broker_error(self):
        class SplunkdConnectionException(Exception):
            pass

        self._failing_seam(
            SplunkdConnectionException(
                "Error connecting to /services/slack_credential: "
                "[Errno 111] Connection refused"
            )
        )
        helper = self._unseeded_helper()
        with self.assertRaises(slack_broker.BrokerError) as caught:
            slack_broker.get_blob(helper)
        self.assertEqual(caught.exception.status, slack_broker.STATUS_NO_RESPONSE)
        self.assertIsNone(caught.exception.correlation_id)
        self.assertEqual(str(caught.exception), "broker call failed")
        self.assertFalse(hasattr(helper, "_slack_broker_blob"))

    def test_converted_failure_suppresses_the_original_traceback(self):
        self._failing_seam(RuntimeError("[Errno 111] Connection refused"))
        helper = self._unseeded_helper()
        try:
            slack_broker.get_blob(helper)
        except slack_broker.BrokerError as exc:
            self.assertTrue(exc.__suppress_context__)
            self.assertIsNone(exc.__cause__)
            self.assertNotIn("Errno 111", str(exc))
        else:
            self.fail("get_blob did not raise BrokerError")

    def test_helper_without_session_key_raises_broker_error(self):
        self._failing_seam(
            AttributeError("'FakeHelper' object has no attribute 'session_key'")
        )
        helper = self._unseeded_helper()
        with self.assertRaises(slack_broker.BrokerError) as caught:
            slack_broker.get_blob(helper)
        self.assertEqual(caught.exception.status, slack_broker.STATUS_NO_RESPONSE)

    def test_malformed_success_body_raises_broker_error(self):
        self._raw_seam(200, "<html>login</html>")
        helper = self._unseeded_helper()
        with self.assertRaises(slack_broker.BrokerError) as caught:
            slack_broker.get_blob(helper)
        self.assertEqual(caught.exception.status, slack_broker.STATUS_NO_RESPONSE)
        self.assertIsNone(caught.exception.correlation_id)
        self.assertFalse(hasattr(helper, "_slack_broker_blob"))

    def test_non_200_status_survives_the_conversion(self):
        self._raw_seam(403, "not json either")
        helper = self._unseeded_helper()
        with self.assertRaises(slack_broker.BrokerError) as caught:
            slack_broker.get_blob(helper)
        self.assertEqual(caught.exception.status, 403)
        self.assertIsNone(caught.exception.correlation_id)


if __name__ == "__main__":
    unittest.main()
