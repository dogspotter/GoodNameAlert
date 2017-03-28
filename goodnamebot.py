import json
import argparse
import sys
import time
import logging
from slackclient import SlackClient

LOG = logging.getLogger('goodnamebot')


class SlackClientWrapper(SlackClient):
    def __init__(self, token):
        super(SlackClientWrapper, self).__init__(token)
        self.logger = logging.getLogger('SlackClientWrapper')

    def api_call(self, method, timeout=None, **kwargs):
        return self.log_and_return(super(SlackClientWrapper, self).api_call(method, timeout, **kwargs))

    def log_and_return(self, data):
        self.logger.debug(data)
        return data


def main(token):
    client = SlackClientWrapper(token)
    if not client.rtm_connect():
        LOG.error("Connection error!")
        return 1
    LOG.info("Connection established. Performing init.")
    client.api_call("chat.postMessage", channel="C1X4V6K7D", text="Name Judger Initialized", as_user=True)
    while True:
        client.rtm_read()
        time.sleep(1)



def parse():
    parser = argparse.ArgumentParser(description="Runs the good name alert bot against a Slack channel")
    parser.add_argument('-c', '--config', dest='config_json', type=str, default="config.json",
                        help="The path to the configuration file to use.")
    args = parser.parse_args()
    with open(args.config_json, "r") as fin:
        config = json.load(fin)
    return main(config['bot_access_token'])


if __name__ == "__main__":
    sys.exit(parse())
