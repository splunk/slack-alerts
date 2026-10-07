import json
import logging
import os
import sys
import uuid

APPROOT = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
for _path in (os.path.join(APPROOT, "lib"), os.path.join(APPROOT, "bin")):
    if _path not in sys.path:
        sys.path.insert(0, _path)

import import_declare_test

import __main__

MAIN_FILE = os.path.join(APPROOT, "bin", "slack_credential.py")

from solnlib import log
from splunk.persistconn.application import PersistentServerConnectionApplication

from slack_broker import ALLOWLIST

logger = log.Logs().get_logger("slack_alerts_credential_broker")


class SlackCredentialHandler(PersistentServerConnectionApplication):
    def __init__(self, _command_line=None, _command_arg=None):
        PersistentServerConnectionApplication.__init__(self)

    def handle(self, in_string):
        correlation_id = uuid.uuid4().hex[:12]
        try:
            request = json.loads(in_string)
        except Exception:
            return self._failure(400, correlation_id, "request_not_json")

        token = request.get("system_authtoken")
        if not token:
            return self._failure(500, correlation_id, "no_system_authtoken")

        previous_main_file = getattr(__main__, "__file__", None)
        __main__.__file__ = MAIN_FILE
        try:
            from splunk.rest import makeSplunkdUri
            from splunktaucclib.rest_handler.credentials import RestCredentials
            from splunktaucclib.rest_handler.handler import RestHandler

            from slack_alerts_rh_settings import endpoint

            handler = RestHandler(makeSplunkdUri(), token, endpoint)
            stanzas = {}
            for name, keys in ALLOWLIST.items():
                stanzas[name] = self._project(
                    handler, name, keys, RestCredentials, correlation_id
                )
            log.log_event(
                logger,
                {
                    "action": "broker_read",
                    "correlation_id": correlation_id,
                    "user": (request.get("session") or {}).get("user"),
                },
                log_level=logging.INFO,
            )
            return {"status": 200, "payload": {"stanzas": stanzas}}
        except Exception as exc:
            log.log_event(
                logger,
                {
                    "action": "broker_failure",
                    "correlation_id": correlation_id,
                    "error_type": type(exc).__name__,
                },
                log_level=logging.ERROR,
            )
            return self._failure(500, correlation_id, None)
        finally:
            if previous_main_file is None:
                if hasattr(__main__, "__file__"):
                    del __main__.__file__
            else:
                __main__.__file__ = previous_main_file

    def _project(self, handler, name, keys, credentials, correlation_id):
        projected = {}
        try:
            for entity in handler.get(name, decrypt=True):
                content = entity.content
                for key in keys:
                    value = content.get(key)
                    if value is None:
                        continue
                    if credentials.is_placeholder(str(value)):
                        continue
                    projected[key] = value
        except Exception as exc:
            log.log_event(
                logger,
                {
                    "action": "broker_stanza_unreadable",
                    "correlation_id": correlation_id,
                    "stanza": name,
                    "error_type": type(exc).__name__,
                },
                log_level=logging.ERROR,
            )
            return projected
        return projected

    def _failure(self, status, correlation_id, reason):
        if reason:
            log.log_event(
                logger,
                {
                    "action": "broker_failure",
                    "correlation_id": correlation_id,
                    "error_type": reason,
                },
                log_level=logging.ERROR,
            )
        return {
            "status": status,
            "payload": {"error": "internal", "correlation_id": correlation_id},
        }

    def done(self):
        pass
