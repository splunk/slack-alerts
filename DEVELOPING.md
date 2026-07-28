# Developing

This app is built with the [Splunk Add-on UCC Framework](https://splunk.github.io/addonfactory-ucc-generator/).
The configuration UI and the alert action are generated from `globalConfig.json`;
the Slack posting logic lives in `package/bin/slack_logic.py`.

## Layout

```
globalConfig.json          UCC definition (Configuration tab + "slack" alert action)
package/
  app.manifest             App metadata (schemaVersion 2.0.0)
  CHANGELOG.md             Release notes (referenced by app.manifest)
  README.md                App description
  bin/
    slack_logic.py         Slack posting logic (process_event entry point)
    safe_fmt.py            Safe string template formatter
  lib/requirements.txt     Python deps vendored into the build
  static/                  App icons
  appserver/static/        Alert action icon (slack.png)
tests/                     Unit tests
```

`ucc-gen build` generates `default/alert_actions.conf`, the alert HTML form,
`app.conf`, the Configuration view, and the `bin/slack.py` entry-point wrapper.
Do not hand-edit anything under `output/` - it is regenerated on every build.

## Prerequisites

Use the `app-toolkit` pyenv environment (holds `ucc-gen` and `splunk-appinspect`):

```sh
PYENV_VERSION="app-toolkit:3.13.7" <command>
```

## Build

```sh
PYENV_VERSION="app-toolkit:3.13.7" ucc-gen build --source package --ta-version 3.0.0
PYENV_VERSION="app-toolkit:3.13.7" ucc-gen package --path output/slack_alerts
```

This produces `output/slack_alerts/` and a `slack_alerts-<version>.tar.gz` you can
upload to Splunk or Splunkbase. Both are gitignored.

## Validate (Splunk Cloud tags)

```sh
PYENV_VERSION="app-toolkit:3.13.7" splunk-appinspect inspect slack_alerts-3.0.0.tar.gz \
  --mode precert --included-tags cloud
```

## Test

```sh
PYENV_VERSION="app-toolkit:3.13.7" PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=package/bin \
  python -m unittest discover -s tests -p '*_tests.py'
```

The app targets Splunk Enterprise 10.0-10.5 and Splunk Cloud. It ships
`python.required = 3.9, 3.13`, so the alert action runs under Python 3.9 on
Splunk 10.0/10.2 and 3.13 on 10.4+.
