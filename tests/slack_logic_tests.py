import json
import unittest

import slack_broker
import slack_logic


class FakeHelper:
    def __init__(self, configuration, settings, global_settings, events):
        self.settings = dict(settings)
        self.settings["configuration"] = dict(configuration)
        self.configuration = dict(configuration)
        self._events = list(events)
        self.search_name = settings.get("search_name")
        self.info = {}
        self.logs = []
        self._slack_broker_blob = {
            "settings": dict(global_settings),
            "proxy": {},
            "logging": {"loglevel": "INFO"},
        }

    def get_param(self, k):
        return self.configuration.get(k)

    def get_events(self):
        return iter(self._events)

    def addinfo(self):
        self.info = {"search_name": self.search_name}

    def log_info(self, m):
        self.logs.append(("info", m))

    def log_error(self, m):
        self.logs.append(("error", m))


TOKEN = "xoxb-1111-2222-secretvalue"
WEBHOOK = "https://hooks.slack.com/services/T00/B00/secretpath"


def make_helper(configuration=None, global_settings=None, events=None):
    cfg = {
        "channel": "#alerts",
        "message": "Alert fired",
        "attachment": "message",
    }
    if configuration:
        cfg.update(configuration)
    gs = {"slack_app_oauth_token": TOKEN, "from_user": "Splunk"}
    if global_settings is not None:
        gs = dict(global_settings)
    return FakeHelper(
        configuration=cfg,
        settings={"search_name": "My Alert", "results_link": "https://splunk/x"},
        global_settings=gs,
        events=events if events is not None else [{"host": "srv1"}],
    )


def build_message(helper):
    config = slack_logic._build_config(helper)
    payload = {
        "configuration": dict(config),
        "search_name": helper.search_name,
        "results_link": config.get("results_link", ""),
        "view_link": config.get("view_link", ""),
        "result": {},
    }
    events = list(helper.get_events())
    result = events[0] if events else {}
    payload["result"] = result
    return slack_logic._build_slack_message(config, payload, result, helper.search_name)


class TestIsSecretKey(unittest.TestCase):
    def test_secret_markers_match(t):
        for key in (
            "slack_app_oauth_token",
            "slack_app_oauth_token_override",
            "webhook_url",
            "webhook_url_override",
            "proxy_url_override",
            "password",
            "client_secret",
        ):
            t.assertTrue(slack_logic._is_secret_key(key), key)

    def test_case_insensitive(t):
        t.assertTrue(slack_logic._is_secret_key("SLACK_APP_OAUTH_TOKEN"))
        t.assertTrue(slack_logic._is_secret_key("Webhook_URL"))

    def test_non_secret_keys_not_matched(t):
        for key in ("channel", "message", "attachment", "fields", "from_user"):
            t.assertFalse(slack_logic._is_secret_key(key), key)


class TestSecretMasking(unittest.TestCase):
    def test_token_masked_when_template_references_it(t):
        helper = make_helper(
            configuration={
                "message": "leak {configuration.slack_app_oauth_token}",
                "attachment": "none",
            }
        )
        msg = build_message(helper)
        t.assertEqual(msg["text"], "leak ****")
        t.assertNotIn(TOKEN, json.dumps(msg))

    def test_override_token_masked(t):
        helper = make_helper(
            configuration={
                "slack_app_oauth_token_override": "xoxb-override-secret",
                "message": "t {configuration.slack_app_oauth_token_override}",
                "attachment": "none",
            }
        )
        msg = build_message(helper)
        t.assertEqual(msg["text"], "t ****")
        t.assertNotIn("xoxb-override-secret", json.dumps(msg))

    def test_webhook_url_masked(t):
        helper = make_helper(
            configuration={
                "message": "hook {configuration.webhook_url}",
                "attachment": "none",
            },
            global_settings={"webhook_url": WEBHOOK, "from_user": "Splunk"},
        )
        msg = build_message(helper)
        t.assertEqual(msg["text"], "hook ****")
        t.assertNotIn(WEBHOOK, json.dumps(msg))

    def test_token_never_in_rendered_output_via_attachment(t):
        helper = make_helper(
            configuration={
                "attachment": "message",
                "message": "{configuration.slack_app_oauth_token}",
            }
        )
        msg = build_message(helper)
        t.assertNotIn(TOKEN, json.dumps(msg))

    def test_nonsecret_config_value_not_masked(t):
        helper = make_helper(
            configuration={
                "message": "chan {configuration.channel}",
                "attachment": "none",
            }
        )
        msg = build_message(helper)
        t.assertEqual(msg["text"], "chan #alerts")


