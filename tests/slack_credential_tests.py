import __main__
import importlib.util
import inspect
import json
import logging
import os
import re
import shutil
import sys
import tempfile
import types
import unittest

MANAGEMENT_URI = "https://127.0.0.1:8089"
CO_RESIDENT_MAIN_FILE = "/opt/splunk/etc/apps/other_app/bin/other_handler.py"
ENDPOINT = object()
CORRELATION_ID = re.compile(r"^[0-9a-f]{12}$")

LOGGER_NAMES = []
LOGGED_EVENTS = []


class FakeEntity:
    def __init__(self, name, content):
        self.name = name
        self.content = content


class FakeRestHandler:
    entities = {}
    raises = {}
    constructed = []
    calls = []
    main_files = []

    def __init__(self, splunkd_uri, session_key, endpoint):
        FakeRestHandler.constructed.append((splunkd_uri, session_key, endpoint))
        FakeRestHandler.main_files.append(getattr(__main__, "__file__", None))

    def get(self, name, decrypt=False):
        FakeRestHandler.calls.append((name, decrypt))
        if name in FakeRestHandler.raises:
            raise FakeRestHandler.raises[name]
        for entity in FakeRestHandler.entities.get(name, []):
            yield entity

    @classmethod
    def reset(cls):
        cls.entities = {}
        cls.raises = {}
        cls.constructed = []
        cls.calls = []
        cls.main_files = []


class FakeRestCredentials:
    PASSWORD = "******"
    LEGACY_PASSWORD = "********"

    @classmethod
    def is_placeholder(cls, value):
        if not isinstance(value, str):
            raise TypeError("is_placeholder takes a string")
        return value in (cls.PASSWORD, cls.LEGACY_PASSWORD)


def _fake_module(name):
    module = types.ModuleType(name)
    sys.modules[name] = module
    return module


def _fake_log_event(logger, key_values, log_level=logging.INFO):
    LOGGED_EVENTS.append((dict(key_values), log_level))


def _events(action):
    return [(e, lvl) for e, lvl in LOGGED_EVENTS if e.get("action") == action]


def _install_fakes():
    _fake_module("import_declare_test")

    splunk = _fake_module("splunk")
    persistconn = _fake_module("splunk.persistconn")
    application = _fake_module("splunk.persistconn.application")

    class PersistentServerConnectionApplication:
        def __init__(self):
            self.base_initialised = True

    application.PersistentServerConnectionApplication = (
        PersistentServerConnectionApplication
    )
    persistconn.application = application
    splunk.persistconn = persistconn

    rest = _fake_module("splunk.rest")
    rest.makeSplunkdUri = lambda: MANAGEMENT_URI
    splunk.rest = rest

    solnlib = _fake_module("solnlib")
    log = _fake_module("solnlib.log")

    class Logs:
        def get_logger(self, name):
            LOGGER_NAMES.append(name)
            logger = logging.getLogger(name)
            logger.addHandler(logging.NullHandler())
            logger.propagate = False
            return logger

    log.Logs = Logs
    log.log_event = _fake_log_event
    solnlib.log = log

    splunktaucclib = _fake_module("splunktaucclib")
    rest_handler = _fake_module("splunktaucclib.rest_handler")
    credentials = _fake_module("splunktaucclib.rest_handler.credentials")
    handler = _fake_module("splunktaucclib.rest_handler.handler")
    credentials.RestCredentials = FakeRestCredentials
    handler.RestHandler = FakeRestHandler
    rest_handler.credentials = credentials
    rest_handler.handler = handler
    splunktaucclib.rest_handler = rest_handler

    generated = _fake_module("slack_alerts_rh_settings")
    generated.endpoint = ENDPOINT


_install_fakes()

_MAIN_FILE_BEFORE_IMPORT = getattr(__main__, "__file__", None)

import slack_broker
import slack_credential

_MAIN_FILE_AFTER_IMPORT = getattr(__main__, "__file__", None)


class BrokerTestCase(unittest.TestCase):
    def setUp(self):
        FakeRestHandler.reset()
        del LOGGED_EVENTS[:]
        self.handler = slack_credential.SlackCredentialHandler(None, None)

    def call(self, **request):
        return self.handler.handle(json.dumps(request))


