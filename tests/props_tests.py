import configparser
import datetime
import os
import re
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROPS = os.path.join(ROOT, "package", "default", "props.conf")
LOG_DIR = "/opt/splunk/var/log/splunk/"


def source_pattern(stanza):
    pattern = stanza[len("source::") :]
    parts = []
    index = 0
    while index < len(pattern):
        if pattern.startswith("...", index):
            parts.append(".*")
            index += 3
        elif pattern[index] == "*":
            parts.append(r"[^/\\]*")
            index += 1
        else:
            parts.append(re.escape(pattern[index]))
            index += 1
    return re.compile("^" + "".join(parts) + "$")


TRACEBACK_RUN = (
    "2026-10-12 13:58:39,871 log_level=ERROR pid=24087 tid=MainThread "
    'file=cim_actions.py:message:467 | sendmodaction - signature="Unexpected error: '
    "Traceback (most recent call last):\n"
    '  File "/opt/splunk/etc/apps/slack_alerts/bin/slack.py", line 57, in process_event\n'
    "    status = slack_logic.process_event(self, *args, **kwargs)\n"
    'KeyError: \'channel\'\n." action_name="slack" action_status="failure"\n'
    "2026-10-12 13:58:39,872 log_level=ERROR pid=24087 tid=MainThread "
    "file=cim_actions.py:message:467 | sendmodaction - "
    'signature="Slack alert action failed with code 5" action_name="slack"\n'
)


def load_props():
    props = configparser.ConfigParser(interpolation=None)
    props.optionxform = str
    props.read(PROPS)
    return props


def break_events(stanza, data):
    breaker = re.compile(stanza["LINE_BREAKER"])
    events = []
    start = 0
    for match in breaker.finditer(data):
        events.append(data[start : match.start(1)])
        start = match.end(1)
    events.append(data[start:])
    return [event for event in events if event.strip()]


def event_time(stanza, event):
    window = event[: int(stanza["MAX_TIMESTAMP_LOOKAHEAD"])]
    assert re.match(stanza["TIME_PREFIX"], window)
    python_format = stanza["TIME_FORMAT"].replace("%3N", "%f")
    return datetime.datetime.strptime(window, python_format)


def sourcetype_for(path):
    props = load_props()
    return [
        props[stanza].get("sourcetype")
        for stanza in props.sections()
        if stanza.startswith("source::") and source_pattern(stanza).match(path)
    ]


class LogSourcetypeTests(unittest.TestCase):
    def test_the_alert_log_is_sourcetyped(self):
        self.assertEqual(
            sourcetype_for(LOG_DIR + "slack_alerts_alert.log"), ["slack_alerts:log"]
        )

    def test_a_rotated_alert_log_keeps_the_sourcetype(self):
        self.assertEqual(
            sourcetype_for(LOG_DIR + "slack_alerts_alert.log.1"), ["slack_alerts:log"]
        )

    def test_the_broker_log_is_sourcetyped(self):
        self.assertEqual(
            sourcetype_for(LOG_DIR + "slack_alerts_credential_broker.log"),
            ["slack_alerts:log"],
        )

    def test_another_apps_log_is_left_alone(self):
        self.assertEqual(sourcetype_for(LOG_DIR + "splunk_ta_aws_sqs.log"), [])


class LogParsingTests(unittest.TestCase):
    def setUp(self):
        props = load_props()
        self.assertIn("slack_alerts:log", props)
        self.stanza = props["slack_alerts:log"]

    def test_a_traceback_stays_inside_its_event(self):
        events = break_events(self.stanza, TRACEBACK_RUN)
        self.assertEqual(len(events), 2)
        self.assertIn("KeyError: 'channel'", events[0])
        self.assertTrue(events[1].startswith("2026-10-12 13:58:39,872"))

    def test_the_timestamp_parses_to_the_millisecond(self):
        event = break_events(self.stanza, TRACEBACK_RUN)[0]
        self.assertEqual(
            event_time(self.stanza, event),
            datetime.datetime(2026, 10, 12, 13, 58, 39, 871000),
        )


if __name__ == "__main__":
    unittest.main()
