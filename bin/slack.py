import sys, json
import urllib2

def send_slack_message(settings):
    params = dict()
    params['text'] = settings.get('message')
    params['username'] = settings.get('from_user', 'Splunk')
    params['icon_url'] = settings.get('from_user_icon')
    channel = settings.get('channel')
    if channel:
        params['channel'] = channel
    else:
        print >> sys.stderr, "WARN No channel supplied, using default for webhook"
    url = settings.get('webhook_url')
    body = json.dumps(params)
    print >> sys.stderr, 'DEBUG Calling url="%s" with body=%s' % (url, body)
    req = urllib2.Request(url, body, {"Content-Type": "application/json"})
    try:
        res = urllib2.urlopen(req)
        body = res.read()
        print >> sys.stderr, "INFO Slack API responded with HTTP status=%d" % res.code
        print >> sys.stderr, "DEBUG Slack API response: %s" % json.dumps(body)
        return 200 <= res.code < 300
    except urllib2.HTTPError, e:
        print >> sys.stderr, "ERROR Error sending message: %s" % e
        return False


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == "--execute":
        payload = json.loads(sys.stdin.read())
        config = payload.get('configuration')
        if not send_slack_message(config):
            print >> sys.stderr, "FATAL Sending the slack message failed"