class ModulePreambleTests(unittest.TestCase):
    def test_logger_is_named_for_the_add_on(self):
        self.assertIn("slack_alerts_credential_broker", LOGGER_NAMES)

    def test_import_leaves_main_file_alone(self):
        self.assertEqual(_MAIN_FILE_AFTER_IMPORT, _MAIN_FILE_BEFORE_IMPORT)


class MainFileScopeTests(BrokerTestCase):
    def setUp(self):
        BrokerTestCase.setUp(self)
        self.outside = getattr(__main__, "__file__", None)
        self.addCleanup(self.restore_main_file)
        __main__.__file__ = CO_RESIDENT_MAIN_FILE

    def restore_main_file(self):
        if self.outside is None:
            if hasattr(__main__, "__file__"):
                del __main__.__file__
        else:
            __main__.__file__ = self.outside

    def test_main_file_is_repointed_into_the_app_bin_directory_during_the_read(self):
        self.call(system_authtoken="session-key")
        self.assertEqual(
            FakeRestHandler.main_files[0].split(os.sep)[-2:],
            ["bin", "slack_credential.py"],
        )

    def test_a_co_resident_handlers_main_file_survives_a_successful_read(self):
        self.call(system_authtoken="session-key")
        self.assertEqual(__main__.__file__, CO_RESIDENT_MAIN_FILE)

    def test_a_co_resident_handlers_main_file_survives_a_failed_read(self):
        real_uri = sys.modules["splunk.rest"].makeSplunkdUri

        def raiser():
            raise RuntimeError("management port closed")

        sys.modules["splunk.rest"].makeSplunkdUri = raiser
        try:
            self.call(system_authtoken="session-key")
        finally:
            sys.modules["splunk.rest"].makeSplunkdUri = real_uri
        self.assertEqual(__main__.__file__, CO_RESIDENT_MAIN_FILE)

    def test_absent_main_file_is_absent_again_afterwards(self):
        del __main__.__file__
        self.call(system_authtoken="session-key")
        self.assertFalse(hasattr(__main__, "__file__"))

    def test_a_rejected_request_never_repoints_main_file(self):
        self.handler.handle("not json")
        self.call(session={"user": "nobody"})
        self.assertEqual(__main__.__file__, CO_RESIDENT_MAIN_FILE)
        self.assertEqual(FakeRestHandler.main_files, [])


class PersistentLoadTests(unittest.TestCase):
    def _stage_app(self, root):
        app = os.path.join(root, "etc", "apps", "slack_alerts")
        os.makedirs(os.path.join(app, "bin"))
        os.makedirs(os.path.join(app, "lib"))
        for module in (slack_credential, slack_broker):
            shutil.copy(module.__file__, os.path.join(app, "bin"))
        with open(os.path.join(app, "bin", "import_declare_test.py"), "w") as stub:
            stub.write("STAGED = True\n")
        return app

    def test_module_loads_from_its_path_alone(self):
        root = tempfile.mkdtemp()
        saved_path = list(sys.path)
        saved_modules = {
            name: sys.modules.pop(name, None)
            for name in (
                "import_declare_test",
                "slack_broker",
                "slack_credential_under_test",
            )
        }
        try:
            app = self._stage_app(root)
            source_dir = os.path.dirname(os.path.realpath(slack_credential.__file__))
            sys.path = [
                entry
                for entry in sys.path
                if os.path.realpath(entry or ".") != source_dir
            ]
            spec = importlib.util.spec_from_file_location(
                "slack_credential_under_test",
                os.path.join(app, "bin", "slack_credential.py"),
            )
            module = importlib.util.module_from_spec(spec)
            sys.modules[spec.name] = module
            spec.loader.exec_module(module)
            self.assertTrue(
                getattr(sys.modules["import_declare_test"], "STAGED", False)
            )
            self.assertTrue(
                _is_persistent_handler(module.SlackCredentialHandler),
            )
        finally:
            sys.path = saved_path
            for name, saved in saved_modules.items():
                if saved is None:
                    sys.modules.pop(name, None)
                else:
                    sys.modules[name] = saved
            shutil.rmtree(root, ignore_errors=True)


