# Slack Alerts for Splunk

Custom alert action to send messages to Slack channels.

## Capability the alert owner needs

The account that owns the saved search needs the `read_slack_alerts_credential` capability, even
when the alert sets its own token or webhook URL override. `admin` and `sc_admin` already hold it.

Grant it to any other alert owner by either route:

- Add `read_slack_alerts_credential = enabled` to a role the owner holds.
- Assign the owner the shipped `slack_alert_action` role.

Without it, the owner's alerts fail with exit code 7.

## Troubleshooting exit code 7

Splunk logs `Alert action script returned error code=7` when the settings read fails. Search
`slack_modalert.log` for:

```text
Slack settings broker call failed
```

Match its `status` against this table.

| `status` | Meaning | Fix |
|----------|---------|-----|
| `0` | No usable answer: refused connection, TLS failure, timeout, or unparsable body. | Run the following `curl` command to confirm splunkd answers. |
| `403` | The owner lacks `read_slack_alerts_credential`, or `SPLUNK_BINDIP` in `splunk-launch.conf` binds splunkd to a routable address. | Grant the capability. If an admin-owned alert also returns `403`, the cause is `SPLUNK_BINDIP`. See Known issues in [CHANGELOG.md](CHANGELOG.md). |
| `404` | The app hasn't loaded since installation. | Restart splunkd. |
| `500` | The endpoint failed to read the settings. | Read the `error_type` of the `broker_failure` entry with the same `correlation_id` in `slack_alerts_credential_broker.log`. |

On a Splunk Enterprise search head, reproduce a status with an account that holds the capability:

```sh
curl -sk -o /dev/null -w '%{http_code}\n' -u <user> \
  "$(cat "$SPLUNK_HOME/var/run/splunk/splunkd_uri.txt")/services/slack_credential?output_mode=json"
```

On Splunk Cloud Platform, run this search and read `status` from the result:

```spl
index=_internal source=*slack_modalert.log "Slack settings broker call failed"
```

## Troubleshooting `No Slack App OAuth token or webhook URL configured.`

1. Search `slack_alerts_credential_broker.log` for a `broker_stanza_unreadable` entry, which names
   the stanza and an `error_type`.
2. Set the Slack token or webhook URL on the Configuration tab.

See [CHANGELOG.md](CHANGELOG.md) for release notes and version history.
