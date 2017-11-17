[slack]

param.webhook_url = <string>
* The webhook URL to send the Slack message requests to. This can be obtained
* by creating a new "Incoming webhook" integration in Slack.

param.from_user = <string>
* The name of the user sending the Slack message. By default this is "Splunk".

param.from_user_icon = <string>
* URL to an icon to show as the avatar for the Slack message. By default this is
* a Splunk icon.

param.attachment = [ none | alert_link ]
* Include an attachment with the slack message.
* - none: Show no attachment
* - alert_link: Show the alert title linking to the result
* Defaults to "none"

param.fields = <csv-list>
* List of fields in include with the slack message.
* It is possible to use wildcards, such as "*" for all fields or "foo*" for 
* prefixed fields, etc.

# Internal parameters
param.view_link = <string>
param.info_trigger_time = <string>
param.info_severity = <string>