def _is_persistent_handler(obj):
    if not inspect.isclass(obj):
        return False
    if obj.__name__ == "PersistentServerConnectionApplication":
        return False
    return any(
        base.__name__ == "PersistentServerConnectionApplication" for base in obj.mro()
    )


def _find_handler_in_module(module):
    classes = inspect.getmembers(module, _is_persistent_handler)
    if len(classes) < 1:
        raise NotImplementedError(
            "No class implements PersistentServerConnectionApplication"
        )
    if len(classes) > 1:
        raise NotImplementedError(
            "More than one class implements PersistentServerConnectionApplication"
        )
    return classes[0][1]


class PlatformHandlerResolutionTests(unittest.TestCase):
    def staged(self, *classes):
        module = types.ModuleType("staged_handler_module")
        for cls in classes:
            setattr(module, cls.__name__, cls)
        return module

    def test_the_shipped_module_resolves_to_the_credential_handler(self):
        self.assertIs(
            _find_handler_in_module(slack_credential),
            slack_credential.SlackCredentialHandler,
        )

    def test_a_module_without_a_handler_class_raises_not_implemented(self):
        with self.assertRaises(NotImplementedError):
            _find_handler_in_module(self.staged())

    def test_a_second_handler_class_raises_not_implemented(self):
        class OtherHandler(slack_credential.PersistentServerConnectionApplication):
            pass

        with self.assertRaises(NotImplementedError):
            _find_handler_in_module(
                self.staged(slack_credential.SlackCredentialHandler, OtherHandler)
            )

    def test_a_handler_class_imported_from_elsewhere_is_counted_too(self):
        class ImportedHandler(slack_credential.PersistentServerConnectionApplication):
            pass

        ImportedHandler.__module__ = "some_other_add_on.bin.other_handler"
        with self.assertRaises(NotImplementedError):
            _find_handler_in_module(
                self.staged(slack_credential.SlackCredentialHandler, ImportedHandler)
            )

    def test_the_resolved_class_is_defined_in_this_module(self):
        resolved = _find_handler_in_module(slack_credential)
        self.assertEqual(resolved.__module__, slack_credential.__name__)


class HandlerDiscoveryTests(unittest.TestCase):
    def test_module_exposes_exactly_one_persistent_handler_class(self):
        found = [
            name
            for name, _ in inspect.getmembers(slack_credential, _is_persistent_handler)
        ]
        self.assertEqual(found, ["SlackCredentialHandler"])

    def test_handle_and_done_are_the_platform_entry_points(self):
        self.assertTrue(callable(slack_credential.SlackCredentialHandler.handle))
        self.assertTrue(callable(slack_credential.SlackCredentialHandler.done))

    def test_handler_accepts_the_command_line_and_argument_the_platform_passes(self):
        self.assertIsNotNone(
            slack_credential.SlackCredentialHandler(["slack_credential.py"], None)
        )


class RequestValidationTests(BrokerTestCase):
    def test_unparsable_request_is_a_400(self):
        result = self.handler.handle("not json")
        self.assertEqual(result["status"], 400)
        self.assertEqual(result["payload"]["error"], "internal")
        self.assertTrue(CORRELATION_ID.match(result["payload"]["correlation_id"]))

    def test_missing_system_authtoken_is_a_500(self):
        result = self.call(session={"user": "nobody"})
        self.assertEqual(result["status"], 500)
        self.assertEqual(result["payload"]["error"], "internal")
        self.assertTrue(CORRELATION_ID.match(result["payload"]["correlation_id"]))

    def test_no_settings_are_read_without_a_system_authtoken(self):
        self.call()
        self.assertEqual(FakeRestHandler.constructed, [])

    def test_failure_payload_carries_nothing_but_error_and_correlation_id(self):
        result = self.handler.handle("not json")
        self.assertEqual(sorted(result["payload"]), ["correlation_id", "error"])

    def test_each_failure_gets_its_own_correlation_id(self):
        first = self.handler.handle("not json")
        second = self.handler.handle("not json")
        self.assertNotEqual(
            first["payload"]["correlation_id"], second["payload"]["correlation_id"]
        )