class TestBrokerFailure(unittest.TestCase):
    def test_broker_failure_returns_error_code_and_does_not_raise(t):
        helper = make_helper()
        delattr(helper, "_slack_broker_blob")

        real_fetch = slack_broker._fetch

        def boom(h):
            raise slack_broker.BrokerError(403, "cafebabe1234")

        slack_broker._fetch = boom
        try:
            status = slack_logic.process_event(helper)
        finally:
            slack_broker._fetch = real_fetch

        t.assertEqual(status, slack_logic.ERROR_CODE_BROKER_UNAVAILABLE)
        errors = [m for level, m in helper.logs if level == "error"]
        t.assertEqual(len(errors), 1)
        joined = " ".join(m for _, m in helper.logs)
        t.assertIn("403", joined)
        t.assertIn("cafebabe1234", joined)
        t.assertNotIn(TOKEN, joined)

    def test_broker_failure_without_correlation_id_logs_none(t):
        helper = make_helper()
        delattr(helper, "_slack_broker_blob")

        real_fetch = slack_broker._fetch

        def boom(h):
            raise slack_broker.BrokerError(503)

        slack_broker._fetch = boom
        try:
            status = slack_logic.process_event(helper)
        finally:
            slack_broker._fetch = real_fetch

        t.assertEqual(status, slack_logic.ERROR_CODE_BROKER_UNAVAILABLE)
        joined = " ".join(m for _, m in helper.logs)
        t.assertIn("status=503", joined)
        t.assertIn("correlation_id=none", joined)

    def test_unreachable_broker_returns_error_code_and_logs_no_exception_text(t):
        helper = make_helper()
        delattr(helper, "_slack_broker_blob")

        real_fetch = slack_broker._fetch

        def boom(h):
            raise RuntimeError(
                "Error connecting to /services/slack_credential: "
                "[Errno 111] Connection refused"
            )

        slack_broker._fetch = boom
        try:
            status = slack_logic.process_event(helper)
        finally:
            slack_broker._fetch = real_fetch

        t.assertEqual(status, slack_logic.ERROR_CODE_BROKER_UNAVAILABLE)
        errors = [m for level, m in helper.logs if level == "error"]
        t.assertEqual(len(errors), 1)
        t.assertIn("status=0", errors[0])
        t.assertIn("correlation_id=none", errors[0])
        t.assertNotIn("Errno 111", errors[0])
        t.assertNotIn("Unexpected error", errors[0])
        t.assertNotIn(TOKEN, " ".join(m for _, m in helper.logs))


PROXY_HOST = "recognisable-proxy.internal.example"


class FakeResponse:
    code = 200

    def read(self):
        return b"ok"


