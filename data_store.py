import json
import logging
import sys
import datetime
import random
import collections

KEY_NAMES = "good_names"
KEY_NAME = "good_name"
KEY_ADDED_BY = "added_by"
KEY_DATE_ADDED = "date_added"
KEY_SEASON = "season"
KEY_VOTES = "votes"
CURRENT_SEASON = "11"
TIME_FMT = '%Y-%m-%d %H:%M:%S'


class GoodName(object):
    def __init__(self, good_name, added_by, season=CURRENT_SEASON, votes=None, date_added=None):
        self.good_name = good_name
        self.added_by = added_by
        self.season = season
        self.votes = votes if votes else {}
        self.date_added = date_added if date_added else datetime.datetime.utcnow().strftime(TIME_FMT)


class BaseDataStore(object):
    def __init__(self, loglevel='DEBUG'):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.addHandler(logging.StreamHandler(sys.stdout))
        self.logger.setLevel(loglevel)

    def get_good_name(self, n=None, s=None):
        pass

    def add_good_name(self, goodname, requester):
        pass

    def is_resource_connected(self):
        return True

    def connect(self):
        pass


class FileDataStore(BaseDataStore):
    """
    Stores data in a basic JSON document that looks like the following:
    >>> {
    >>> "good_names":[
    >>>  {
    >>>   "good_name":"Jerry Mander",
    >>>   "added_by":"U04S0E2JZ",
    >>>   "date_added":"2017-05-14 12:00:00",
    >>>   "season":"11",
    >>>   "votes":{}
    >>>  }]
    >>> }
    """
    def __init__(self, filename, connect=False):
        super(FileDataStore, self).__init__()
        self.filename = filename
        self.data = None
        self.name_map = None
        if connect:
            self.connect()

    def connect(self):
        try:
            with open(self.filename, 'r') as fin:
                self.data = json.load(fin, object_pairs_hook=collections.OrderedDict)
            self.name_map = dict([(d[KEY_NAME], GoodName(**d)) for d in self.data[KEY_NAMES]])
        except Exception as e:
            self.data = None
            self.logger.error('Got error when attempting to open file: %s', e)

    def add_good_name(self, goodname, requester):
        goodname = str(goodname).strip().capitalize()
        if goodname not in self.name_map:
            n = GoodName(goodname, requester)
            self.name_map[goodname] = n
            self.data[KEY_NAMES].append(vars(n))
            try:
                with open(self.filename, 'w') as fout:
                    json.dump(self.data, fout, indent=2, separators=(',', ':'))
                return goodname
            except Exception as e:
                self.logger.error('Got error when attempting to dump current good names: %s', e)

    def is_resource_connected(self):
        return self.data is not None

    def get_good_name(self, n=None, s=None):
        if not self.is_resource_connected():
            self.logger.debug("Could not get good name, resource not connected")
            return None
        return random.choice(self.name_map.keys())
