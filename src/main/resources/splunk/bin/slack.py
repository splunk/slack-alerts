import sys
import json
import urllib2
import re
import time
from copy import deepcopy
from fnmatch import fnmatch
from safe_fmt import safe_format

SEVERITY_COLORS = ['#555555','#6DB7C6','#65A637','#F7BC38','#F58F39','#D93F3C']

OK = 0
ERROR_CODE_UNKNOWN = 1
ERROR_CODE_VALIDATION_FAILED = 2
ERROR_CODE_CHANNEL_NOT_FOUND = 3
ERROR_CODE_FORBIDDEN = 4
ERROR_CODE_HTTP_FAIL = 5
ERROR_CODE_UNEXPECTED = 6

def build_fields_attachment(payload):
    res = payload.get('result', dict())
    available_fields = res.keys()
    field_attachments = []
    seen_fields = set()
    field_list = re.split(r'\s*,\s*', payload['configuration'].get('fields', '').strip())
    for f in field_list:
        for af in available_fields:
            if af not in seen_fields and fnmatch(af, f):
                seen_fields.add(af)
                val = res[af]
                if type(val) == list:
                    val = val[0]
                field_attachments.append(dict(title=af, value=val, short=True))
    return field_attachments

def format_template(template_key, payload, fallback=''):
    config = payload['configuration']
    template = config.get(template_key)
    if template is not None:
        fallback = template
        try:
            args = deepcopy(payload)
            args['configuration']['webhook_url'] = '****'
            args['configuration']['webhook_url_override'] = '****'
            return safe_format(template, args)
        except:
            print >> sys.stderr, "WARN Failed to format template %s \"%s\" -" % (template_key, template), sys.exc_info()[1]
    return fallback

def build_alert_attachment(payload):
    config = payload['configuration']
    attachment = dict()
    if 'info_severity' in config:
        try:
            attachment['color'] = SEVERITY_COLORS[int(config['info_severity'])]
        except: pass
    attachment['fallback'] = format_template('attachment_fallback', payload)
    attachment_title_key = 'attachment_alert_title' if payload.get('search_name') else 'attachment_adhoc_title'
    attachment['title'] = format_template(attachment_title_key, payload, 'Alert')
    if config.get('attachment', 'none') == 'message':
        attachment['text'] = format_template('message', payload)
    else:
        attachment['text'] = format_template('attachment_results_link', payload)
    attachment['title_link'] = config.get('view_link')
    attachment['footer'] = format_template('attachment_footer_text', payload)
    attachment['footer_icon'] = 'https://s3-us-west-1.amazonaws.com/ziegfried-apps/slack-alerts/splunk-icon.png'
    try:
        attachment['ts'] = int(float(config.get('info_trigger_time')))
    except: pass
    if config.get('fields'):
        attachment['fields'] = build_fields_attachment(payload)
    return attachment

def build_slack_message(payload):
    config = payload.get('configuration')
    params = dict()

    if config['attachment'] != 'message':
        params['text'] = format_template('message', payload)
    params['username'] = config.get('from_user', 'Splunk')
    params['icon_url'] = config.get('from_user_icon')

    channel = config.get('channel')
    if channel:
        params['channel'] = channel
    else:
        print >> sys.stderr, "WARN No channel supplied, using default for webhook"

    if config.get('attachment', 'none') != 'none':
        params['attachments'] = [build_alert_attachment(payload)]
    elif config.get('fields'):
        params['attachments'] = [dict(fields=build_fields_attachment(payload))]
    return params

def send_slack_message(payload):
    try:
        config = payload.get('configuration')
        url = config.get('webhook_url', '')
        if config.get('webhook_url_override'):
            url = config.get('webhook_url_override', '')
            print >> sys.stderr, "INFO Using webhook URL from webhook_url_override: %s" % url
        elif not url:
            print >> sys.stderr, "FATAL No webhook URL configured and no override specified"
            return ERROR_CODE_VALIDATION_FAILED
        else:
            print >> sys.stderr, "INFO Using configured webhook URL: %s" % url

        if not url.startswith('https:'):
            print >> sys.stderr, "FATAL Invalid webhook URL specified. The URL must use HTTPS."
            return ERROR_CODE_VALIDATION_FAILED

        body = json.dumps(build_slack_message(payload))

        print >> sys.stderr, 'DEBUG Calling url="%s" with body=%s' % (url, body)
        req = urllib2.Request(url, body, {"Content-Type": "application/json"})
        try:
            res = urllib2.urlopen(req)
            body = res.read()
            print >> sys.stderr, "INFO Slack API responded with HTTP status=%d" % res.code
            print >> sys.stderr, "DEBUG Slack API response: %s" % json.dumps(body)
            if 200 <= res.code < 300:
                return OK
        except urllib2.HTTPError, e:
            print >> sys.stderr, "ERROR HTTP request to Slack webhook URL failed: %s" % e
            try:
                res = e.read()
                print >> sys.stderr, "ERROR Slack error response: %s" % res
                if res in ('channel_not_found', 'channel_is_archived'):
                    return ERROR_CODE_CHANNEL_NOT_FOUND
                if res == 'action_prohibited':
                    return ERROR_CODE_FORBIDDEN
            except:
                pass
            return ERROR_CODE_HTTP_FAIL
    except:
        print >> sys.stderr, "FATAL Unexpected error:", sys.exc_info()[0]
        return ERROR_CODE_UNEXPECTED

def validate_payload(payload):
    if not 'configuration' in payload:
        print >> sys.stderr, "FATAL Invalid payload, missing 'configuration'"
        return False
    config = payload.get('configuration')
    channel = config.get('channel')

    if channel and (channel[0] != '#' and channel[0] != '@'):
        # Only warn here for now
        print >> sys.stderr, "WARN Validation warning: Parameter `channel` \"%s\" should start with # or @" % channel

    msg = config.get('message')
    if not msg:
        print >> sys.stderr, "FATAL Validation error: Parameter `message` is missing or empty"
        return False

    att = config.get('attachment')
    if att and att not in ('alert_link', 'message'):
        print >> sys.stderr, "WARN Validation warning: Parameter `attachment` must be ether \"alert_link\" or \"message\""

    return True

if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == "--execute":
        payload = json.loads(sys.stdin.read())

        if not validate_payload(payload):
            sys.exit(ERROR_CODE_VALIDATION_FAILED)
    
        result = send_slack_message(payload)
        if result == OK:
            print >> sys.stderr, "INFO Successfully sent slack message"
        else:
            print >> sys.stderr, "FATAL Alert action failed"

        sys.exit(result)
