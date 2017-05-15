import argparse
import json
import logging
import logging.handlers
import re
import socket
import sys
import time
from data_store import FileDataStore

from slackclient import SlackClient

CONFIG_ACTIONS_KEY = 'actions'


class MessageHandler(object):
    """
    Handles routing a message match to its respective handling method
    """
    def __init__(self, regex, target):
        """
        Creates the instance.
        :param regex: (RegexObject) the compiled regular expression to match with
        :param target: (func) the target function to call when a match is found
        """
        self.regex = regex
        self.target = target
        self.name = target.__name__

    def handle_message(self, data):
        """
        Checks if the provided data matches this handler's regex. If so, invokes the target. 
        :param data: (dict) A message from Slack
        """
        if not data:
            return
        match = self.regex.match(data.get('text').strip())
        if match:
            self.target(data, match)


class Bot(SlackClient):
    def __init__(self, token, actions, data_store, loglevel="DEBUG"):
        """
        Creates a new Bot
        :param token: (str) The bot's access token
        :param actions: (list) A map that includes a trigger regex and a method name on this object. Format:
        >>> [{"action": "post_good_name_alert", "trigger": ".*name alert.*"}]
        :param data_store: (BaseDataStore) a data store object to use to fetch/retrieve good name data
        :param loglevel: (str) A python `logging` module-compatible log level argument
        """
        super(Bot, self).__init__(token)
        self.data_store = data_store
        self.logger = logging.getLogger('goodnamebot.Bot')
        self.logger.addHandler(logging.StreamHandler(sys.stdout))
        self.logger.setLevel(loglevel)
        self._handlers = [MessageHandler(re.compile(a['trigger'], re.IGNORECASE),
                                         getattr(self, a['action'], self.missing_action)) for a in actions]

    def rtm_read(self):
        """
        Gets all new messages from Slack
        :return: (list) the messages
        """
        data = self._log_and_return(super(Bot, self).rtm_read())
        return data

    def api_call(self, method, timeout=None, **kwargs):
        return self._log_and_return(super(Bot, self).api_call(method, timeout, **kwargs))

    def initialize(self):
        """
        Connects to slack.
        """
        if not self.rtm_connect():
            self.logger.error("Connection error!")
            raise
        self.logger.info("Connection established.")

    def _log_and_return(self, data):
        """Logs the data and passes it through"""
        if data:
            self.logger.debug(data)
        return data

    def _handle_data(self, data):
        if data.get('type') != 'message' or not data.get('text', '').strip():
            return
        [h.handle_message(data) for h in self._handlers]

    def post_good_name_alert(self, data, match):
        """
        Posts a random good name to the channel.
        """
        self.send_msg(data['channel'], "Good name: {}".format(self.data_store.get_good_name()))

    def add_good_name(self, data, match):
        """Idempotently adds a good name to the data store"""
        self.logger.debug("Match: %s", match.groups())
        added_name = self.data_store.add_good_name(match.group(1), data['user'])
        if added_name:
            self.send_msg(data['channel'], "Good name {} recorded.".format(added_name))

    def missing_action(self, data, match):
        """Debug action in case an action does not specify a proper method"""
        self.logger.warn("Action defined for pattern '%s' did not match any known method. Data: %s", match.re, data)

    def send_msg(self, target_id, text):
        result = self.api_call("chat.postMessage", channel=target_id, text=text, as_user=True)
        if not result.get('ok'):
            self.logger.warn("Erroneous result?: %s", result)

    def run(self):
        while True:
            try:
                [self._handle_data(item) for item in self.rtm_read()]
            except Exception as e:
                self.logger.error("Got exception when attempting to read! %s", e)
                self.initialize()
            time.sleep(1)


def main(token, **kwargs):
    if CONFIG_ACTIONS_KEY not in kwargs:
        raise KeyError("Config did not contain a value for key: " + CONFIG_ACTIONS_KEY)
    client = Bot(token, kwargs[CONFIG_ACTIONS_KEY], FileDataStore('good_names.json', connect=True))
    client.initialize()
    perform_debug_calls(client, kwargs.get("debug_calls", []))
    client.run()


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
