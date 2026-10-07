import os
import shutil

ALERT_TOKEN_PARAMS = {
    "param.view_link": "$view_link$",
    "param.info_trigger_time": "$trigger_time$",
    "param.info_severity": "$alert.severity$",
}

BROKER_STANZA = """
[script:slack_credential]
match                 = /slack_credential
scripttype            = persist
script                = slack_credential.py
handler               = slack_credential.SlackCredentialHandler
passSystemAuth        = true
passSession           = true
capability            = read_slack_alerts_credential
acceptFrom            = 127.0.0.1, ::1
output_modes          = json
python.version        = python3
python.required       = 3.9, 3.13
"""

RESTMAP_ANCHOR = "[admin_external:slack_alerts_settings]"

ALERT_OVERRIDES = """
    def get_log_level(self):
        try:
            import slack_broker

            return slack_broker.log_level(self)
        except Exception:
            return "INFO"

    def get_events(self):
        import slack_results

        return slack_results.get_events(self)

    def prepare_meta_for_cam(self):
        import slack_results

        if not slack_results.results_present(self):
            return None
        return super().prepare_meta_for_cam()
"""

ALERT_ANCHOR = "    def process_event(self"

ALERT_MARKER = "slack_results.results_present"

PYCACHE_DIR = "__pycache__"

PYC_SUFFIX = ".pyc"


def remove_bytecode_caches(output_directory, ta_name):
    root = os.path.join(output_directory, ta_name)
    for parent, directories, _files in os.walk(root, topdown=False):
        for directory in directories:
            if directory == PYCACHE_DIR:
                shutil.rmtree(os.path.join(parent, directory))


def _raise_walk_error(error):
    raise error


def assert_no_bytecode_caches(output_directory, ta_name):
    root = os.path.join(output_directory, ta_name)
    for parent, directories, files in os.walk(root, onerror=_raise_walk_error):
        for directory in directories:
            if directory == PYCACHE_DIR:
                raise RuntimeError(
                    "bytecode cache survived at %s" % os.path.join(parent, directory)
                )
        for name in files:
            if name.endswith(PYC_SUFFIX):
                raise RuntimeError(
                    "bytecode cache survived at %s" % os.path.join(parent, name)
                )


def cleanup_output_files(output_directory, ta_name):
    remove_bytecode_caches(output_directory, ta_name)

    conf_path = os.path.join(output_directory, ta_name, "default", "alert_actions.conf")
    if not os.path.exists(conf_path):
        raise RuntimeError("generated alert_actions.conf missing at %s" % conf_path)

    with open(conf_path) as fh:
        lines = fh.readlines()

    out = []
    in_slack = False
    injected = False
    existing = set()

    def flush_tokens():
        added = []
        for key, value in ALERT_TOKEN_PARAMS.items():
            if key not in existing:
                added.append("%s = %s\n" % (key, value))
        return added

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            if in_slack and not injected:
                out.extend(flush_tokens())
                injected = True
            in_slack = stripped == "[slack]"
            existing = set()
        elif in_slack and "=" in line:
            existing.add(line.split("=", 1)[0].strip())
        out.append(line)

    if in_slack and not injected:
        out.extend(flush_tokens())
        injected = True

    if not injected:
        raise RuntimeError(
            "[slack] stanza not found in %s; alert token params were not injected."
            % conf_path
        )

    with open(conf_path, "w") as fh:
        fh.writelines(out)

    restmap = os.path.join(output_directory, ta_name, "default", "restmap.conf")
    if not os.path.exists(restmap):
        raise RuntimeError("restmap.conf missing at %s" % restmap)
    with open(restmap) as handle:
        text = handle.read()
    if RESTMAP_ANCHOR not in text:
        raise RuntimeError(
            "anchor %s absent from %s, so the broker stanza was not injected"
            % (RESTMAP_ANCHOR, restmap)
        )
    if "[script:slack_credential]" not in text:
        with open(restmap, "w") as handle:
            handle.write(text.rstrip("\n") + "\n" + BROKER_STANZA)

    alert = os.path.join(output_directory, ta_name, "bin", "slack.py")
    if not os.path.exists(alert):
        raise RuntimeError("generated alert action missing at %s" % alert)
    with open(alert) as handle:
        alert_text = handle.read()
    if ALERT_ANCHOR not in alert_text:
        raise RuntimeError(
            "anchor %r absent from %s, so the overrides were not injected"
            % (ALERT_ANCHOR, alert)
        )
    if ALERT_MARKER not in alert_text:
        if "def get_log_level" in alert_text:
            raise RuntimeError(
                "%s defines get_log_level without %r, so the framework now owns a "
                "method the overrides replace" % (alert, ALERT_MARKER)
            )
        alert_text = alert_text.replace(
            ALERT_ANCHOR, ALERT_OVERRIDES.rstrip("\n") + "\n\n" + ALERT_ANCHOR, 1
        )
        with open(alert, "w") as handle:
            handle.write(alert_text)

    settings_handler = os.path.join(
        output_directory, ta_name, "bin", "slack_alerts_rh_settings.py"
    )
    if not os.path.exists(settings_handler):
        raise RuntimeError(
            "generated settings handler missing at %s, so the broker cannot import it"
            % settings_handler
        )

    assert_no_bytecode_caches(output_directory, ta_name)