class ProjectionTests(BrokerTestCase):
    def test_success_returns_every_allowlisted_stanza(self):
        result = self.call(system_authtoken="session-key")
        self.assertEqual(result["status"], 200)
        self.assertEqual(
            sorted(result["payload"]["stanzas"]), sorted(slack_broker.ALLOWLIST)
        )

    def test_session_key_is_passed_to_the_handler_explicitly(self):
        self.call(system_authtoken="session-key")
        self.assertEqual(
            FakeRestHandler.constructed[0], (MANAGEMENT_URI, "session-key", ENDPOINT)
        )

    def test_settings_are_read_decrypted(self):
        self.call(system_authtoken="session-key")
        self.assertIn(("settings", True), FakeRestHandler.calls)

    def test_allowlisted_values_are_returned(self):
        FakeRestHandler.entities = {
            "settings": [
                FakeEntity(
                    "settings",
                    {
                        "webhook_url": "https://hooks.example.com/x",
                        "from_user": "Splunk",
                    },
                )
            ]
        }
        result = self.call(system_authtoken="session-key")
        self.assertEqual(
            result["payload"]["stanzas"]["settings"],
            {"webhook_url": "https://hooks.example.com/x", "from_user": "Splunk"},
        )

    def test_key_outside_the_allowlist_is_withheld(self):
        FakeRestHandler.entities = {
            "settings": [
                FakeEntity(
                    "settings",
                    {
                        "webhook_url": "https://hooks.example.com/x",
                        "eai:acl": {"app": "slack_alerts"},
                        "disabled": "0",
                    },
                )
            ],
            "proxy": [
                FakeEntity(
                    "proxy",
                    {
                        "proxy_enabled": "1",
                        "proxy_url": "p.example.com",
                        "proxy_port": "8080",
                        "proxy_password": "s3cret",
                        "proxy_username": "admin",
                        "eai:userName": "nobody",
                        "disabled": "0",
                    },
                )
            ],
        }
        result = self.call(system_authtoken="session-key")
        self.assertEqual(
            sorted(result["payload"]["stanzas"]["settings"]), ["webhook_url"]
        )
        self.assertEqual(
            sorted(result["payload"]["stanzas"]["proxy"]),
            [
                "proxy_enabled",
                "proxy_password",
                "proxy_port",
                "proxy_url",
                "proxy_username",
            ],
        )

    def test_placeholder_value_is_not_returned(self):
        FakeRestHandler.entities = {
            "settings": [
                FakeEntity(
                    "settings",
                    {
                        "slack_app_oauth_token": FakeRestCredentials.PASSWORD,
                        "webhook_url": FakeRestCredentials.LEGACY_PASSWORD,
                        "from_user": "Splunk",
                    },
                )
            ]
        }
        result = self.call(system_authtoken="session-key")
        self.assertEqual(
            result["payload"]["stanzas"]["settings"], {"from_user": "Splunk"}
        )

    def test_absent_value_is_not_returned_as_none(self):
        FakeRestHandler.entities = {
            "settings": [FakeEntity("settings", {"webhook_url": None})]
        }
        result = self.call(system_authtoken="session-key")
        self.assertEqual(result["payload"]["stanzas"]["settings"], {})

    def test_non_string_value_survives_the_placeholder_check(self):
        FakeRestHandler.entities = {
            "proxy": [FakeEntity("proxy", {"proxy_port": 8080})]
        }
        result = self.call(system_authtoken="session-key")
        self.assertEqual(result["payload"]["stanzas"]["proxy"], {"proxy_port": 8080})