class TestProxyValidation(unittest.TestCase):
    def setUp(t):
        t.posted = []
        real_post = slack_logic._post

        def fake_post(helper, url, data, headers, proxy_uri):
            t.posted.append(proxy_uri)
            return FakeResponse()

        slack_logic._post = fake_post
        t.addCleanup(setattr, slack_logic, "_post", real_post)

    def run_with_proxy(t, stanza):
        helper = make_helper()
        helper._slack_broker_blob["proxy"] = dict(stanza)
        status = slack_logic.process_event(helper)
        return status, helper

    def proxy_logs(t, helper):
        return [m for _, m in helper.logs if "proxy" in m.lower()]

    def test_enabled_and_valid_proxy_delivers_through_that_proxy(t):
        status, helper = t.run_with_proxy(
            {"proxy_enabled": "1", "proxy_url": PROXY_HOST, "proxy_port": "3128"}
        )
        t.assertEqual(status, slack_logic.OK)
        t.assertEqual(t.posted, ["http://%s:3128" % PROXY_HOST])
        t.assertEqual(t.proxy_logs(helper), [])

    def test_disabled_proxy_delivers_directly(t):
        status, helper = t.run_with_proxy(
            {"proxy_enabled": "0", "proxy_url": PROXY_HOST, "proxy_port": "3128"}
        )
        t.assertEqual(status, slack_logic.OK)
        t.assertEqual(t.posted, [""])
        t.assertEqual(t.proxy_logs(helper), [])

    def test_absent_proxy_stanza_delivers_directly(t):
        status, helper = t.run_with_proxy({})
        t.assertEqual(status, slack_logic.OK)
        t.assertEqual(t.posted, [""])
        t.assertEqual(t.proxy_logs(helper), [])

    def test_enabled_with_an_empty_host_fails_without_delivering(t):
        status, helper = t.run_with_proxy(
            {"proxy_enabled": "1", "proxy_url": "", "proxy_port": "3128"}
        )
        t.assertEqual(status, slack_logic.ERROR_CODE_VALIDATION_FAILED)
        t.assertEqual(t.posted, [])

    def test_the_empty_host_emits_exactly_one_log_line_naming_the_host(t):
        _status, helper = t.run_with_proxy(
            {"proxy_enabled": "1", "proxy_url": "", "proxy_port": "3128"}
        )
        lines = t.proxy_logs(helper)
        t.assertEqual(len(lines), 1)
        t.assertIn("host", lines[0].lower())
        t.assertNotIn("port", lines[0].lower())

    def test_enabled_with_a_non_numeric_port_fails_without_delivering(t):
        status, helper = t.run_with_proxy(
            {"proxy_enabled": "1", "proxy_url": PROXY_HOST, "proxy_port": "notaport"}
        )
        t.assertEqual(status, slack_logic.ERROR_CODE_VALIDATION_FAILED)
        t.assertEqual(t.posted, [])

    def test_the_bad_port_emits_exactly_one_log_line_naming_the_port(t):
        _status, helper = t.run_with_proxy(
            {"proxy_enabled": "1", "proxy_url": PROXY_HOST, "proxy_port": "notaport"}
        )
        lines = t.proxy_logs(helper)
        t.assertEqual(len(lines), 1)
        t.assertIn("port", lines[0].lower())

    def test_enabled_with_an_absent_port_fails_like_the_developer_kit(t):
        status, helper = t.run_with_proxy(
            {"proxy_enabled": "1", "proxy_url": PROXY_HOST}
        )
        t.assertEqual(status, slack_logic.ERROR_CODE_VALIDATION_FAILED)
        t.assertEqual(t.posted, [])
        t.assertIn("port", t.proxy_logs(helper)[0].lower())

    def test_the_proxy_host_never_reaches_a_log_line(t):
        for stanza in (
            {"proxy_enabled": "1", "proxy_url": PROXY_HOST, "proxy_port": "notaport"},
            {"proxy_enabled": "1", "proxy_url": PROXY_HOST},
            {"proxy_enabled": "1", "proxy_url": PROXY_HOST, "proxy_port": "3128"},
        ):
            _status, helper = t.run_with_proxy(stanza)
            logged = " ".join(m for _, m in helper.logs)
            t.assertNotIn(PROXY_HOST, logged)
            t.assertNotIn("3128", logged)
            t.assertNotIn("notaport", logged)

    def test_the_proxy_port_value_never_reaches_a_log_line(t):
        _status, helper = t.run_with_proxy(
            {"proxy_enabled": "1", "proxy_url": PROXY_HOST, "proxy_port": "8888bad"}
        )
        t.assertNotIn("8888bad", " ".join(m for _, m in helper.logs))

    def test_a_broken_proxy_does_not_raise_out_of_process_event(t):
        status, _helper = t.run_with_proxy(
            {"proxy_enabled": "1", "proxy_url": "", "proxy_port": ""}
        )
        t.assertEqual(status, slack_logic.ERROR_CODE_VALIDATION_FAILED)

    def test_a_broken_proxy_beats_a_missing_webhook_to_the_single_log_line(t):
        helper = make_helper(global_settings={"from_user": "Splunk"})
        helper._slack_broker_blob["proxy"] = {"proxy_enabled": "1", "proxy_url": ""}
        status = slack_logic.process_event(helper)
        t.assertEqual(status, slack_logic.ERROR_CODE_VALIDATION_FAILED)
        t.assertEqual(len(t.proxy_logs(helper)), 1)
        t.assertEqual(t.posted, [])


PROXY_USER = "puser"
PROXY_PASSWORD = "ppass"
AWKWARD_PASSWORD = "p@ss/word"


