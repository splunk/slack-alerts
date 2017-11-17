# Slack alert action params

action.slack.param.channel = <string>
* The Slack channel to send the message to. Typically starts with a # - which
* indicates that it's a public channel. It can also start with @ for sending
* a message directly to a user.

action.slack.param.message = <string>
* The message text to send. See Slack API documentation for incoming webhooks
* in order to find out what's possible.

action.slack.param.attachment = [ none | alert_link ]
* Include an attachment with the slack message.
* - none: Show no attachment
* - alert_link: Show the alert title linking to the result
* Defaults to "none"

action.slack.param.fields = <csv-list>
* List of fields in include with the slack message.
* It is possible to use wildcards, such as "*" for all fields or "foo*" for 
* prefixed fields, etc.
