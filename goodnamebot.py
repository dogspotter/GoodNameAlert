import argparse
import json
import logging
import logging.handlers
import re
import sys
import time

from slackclient import SlackClient


class MessageHandler(object):
    """
    Handles routing a message match to its respective handling method
    """
    def __init__(self, name, regex, target):
        """
        Creates the instance.
        :param name: (str) Name of this handler
        :param regex: (RegexObject) the compiled regular expression to match with
        :param target: (func) the target function to call when a match is found
        """
        self.name = name
        self.regex = regex
        self.target = target

    def handle_message(self, msg):
        if not msg:
            return
        match = self.regex.match(msg)
        if match:
            self.target(match)


class Bot(SlackClient):
    def __init__(self, token, loglevel="DEBUG"):
        super(Bot, self).__init__(token)
        self.logger = logging.getLogger('goodnamebot.Bot')
        self.logger.addHandler(logging.StreamHandler(sys.stdout))
        self.logger.setLevel(loglevel)
        self._handlers = [
            MessageHandler("Good Name Addition", re.compile("!gna(.+)", re.IGNORECASE), self._add_good_name),
            MessageHandler("Good Name Alert", re.compile(".*name alert.*", re.IGNORECASE), self._post_good_name_alert)
        ]

    def rtm_read(self):
        data = self._log_and_return(super(Bot, self).rtm_read())
        [self._handle_data(item) for item in data]
        return data

    def api_call(self, method, timeout=None, **kwargs):
        return self._log_and_return(super(Bot, self).api_call(method, timeout, **kwargs))

    def initialize(self):
        if not self.rtm_connect():
            self.logger.error("Connection error!")
            raise
        self.logger.info("Connection established.")

    def _log_and_return(self, data):
        if data:
            self.logger.debug(data)
        return data

    def _handle_data(self, data):
        if data.get('type') != 'message' or not data.get('text', '').strip():
            return
        [h.handle_message(data.get('text').strip()) for h in self._handlers]

    def _post_good_name_alert(self, match):
        self.logger.debug("Match: %s", match.groups())

    def _add_good_name(self, match):
        self.logger.debug("Match: %s", match.groups())


def main(token, **kwargs):
    client = Bot(token)
    client.initialize()
    perform_debug_calls(client, kwargs.get("debug_calls", []))
    while True:
        client.rtm_read()
        time.sleep(1)


def perform_debug_calls(client, debug_calls):
    """
    Debug calls may be placed in the config.json in order to just run a bunch of random calls for debugging purposes
    at the start of a session. Each item in the 'debug_calls' list element is a dict that maps to the 
    SlackClient.api_call arguments
    """
    for call in debug_calls:
        call.setdefault("timeout", None)
        client.logger.debug("Calling api '%s'", call)
        client.api_call(**call)


def parse():
    parser = argparse.ArgumentParser(description="Runs the good name alert bot against a Slack channel")
    parser.add_argument('-c', '--config', dest='config_json', type=str, default="config.json",
                        help="The path to the configuration file to use.")
    args = parser.parse_args()
    with open(args.config_json, "r") as fin:
        config = json.load(fin)
    config.update(vars(args))
    main(**config)


if __name__ == "__main__":
    parse()
