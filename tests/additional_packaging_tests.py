import os
import shutil
import sys
import tempfile
import types
import unittest

import additional_packaging

BASE_META = {"base": True}
FAKE_MODULES = (
    "import_declare_test",
    "splunktaucclib",
    "splunktaucclib.alert_actions_base",
    "slack_logic",
)

ALERT_ACTIONS = """[slack]
is_custom = 1
label = Slack
"""

RESTMAP = """[admin:slack_alerts]
match = /
members = slack_alerts_settings

[admin_external:slack_alerts_settings]
handlertype = python
python.version = python3
handlerfile = slack_alerts_rh_settings.py
handleractions = edit, list
handlerpersistentmode = true
"""

SLACK_PY = """# encoding = utf-8
import import_declare_test

import os
import sys

from splunktaucclib.alert_actions_base import ModularAlertBase
import slack_logic


class AlertActionWorkerslack(ModularAlertBase):

    def __init__(self, ta_name, alert_name):
        super(AlertActionWorkerslack, self).__init__(ta_name, alert_name)

    def validate_params(self):
        if not self.get_param("message"):
            self.log_error("message is a mandatory parameter, but its value is None.")
            return False
        return True

    def process_event(self, *args, **kwargs):
        status = 0
        return status


if __name__ == "__main__":
    exitcode = AlertActionWorkerslack("slack_alerts", "slack").run(sys.argv)
    sys.exit(exitcode)
"""


class PackagingTestCase(unittest.TestCase):
    def setUp(self):
        self.output_directory = tempfile.mkdtemp()
        self.ta_name = "slack_alerts"
        self.default = os.path.join(self.output_directory, self.ta_name, "default")
        self.bin = os.path.join(self.output_directory, self.ta_name, "bin")
        os.makedirs(self.default)
        os.makedirs(self.bin)
        self.alert_actions = os.path.join(self.default, "alert_actions.conf")
        self.restmap = os.path.join(self.default, "restmap.conf")
        self.alert = os.path.join(self.bin, "slack.py")
        self.settings_handler = os.path.join(self.bin, "slack_alerts_rh_settings.py")
        self.write(self.alert_actions, ALERT_ACTIONS)
        self.write(self.restmap, RESTMAP)
        self.write(self.alert, SLACK_PY)
        self.write(self.settings_handler, "endpoint = None\n")
        self.addCleanup(shutil.rmtree, self.output_directory, True)

    def write(self, path, text):
        with open(path, "w") as handle:
            handle.write(text)

    def read(self, path):
        with open(path) as handle:
            return handle.read()

    def run_cleanup(self):
        additional_packaging.cleanup_output_files(self.output_directory, self.ta_name)


class BrokerStanzaTests(unittest.TestCase):
    def test_stanza_header_matches_the_endpoint_name(self):
        self.assertIn("[script:slack_credential]", additional_packaging.BROKER_STANZA)

    def test_match_is_the_broker_path(self):
        self.assertIn(
            "match                 = /slack_credential",
            additional_packaging.BROKER_STANZA,
        )

    def test_scripttype_is_persist(self):
        self.assertIn(
            "scripttype            = persist", additional_packaging.BROKER_STANZA
        )

    def test_script_key_is_present_for_cloud_resolution(self):
        self.assertIn(
            "script                = slack_credential.py",
            additional_packaging.BROKER_STANZA,
        )

    def test_handler_names_the_script_module_and_its_class(self):
        self.assertIn(
            "handler               = slack_credential.SlackCredentialHandler",
            additional_packaging.BROKER_STANZA,
        )

    def test_handler_names_no_module_the_add_on_does_not_ship(self):
        self.assertNotIn("application.", additional_packaging.BROKER_STANZA)

    def test_system_auth_and_session_are_passed(self):
        self.assertIn(
            "passSystemAuth        = true", additional_packaging.BROKER_STANZA
        )
        self.assertIn(
            "passSession           = true", additional_packaging.BROKER_STANZA
        )

    def test_capability_is_the_narrow_credential_capability(self):
        self.assertIn(
            "capability            = read_slack_alerts_credential",
            additional_packaging.BROKER_STANZA,
        )

    def test_accept_from_is_loopback_only(self):
        self.assertIn(
            "acceptFrom            = 127.0.0.1, ::1", additional_packaging.BROKER_STANZA
        )

    def test_output_modes_is_json(self):
        self.assertIn(
            "output_modes          = json", additional_packaging.BROKER_STANZA
        )

    def test_python_version_is_python3(self):
        self.assertIn(
            "python.version        = python3", additional_packaging.BROKER_STANZA
        )

    def test_python_required_lists_both_targets(self):
        self.assertIn(
            "python.required       = 3.9, 3.13", additional_packaging.BROKER_STANZA
        )

    def test_stanza_carries_no_comment(self):
        for line in additional_packaging.BROKER_STANZA.splitlines():
            self.assertFalse(line.lstrip().startswith("#"))


