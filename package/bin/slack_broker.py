import json

ALLOWLIST = {
    "settings": ("slack_app_oauth_token", "webhook_url", "from_user", "from_user_icon"),
    "proxy": (
        "proxy_enabled",
        "proxy_url",
        "proxy_port",
        "proxy_username",
        "proxy_password",
        "proxy_type",
        "proxy_rdns",
    ),
    "logging": ("loglevel",),
}

BROKER_PATH = "/services/slack_credential"
DEFAULT_LOG_LEVEL = "INFO"
STATUS_NO_RESPONSE = 0
TRUTHY = ("1", "TRUE", "T", "Y", "YES")

_CACHE_ATTR = "_slack_broker_blob"


class BrokerError(Exception):
    def __init__(self, status, correlation_id=None):
        super(BrokerError, self).__init__("broker call failed")
        self.status = status
        self.correlation_id = correlation_id


def _fetch(helper):
    from splunk.rest import simpleRequest

    return simpleRequest(
        BROKER_PATH,
        sessionKey=helper.session_key,
        getargs={"output_mode": "json"},
        rawResult=True,
    )


def get_blob(helper):
    cached = getattr(helper, _CACHE_ATTR, None)
    if cached is not None:
        return cached

    try:
        response, content = _fetch(helper)
        status = int(getattr(response, "status", STATUS_NO_RESPONSE))
        if status != 200:
            raise BrokerError(status, _correlation_id_from(content))
        blob = json.loads(content).get("stanzas") or {}
    except BrokerError:
        raise
    except Exception:
        raise BrokerError(STATUS_NO_RESPONSE) from None

    setattr(helper, _CACHE_ATTR, blob)
    return blob


def _correlation_id_from(content):
    try:
        return json.loads(content).get("correlation_id")
    except Exception:
        return None


def _stanza(helper, name):
    return get_blob(helper).get(name) or {}


def setting(helper, key):
    if key not in ALLOWLIST["settings"]:
        return None
    return _stanza(helper, "settings").get(key)


def proxy(helper):
    stanza = _stanza(helper, "proxy")
    if not stanza:
        return {}
    if str(stanza.get("proxy_enabled", "0")).strip().upper() not in TRUTHY:
        return {}
    return {
        "proxy_url": stanza.get("proxy_url", ""),
        "proxy_port": stanza.get("proxy_port"),
        "proxy_username": stanza.get("proxy_username", ""),
        "proxy_password": stanza.get("proxy_password", ""),
        "proxy_type": stanza.get("proxy_type", ""),
        "proxy_rdns": stanza.get("proxy_rdns"),
    }


def log_level(helper):
    return _stanza(helper, "logging").get("loglevel") or DEFAULT_LOG_LEVEL
