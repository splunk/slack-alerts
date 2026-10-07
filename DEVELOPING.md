# Developing

This app is built with the [Splunk Add-on UCC Framework](https://splunk.github.io/addonfactory-ucc-generator/).
The configuration UI and the alert action are generated from `globalConfig.json`;
the Slack posting logic lives in `package/bin/slack_logic.py`.

## Layout

```
globalConfig.json          UCC definition (Configuration tab + "slack" alert action)
additional_packaging.py    Post-build hook that patches the generated tree
package/
  app.manifest             App metadata (schemaVersion 2.0.0)
  CHANGELOG.md             Release notes (referenced by app.manifest)
  README.md                App description
  bin/
    slack_logic.py         Slack posting logic (process_event entry point)
    slack_broker.py        Client the alert action reads its settings through
    slack_credential.py    Privileged REST handler that serves those settings
    slack_results.py       Results-file reader (an absent file reads as empty)
    safe_fmt.py            Safe string template formatter
  default/
    authorize.conf         read_slack_alerts_credential and the slack_alert_action role
  lib/requirements.txt     Python deps vendored into the build
  static/                  App icons
  appserver/static/        Alert action icon (slack.png)
tests/                     Unit tests
```

`ucc-gen build` generates `default/alert_actions.conf`, the alert HTML form,
`app.conf`, the Configuration view, and the `bin/slack.py` entry-point wrapper.
`additional_packaging.py` then patches the generated tree, and fails the build when
an anchor or file it needs is missing:

- `default/alert_actions.conf`: the alert token params
- `default/restmap.conf`: the broker's `[script:slack_credential]` stanza
- `bin/slack.py`: the results-file and log-level overrides

Do not hand-edit anything under `output/` - every build regenerates it.

## Prerequisites

Use the `app-toolkit` pyenv environment (holds `ucc-gen` and `splunk-appinspect`):

```sh
PYENV_VERSION="app-toolkit:3.13.7" <command>
```

Both CI workflows pin the generator to `splunk-add-on-ucc-framework==6.5.3`. Keep the
`app-toolkit` environment on the same version.

## Build

```sh
PYENV_VERSION="app-toolkit:3.13.7" ucc-gen build --source package --ta-version 3.1.0
PYENV_VERSION="app-toolkit:3.13.7" ucc-gen package --path output/slack_alerts
```

This produces `output/slack_alerts/` and a `slack_alerts-<version>.tar.gz` you can
upload to Splunk or Splunkbase. Both are gitignored.

## Validate (Splunk Cloud Platform tags)

```sh
PYENV_VERSION="app-toolkit:3.13.7" splunk-appinspect inspect slack_alerts-3.1.0.tar.gz \
  --mode precert --included-tags cloud \
  --included-tags private_app --included-tags private_victoria --included-tags private_classic
```

## Test

```sh
PYENV_VERSION="app-toolkit:3.13.7" PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=package/bin \
  python -m unittest discover -s tests -p '*_tests.py'
```

The app targets Splunk Enterprise 10.0-10.6 and Splunk Cloud Platform. It ships
`python.required = 3.9, 3.13`, so the alert action runs under Python 3.9 on
Splunk 10.0/10.2 and 3.13 on 10.4+.