class RestmapInjectionTests(PackagingTestCase):
    def test_stanza_is_appended(self):
        self.run_cleanup()
        self.assertIn("[script:slack_credential]", self.read(self.restmap))

    def test_generated_settings_handler_survives(self):
        self.run_cleanup()
        text = self.read(self.restmap)
        self.assertIn("[admin_external:slack_alerts_settings]", text)
        self.assertIn("handlerfile = slack_alerts_rh_settings.py", text)

    def test_injection_is_idempotent(self):
        self.run_cleanup()
        once = self.read(self.restmap)
        self.run_cleanup()
        self.assertEqual(once, self.read(self.restmap))

    def test_stanza_header_starts_its_own_line(self):
        self.run_cleanup()
        self.assertIn("\n[script:slack_credential]\n", self.read(self.restmap))

    def test_alert_token_params_still_injected(self):
        self.run_cleanup()
        self.assertIn("param.view_link = $view_link$", self.read(self.alert_actions))


class FailLoudTests(PackagingTestCase):
    def test_missing_alert_actions_raises(self):
        os.remove(self.alert_actions)
        with self.assertRaises(RuntimeError) as caught:
            self.run_cleanup()
        self.assertIn("alert_actions.conf", str(caught.exception))
        self.assertIn(self.alert_actions, str(caught.exception))

    def test_missing_restmap_raises(self):
        os.remove(self.restmap)
        with self.assertRaises(RuntimeError) as caught:
            self.run_cleanup()
        self.assertIn(self.restmap, str(caught.exception))

    def test_missing_settings_handler_the_broker_imports_raises(self):
        os.remove(self.settings_handler)
        with self.assertRaises(RuntimeError) as caught:
            self.run_cleanup()
        self.assertIn(self.settings_handler, str(caught.exception))

    def test_moved_anchor_raises_naming_the_anchor(self):
        self.write(self.restmap, RESTMAP.replace("slack_alerts_settings]", "MOVED]"))
        with self.assertRaises(RuntimeError) as caught:
            self.run_cleanup()
        self.assertIn(additional_packaging.RESTMAP_ANCHOR, str(caught.exception))

    def test_moved_anchor_leaves_the_stanza_uninjected(self):
        self.write(self.restmap, RESTMAP.replace("slack_alerts_settings]", "MOVED]"))
        try:
            self.run_cleanup()
        except RuntimeError:
            pass
        self.assertNotIn("[script:slack_credential]", self.read(self.restmap))


