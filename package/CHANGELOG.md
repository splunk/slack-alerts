# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [3.0.0] - 2026-07-22

Rebuilt on the Splunk Add-on UCC framework for Splunk Enterprise 10.0-10.5 and
Splunk Cloud.

### Changed
- Replaced the legacy setup page (deprecated in Splunk 10.4, non-functional on
  Splunk Cloud) with a standard UCC configuration screen.
- Global Slack credentials (App OAuth token, webhook URL) are now stored
  encrypted in `storage/passwords` instead of plaintext, and are never written
  to logs.
- Declared `python.required = 3.9, 3.13` (runs under Python 3.9 on Splunk
  10.0/10.2 and 3.13 on Splunk 10.4+).

### Removed
- Python 2 support and the vendored `six` compatibility shim.

### Upgrade notes
- Existing alerts continue to work without changes; per-alert settings
  (channel, message, attachment, fields, and the override fields) are
  unchanged.
- After upgrading, an admin must re-enter the global Slack credentials on the
  app's Configuration page. Values configured in 2.x are not migrated, so
  alerts that rely on the global default token or webhook will not send until
  the Configuration page is filled in.
