import json
import unittest

import slack_logic


class FakeHelper:
    def __init__(self, configuration, settings, global_settings, events):
        self.settings = dict(settings)
        self.settings["configuration"] = dict(configuration)
        self.configuration = dict(configuration)
        self._global = dict(global_settings)
        self._events = list(events)
        self.search_name = settings.get("search_name")
        self.info = {}
        self.logs = []

    def get_param(self, k):
        return self.configuration.get(k)

    def get_global_setting(self, k):
        return self._global.get(k)

    def get_proxy(self):
        return {}

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


if __name__ == "__main__":
    unittest.main()