class PycacheRemovalTests(PackagingTestCase):
    def plant(self, *parts):
        directory = os.path.join(self.output_directory, self.ta_name, *parts)
        os.makedirs(directory)
        path = os.path.join(directory, "slack_broker.cpython-313.pyc")
        with open(path, "wb") as handle:
            handle.write(b"\x00\x00\x00\x00")
        return directory

    def surviving(self):
        found = []
        for root, directories, _files in os.walk(
            os.path.join(self.output_directory, self.ta_name)
        ):
            for directory in directories:
                if directory == "__pycache__":
                    found.append(os.path.join(root, directory))
        return found

    def test_bin_pycache_is_removed(self):
        self.plant("bin", "__pycache__")
        self.run_cleanup()
        self.assertEqual(self.surviving(), [])

    def test_nested_pycache_outside_bin_is_removed(self):
        self.plant("lib", "splunktaucclib", "__pycache__")
        self.run_cleanup()
        self.assertEqual(self.surviving(), [])

    def test_several_pycache_directories_are_all_removed(self):
        self.plant("bin", "__pycache__")
        self.plant("lib", "__pycache__")
        self.plant("lib", "solnlib", "packages", "__pycache__")
        self.run_cleanup()
        self.assertEqual(self.surviving(), [])

    def test_sibling_files_survive_the_removal(self):
        self.plant("bin", "__pycache__")
        self.run_cleanup()
        self.assertTrue(os.path.exists(self.alert))
        self.assertTrue(os.path.exists(self.restmap))

    def test_removal_is_a_no_op_without_any_pycache(self):
        self.run_cleanup()
        self.assertEqual(self.surviving(), [])

    def test_removal_runs_before_the_injections(self):
        self.plant("bin", "__pycache__")
        os.remove(self.alert_actions)
        try:
            self.run_cleanup()
        except RuntimeError:
            pass
        self.assertEqual(self.surviving(), [])

    def test_a_stray_pyc_outside_a_pycache_directory_raises(self):
        stray = os.path.join(self.bin, "slack_broker.cpython-313.pyc")
        with open(stray, "wb") as handle:
            handle.write(b"\x00\x00\x00\x00")
        with self.assertRaises(RuntimeError) as caught:
            self.run_cleanup()
        self.assertIn(stray, str(caught.exception))

    def test_a_pycache_the_removal_missed_raises_naming_the_path(self):
        directory = self.plant("bin", "__pycache__")
        original = additional_packaging.remove_bytecode_caches
        additional_packaging.remove_bytecode_caches = lambda *_args: None
        self.addCleanup(
            setattr, additional_packaging, "remove_bytecode_caches", original
        )
        with self.assertRaises(RuntimeError) as caught:
            self.run_cleanup()
        self.assertIn(directory, str(caught.exception))

    def test_an_undeletable_pycache_stops_the_hook(self):
        directory = self.plant("bin", "__pycache__")
        parent = os.path.dirname(directory)
        os.chmod(parent, 0o500)
        self.addCleanup(os.chmod, parent, 0o700)
        with self.assertRaises(OSError):
            self.run_cleanup()

    def test_an_unlistable_directory_stops_the_hook(self):
        directory = self.plant("bin", "unlistable", "__pycache__")
        unlistable = os.path.dirname(directory)
        os.chmod(unlistable, 0o300)
        self.addCleanup(os.chmod, unlistable, 0o700)
        with self.assertRaises(OSError):
            self.run_cleanup()


class AlertOverrideTests(unittest.TestCase):
    def test_anchor_is_the_indented_process_event_definition(self):
        self.assertEqual(
            additional_packaging.ALERT_ANCHOR, "    def process_event(self"
        )

    def test_log_level_override_delegates_to_the_broker(self):
        self.assertIn("def get_log_level(self):", additional_packaging.ALERT_OVERRIDES)
        self.assertIn(
            "return slack_broker.log_level(self)", additional_packaging.ALERT_OVERRIDES
        )

    def test_log_level_override_falls_back_without_logging(self):
        overrides = additional_packaging.ALERT_OVERRIDES
        self.assertIn('return "INFO"', overrides)
        self.assertNotIn("log_error", overrides)

    def test_get_events_override_delegates_to_slack_results(self):
        self.assertIn(
            "return slack_results.get_events(self)",
            additional_packaging.ALERT_OVERRIDES,
        )

    def test_prepare_meta_pre_checks_then_defers_to_the_base(self):
        overrides = additional_packaging.ALERT_OVERRIDES
        self.assertIn("if not slack_results.results_present(self):", overrides)
        self.assertIn("return super().prepare_meta_for_cam()", overrides)
        self.assertNotIn("SystemExit", overrides)

    def test_overrides_name_no_generated_class(self):
        self.assertNotIn("AlertActionWorker", additional_packaging.ALERT_OVERRIDES)

    def test_overrides_carry_no_comment(self):
        for line in additional_packaging.ALERT_OVERRIDES.splitlines():
            self.assertFalse(line.lstrip().startswith("#"))


