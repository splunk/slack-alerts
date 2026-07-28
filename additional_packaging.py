import os

ALERT_TOKEN_PARAMS = {
    "param.view_link": "$view_link$",
    "param.info_trigger_time": "$trigger_time$",
    "param.info_severity": "$alert.severity$",
}


def cleanup_output_files(output_directory, ta_name):
    conf_path = os.path.join(output_directory, ta_name, "default", "alert_actions.conf")
    if not os.path.exists(conf_path):
        return

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