class StanzaIsolationTests(BrokerTestCase):
    def test_one_unreadable_stanza_does_not_fail_the_others(self):
        FakeRestHandler.entities = {
            "settings": [
                FakeEntity("settings", {"webhook_url": "https://hooks.example.com/x"})
            ],
            "logging": [FakeEntity("logging", {"loglevel": "DEBUG"})],
        }
        FakeRestHandler.raises = {"proxy": ValueError("stanza absent")}
        result = self.call(system_authtoken="session-key")
        self.assertEqual(result["status"], 200)
        self.assertEqual(result["payload"]["stanzas"]["proxy"], {})
        self.assertEqual(
            result["payload"]["stanzas"]["settings"],
            {"webhook_url": "https://hooks.example.com/x"},
        )
        self.assertEqual(result["payload"]["stanzas"]["logging"], {"loglevel": "DEBUG"})

    def test_every_stanza_unreadable_still_returns_200_with_empty_stanzas(self):
        FakeRestHandler.raises = {
            name: ValueError("stanza absent") for name in slack_broker.ALLOWLIST
        }
        result = self.call(system_authtoken="session-key")
        self.assertEqual(result["status"], 200)
        self.assertEqual(
            result["payload"]["stanzas"], {name: {} for name in slack_broker.ALLOWLIST}
        )


class FailureDisclosureTests(BrokerTestCase):
    def setUp(self):
        BrokerTestCase.setUp(self)
        self.real_uri = sys.modules["splunk.rest"].makeSplunkdUri

    def tearDown(self):
        sys.modules["splunk.rest"].makeSplunkdUri = self.real_uri

    def _break_the_privileged_path(self):
        def raiser():
            raise RuntimeError("management port closed at https://127.0.0.1:8089")

        sys.modules["splunk.rest"].makeSplunkdUri = raiser

    def test_unexpected_failure_is_a_500_with_no_detail(self):
        self._break_the_privileged_path()
        result = self.call(system_authtoken="session-key")
        self.assertEqual(result["status"], 500)
        self.assertEqual(sorted(result["payload"]), ["correlation_id", "error"])
        self.assertEqual(result["payload"]["error"], "internal")
        self.assertNotIn("management port closed", json.dumps(result))

    def test_logged_failure_names_the_exception_type_only(self):
        self._break_the_privileged_path()
        result = self.call(system_authtoken="session-key")
        self.assertEqual(len(LOGGED_EVENTS), 1)
        event, level = LOGGED_EVENTS[0]
        self.assertEqual(level, logging.ERROR)
        self.assertEqual(event["action"], "broker_failure")
        self.assertEqual(event["error_type"], "RuntimeError")
        self.assertEqual(event["correlation_id"], result["payload"]["correlation_id"])
        self.assertNotIn(
            "management port closed", " ".join(str(v) for v in event.values())
        )

    def test_validation_failure_is_logged_by_reason(self):
        self.call(session={"user": "nobody"})
        self.assertEqual(len(LOGGED_EVENTS), 1)
        event, level = LOGGED_EVENTS[0]
        self.assertEqual(level, logging.ERROR)
        self.assertEqual(event["error_type"], "no_system_authtoken")

    def test_no_secret_reaches_the_failure_payload(self):
        FakeRestHandler.entities = {
            "settings": [
                FakeEntity("settings", {"slack_app_oauth_token": "xoxb-secret"})
            ]
        }
        FakeRestHandler.raises = {"proxy": ValueError("xoxb-secret")}
        result = self.call(system_authtoken="session-key")
        self.assertNotIn(
            "xoxb-secret", json.dumps(result["payload"]["stanzas"]["proxy"])
        )
        for event, _ in LOGGED_EVENTS:
            self.assertNotIn("xoxb-secret", " ".join(str(v) for v in event.values()))