class AlertInjectionTests(PackagingTestCase):
    def test_all_three_overrides_land(self):
        self.run_cleanup()
        text = self.read(self.alert)
        self.assertIn("    def get_log_level(self):", text)
        self.assertIn("    def get_events(self):", text)
        self.assertIn("    def prepare_meta_for_cam(self):", text)

    def test_overrides_land_above_the_anchor(self):
        self.run_cleanup()
        text = self.read(self.alert)
        self.assertLess(
            text.index("def get_log_level"),
            text.index(additional_packaging.ALERT_ANCHOR),
        )

    def test_the_generated_body_survives(self):
        self.run_cleanup()
        text = self.read(self.alert)
        self.assertIn("def validate_params(self):", text)
        self.assertIn(additional_packaging.ALERT_ANCHOR, text)

    def test_the_injected_file_is_valid_python(self):
        self.run_cleanup()
        compile(self.read(self.alert), self.alert, "exec")

    def test_the_import_block_is_untouched(self):
        self.run_cleanup()
        text = self.read(self.alert)
        self.assertEqual(text.count("\nimport os\n"), 1)
        self.assertEqual(text.count("\nimport sys\n"), 1)

    def test_injection_is_idempotent(self):
        self.run_cleanup()
        once = self.read(self.alert)
        self.run_cleanup()
        self.assertEqual(once, self.read(self.alert))

    def test_restmap_injection_still_runs(self):
        self.run_cleanup()
        self.assertIn("[script:slack_credential]", self.read(self.restmap))


FRAMEWORK_LOG_LEVEL = """    def get_log_level(self):
        return "DEBUG"

"""


class AlertIdempotencyTests(PackagingTestCase):
    def test_the_marker_is_produced_by_the_overrides(self):
        self.assertIn(
            additional_packaging.ALERT_MARKER, additional_packaging.ALERT_OVERRIDES
        )

    def test_the_marker_is_not_the_anchor_or_a_framework_concern(self):
        self.assertNotIn("get_log_level", additional_packaging.ALERT_MARKER)
        self.assertNotEqual(
            additional_packaging.ALERT_MARKER, additional_packaging.ALERT_ANCHOR
        )

    def test_a_second_run_injects_nothing_further(self):
        self.run_cleanup()
        once = self.read(self.alert)
        self.run_cleanup()
        twice = self.read(self.alert)
        self.assertEqual(once, twice)
        self.assertEqual(twice.count("def get_events(self):"), 1)
        self.assertEqual(twice.count("def prepare_meta_for_cam(self):"), 1)
        self.assertEqual(twice.count(additional_packaging.ALERT_MARKER), 1)

    def test_a_framework_log_level_without_our_marker_raises(self):
        self.write(
            self.alert,
            SLACK_PY.replace(
                additional_packaging.ALERT_ANCHOR,
                FRAMEWORK_LOG_LEVEL + additional_packaging.ALERT_ANCHOR,
            ),
        )
        with self.assertRaises(RuntimeError) as caught:
            self.run_cleanup()
        message = str(caught.exception)
        self.assertIn("get_log_level", message)
        self.assertIn(additional_packaging.ALERT_MARKER, message)
        self.assertIn(self.alert, message)

    def test_a_framework_log_level_leaves_the_file_uninjected(self):
        self.write(
            self.alert,
            SLACK_PY.replace(
                additional_packaging.ALERT_ANCHOR,
                FRAMEWORK_LOG_LEVEL + additional_packaging.ALERT_ANCHOR,
            ),
        )
        try:
            self.run_cleanup()
        except RuntimeError:
            pass
        text = self.read(self.alert)
        self.assertNotIn(additional_packaging.ALERT_MARKER, text)
        self.assertNotIn("def get_events(self):", text)


