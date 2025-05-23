[slack]

param.slack_app_oauth_token = <string>
* The Slack App OAuth token that Splunk should use to send Slack alerts.  This
* can be obtained by create a new Slack App for your workspace at
* https://api.slack.com/apps.
* This takes precendence over the deprecated webhook_url parameter (below).

param.webhook_url = <string>
* DEPRECATED - Slack has deprecated this feature and will possibly be removed in the future.
* The webhook URL to send the Slack message requests to. This can be obtained
* by creating a new "Incoming webhook" integration in Slack.

param.http_proxy = <string>
* your proxy http://proxy:port

param.from_user = <string>
* DEPRECATED - This is only used in the deprecated webhook_url parameter.
* The name of the user sending the Slack message. By default this is "Splunk".

param.from_user_icon = <string>
* DEPRECATED - This is only used in the deprecated webhook_url parameter.
* URL to an icon to show as the avatar for the Slack message. By default this is
* a Splunk icon.

param.attachment = [ none | alert_link | message ]
* Include an attachment with the slack message.
* - none: Show no attachment
* - alert_link: Show the alert title linking to the result
* Defaults to "none"

param.attachment_alert_title = <string>
* A string format template used to generate the title of the alert-link message
* attachment. This can contain {search_name} - which is replaced with the name 
* of the alert.
* Defaults to: :bell: {search_name}

param.attachment_adhoc_title = <string>
* A string format template used to generate the title of the alert-link message
* attachment for ad-hoc invocations of the alert action (ie. not via an alert).
* Defaults to: :zap: Ad-hoc search

param.attachment_results_link = <string>
* A string format template used to generate the link to search results in a message
* attachment. This can contain {results_link} - which is replaced with the actual
* URL to the search results.
* Defaults to: <{results_link}|Show results in Splunk> :mag:

param.attachment_footer_text = <string>
* A string template used to generate the text in the footer of a message attachment.
* Defaults to: Splunk Alert

param.attachment_fallback = <string>
* A string template used to generate the text in the footer of a message attachment.
* Defaults to: Alert generated by Splunk: {results_link}

param.fields = <csv-list>
* List of fields in include with the slack message.
* It is possible to use wildcards, such as "*" for all fields or "foo*" for 
* prefixed fields, etc.

# Internal parameters
param.view_link = <string>
param.info_trigger_time = <string>
param.info_severity = <string>