class TestProxyCredentialPassthrough(unittest.TestCase):
    def setUp(t):
        t.posted = []
        t.bodies = []
        real_post = slack_logic._post

        def fake_post(helper, url, data, headers, proxy_uri):
            t.posted.append(proxy_uri)
            t.bodies.append(data)
            return FakeResponse()

        slack_logic._post = fake_post
        t.addCleanup(setattr, slack_logic, "_post", real_post)

    def run_with_proxy(t, stanza, configuration=None):
        helper = make_helper(configuration=configuration)
        helper._slack_broker_blob["proxy"] = dict(stanza)
        status = slack_logic.process_event(helper)
        return status, helper

    def test_credentialed_stanza_authenticates_through_the_proxy(t):
        status, _helper = t.run_with_proxy(
            {
                "proxy_enabled": "1",
                "proxy_url": "proxy.example.com",
                "proxy_port": "8080",
                "proxy_username": PROXY_USER,
                "proxy_password": PROXY_PASSWORD,
                "proxy_type": "https",
            }
        )
        t.assertEqual(status, slack_logic.OK)
        t.assertEqual(t.posted, ["https://puser:ppass@proxy.example.com:8080"])

    def test_proxy_type_selects_the_scheme(t):
        _status, _helper = t.run_with_proxy(
            {
                "proxy_enabled": "1",
                "proxy_url": "proxy.example.com",
                "proxy_port": "8080",
                "proxy_type": "https",
            }
        )
        t.assertEqual(t.posted, ["https://proxy.example.com:8080"])

    def test_absent_proxy_type_still_defaults_to_http(t):
        _status, _helper = t.run_with_proxy(
            {
                "proxy_enabled": "1",
                "proxy_url": "proxy.example.com",
                "proxy_port": "8080",
            }
        )
        t.assertEqual(t.posted, ["http://proxy.example.com:8080"])

    def test_a_password_needing_percent_encoding_is_encoded(t):
        _status, _helper = t.run_with_proxy(
            {
                "proxy_enabled": "1",
                "proxy_url": "proxy.example.com",
                "proxy_port": "8080",
                "proxy_username": PROXY_USER,
                "proxy_password": AWKWARD_PASSWORD,
            }
        )
        t.assertEqual(len(t.posted), 1)
        t.assertIn("p%40ss%2Fword", t.posted[0])
        t.assertNotIn(AWKWARD_PASSWORD, t.posted[0])

    def test_the_alert_configuration_holds_no_proxy_setting(t):
        helper = make_helper()
        helper._slack_broker_blob["proxy"] = {
            "proxy_enabled": "1",
            "proxy_url": "proxy.example.com",
            "proxy_port": "8080",
            "proxy_username": PROXY_USER,
            "proxy_password": PROXY_PASSWORD,
        }
        config = slack_logic._build_config(helper)
        t.assertEqual(
            [k for k in config if k.startswith("proxy")], ["proxy_url_override"]
        )
        rendered = json.dumps(config)
        for value in ("proxy.example.com", PROXY_USER, PROXY_PASSWORD, "8080"):
            t.assertNotIn(value, rendered, value)

    def test_the_proxy_password_reaches_no_log_line_and_no_slack_payload(t):
        for password in (PROXY_PASSWORD, AWKWARD_PASSWORD):
            t.posted = []
            t.bodies = []
            _status, helper = t.run_with_proxy(
                {
                    "proxy_enabled": "1",
                    "proxy_url": "proxy.example.com",
                    "proxy_port": "8080",
                    "proxy_username": PROXY_USER,
                    "proxy_password": password,
                },
                configuration={
                    "message": "{configuration} {configuration.proxy_password}",
                    "attachment": "message",
                    "fields": "*",
                },
            )
            logged = " ".join(m for _, m in helper.logs)
            t.assertNotIn(password, logged, password)
            t.assertEqual(len(t.bodies), 1)
            t.assertNotIn(password, t.bodies[0], password)

    def test_the_proxy_uri_reaches_no_log_line_and_no_slack_payload(t):
        _status, helper = t.run_with_proxy(
            {
                "proxy_enabled": "1",
                "proxy_url": "proxy.example.com",
                "proxy_port": "8080",
                "proxy_username": PROXY_USER,
                "proxy_password": PROXY_PASSWORD,
            },
            configuration={"message": "{configuration}", "attachment": "message"},
        )
        logged = " ".join(m for _, m in helper.logs)
        for fragment in ("proxy.example.com", PROXY_USER, "8080"):
            t.assertNotIn(fragment, logged, fragment)
            t.assertNotIn(fragment, t.bodies[0], fragment)


if __name__ == "__main__":
    unittest.main()