class AlertFailLoudTests(PackagingTestCase):
    def test_missing_alert_action_raises(self):
        os.remove(self.alert)
        with self.assertRaises(RuntimeError) as caught:
            self.run_cleanup()
        self.assertIn(self.alert, str(caught.exception))

    def test_renamed_anchor_raises_naming_the_anchor(self):
        self.write(
            self.alert, SLACK_PY.replace("def process_event(self", "def renamed(self")
        )
        with self.assertRaises(RuntimeError) as caught:
            self.run_cleanup()
        self.assertIn(additional_packaging.ALERT_ANCHOR, str(caught.exception))

    def test_renamed_anchor_leaves_the_file_uninjected(self):
        self.write(
            self.alert, SLACK_PY.replace("def process_event(self", "def renamed(self")
        )
        try:
            self.run_cleanup()
        except RuntimeError:
            pass
        self.assertNotIn("def get_log_level", self.read(self.alert))


class FakeModularAlertBase(object):
    def __init__(self, ta_name, alert_name):
        self.ta_name = ta_name
        self.alert_name = alert_name
        self.results_file = None

    def prepare_meta_for_cam(self):
        return BASE_META


class InjectedOverrideTests(PackagingTestCase):
    def worker(self, source=SLACK_PY):
        self.write(self.alert, source)
        self.run_cleanup()
        saved = {name: sys.modules.get(name) for name in FAKE_MODULES}
        self.addCleanup(self.restore_modules, saved)
        declare = types.ModuleType("import_declare_test")
        package = types.ModuleType("splunktaucclib")
        base = types.ModuleType("splunktaucclib.alert_actions_base")
        base.ModularAlertBase = FakeModularAlertBase
        package.alert_actions_base = base
        sys.modules["import_declare_test"] = declare
        sys.modules["splunktaucclib"] = package
        sys.modules["splunktaucclib.alert_actions_base"] = base
        sys.modules["slack_logic"] = types.ModuleType("slack_logic")
        namespace = {"__name__": "slack_alerts_injected", "__file__": self.alert}
        exec(compile(self.read(self.alert), self.alert, "exec"), namespace)
        generated = [
            value
            for value in namespace.values()
            if isinstance(value, type)
            and issubclass(value, FakeModularAlertBase)
            and value is not FakeModularAlertBase
        ]
        return generated[0]("slack_alerts", "slack")

    def restore_modules(self, saved):
        for name, module in saved.items():
            if module is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = module

    def results_path(self):
        path = os.path.join(self.output_directory, "results.csv.gz")
        with open(path, "wb") as handle:
            handle.write(b"")
        return path

    def test_prepare_meta_defers_to_the_base_when_results_are_present(self):
        worker = self.worker()
        worker.results_file = self.results_path()
        self.assertEqual(worker.prepare_meta_for_cam(), BASE_META)

    def test_prepare_meta_returns_none_when_the_results_file_is_absent(self):
        worker = self.worker()
        worker.results_file = os.path.join(self.output_directory, "missing.csv.gz")
        self.assertIsNone(worker.prepare_meta_for_cam())

    def test_prepare_meta_defers_when_the_generated_class_is_renamed(self):
        worker = self.worker(
            SLACK_PY.replace("AlertActionWorkerslack", "AlertActionWorker")
        )
        worker.results_file = self.results_path()
        self.assertEqual(worker.prepare_meta_for_cam(), BASE_META)

    def test_get_events_reads_through_slack_results(self):
        worker = self.worker()
        worker.results_file = os.path.join(self.output_directory, "missing.csv.gz")
        self.assertEqual(list(worker.get_events()), [])


class SourceTreeTests(unittest.TestCase):
    def test_no_restmap_is_shipped_in_the_source_tree(self):
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.assertFalse(
            os.path.exists(os.path.join(root, "package", "default", "restmap.conf"))
        )


if __name__ == "__main__":
    unittest.main()