class StanzaFailureLoggingTests(BrokerTestCase):
    def test_unreadable_stanza_is_logged_with_its_name_and_error_type(self):
        FakeRestHandler.raises = {"proxy": ValueError("stanza absent")}
        self.call(system_authtoken="session-key")
        failures = _events("broker_stanza_unreadable")
        self.assertEqual(len(failures), 1)
        event, level = failures[0]
        self.assertEqual(level, logging.ERROR)
        self.assertEqual(event["stanza"], "proxy")
        self.assertEqual(event["error_type"], "ValueError")
        self.assertTrue(CORRELATION_ID.match(event["correlation_id"]))

    def test_every_unreadable_stanza_is_logged_under_one_correlation_id(self):
        FakeRestHandler.raises = {
            name: ValueError("stanza absent") for name in slack_broker.ALLOWLIST
        }
        self.call(system_authtoken="session-key")
        failures = _events("broker_stanza_unreadable")
        self.assertEqual(len(failures), len(slack_broker.ALLOWLIST))
        self.assertEqual(
            sorted(event["stanza"] for event, _ in failures),
            sorted(slack_broker.ALLOWLIST),
        )
        self.assertEqual(len({event["correlation_id"] for event, _ in failures}), 1)

    def test_a_readable_stanza_logs_no_stanza_failure(self):
        FakeRestHandler.entities = {
            "settings": [FakeEntity("settings", {"from_user": "Splunk"})]
        }
        self.call(system_authtoken="session-key")
        self.assertEqual(_events("broker_stanza_unreadable"), [])

    def test_stanza_failure_log_carries_nothing_but_the_four_fields(self):
        FakeRestHandler.raises = {"logging": ValueError("stanza absent")}
        self.call(system_authtoken="session-key")
        event, _ = _events("broker_stanza_unreadable")[0]
        self.assertEqual(
            sorted(event), ["action", "correlation_id", "error_type", "stanza"]
        )


class SuccessLoggingTests(BrokerTestCase):
    SESSION = {"user": "alert_owner", "authtoken": "owner-session-key"}

    def setUp(self):
        BrokerTestCase.setUp(self)
        FakeRestHandler.entities = {
            "settings": [
                FakeEntity(
                    "settings",
                    {
                        "slack_app_oauth_token": "xoxb-secret",
                        "webhook_url": "https://hooks.slack.com/services/T0/B0/secret",
                    },
                )
            ]
        }

    def test_a_successful_read_logs_the_caller_once_at_info(self):
        result = self.call(system_authtoken="system-key", session=self.SESSION)
        reads = _events("broker_read")
        self.assertEqual(len(reads), 1)
        event, level = reads[0]
        self.assertEqual(level, logging.INFO)
        self.assertEqual(event["user"], "alert_owner")
        self.assertEqual(result["status"], 200)
        self.assertTrue(CORRELATION_ID.match(event["correlation_id"]))

    def test_success_log_carries_nothing_but_the_three_fields(self):
        self.call(system_authtoken="system-key", session=self.SESSION)
        event, _ = _events("broker_read")[0]
        self.assertEqual(sorted(event), ["action", "correlation_id", "user"])

    def test_success_log_carries_no_secret_or_session_key(self):
        self.call(system_authtoken="system-key", session=self.SESSION)
        logged = " ".join(str(v) for e, _ in LOGGED_EVENTS for v in e.values())
        for secret in (
            "xoxb-secret",
            "hooks.slack.com",
            "owner-session-key",
            "system-key",
        ):
            self.assertNotIn(secret, logged)

    def test_a_read_without_a_session_still_logs_and_names_no_user(self):
        result = self.call(system_authtoken="system-key")
        self.assertEqual(result["status"], 200)
        event, _ = _events("broker_read")[0]
        self.assertIsNone(event["user"])

    def test_a_failed_read_logs_no_success(self):
        real_uri = sys.modules["splunk.rest"].makeSplunkdUri

        def raiser():
            raise RuntimeError("management port closed")

        sys.modules["splunk.rest"].makeSplunkdUri = raiser
        self.addCleanup(setattr, sys.modules["splunk.rest"], "makeSplunkdUri", real_uri)
        self.call(system_authtoken="system-key", session=self.SESSION)
        self.assertEqual(_events("broker_read"), [])

    def test_a_rejected_request_logs_no_success(self):
        self.call(session=self.SESSION)
        self.assertEqual(_events("broker_read"), [])


class LifecycleTests(BrokerTestCase):
    def test_base_initialiser_runs(self):
        self.assertTrue(getattr(self.handler, "base_initialised", False))

    def test_done_is_a_no_op(self):
        self.assertIsNone(self.handler.done())


if __name__ == "__main__":
    unittest.main()
