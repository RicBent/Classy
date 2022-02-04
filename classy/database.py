import _pickle as cPickle
import idaapi
import os
from datetime import datetime

from classy.util import log
from PyQt5 import QtCore


class ClassyDatabase(object):

    CURRENT_VERSION = 1

    NON_DICT_ATTRIBUTES = ['data', 'path', 'autosave_path', 'is_open', 'autosave_timer']

    NONE_DEFAULTS = []
    HASH_DEFAULTS = ['classes_by_name', 'classes_by_struct_id', 'known_methods', 'typedefs']
    LIST_DEFAULTS = ['root_classes', 'pure_virtual_vals', 'deleted_virtual_vals']
    DEFAULTS = {'autosave_interval': 60}


    def __init__(self):
        self.data = {}
        self.is_open = False

        idb_path = idaapi.get_path(idaapi.PATH_TYPE_IDB)
        self.path = os.path.splitext(idb_path)[0] + '.cdb'
        self.autosave_path = os.path.splitext(idb_path)[0] + '.autosave.cdb'

        self.autosave_timer = QtCore.QTimer()
        self.autosave_timer.timeout.connect(self.autosave)


    def is_created(self):
        if self.is_open:
            return True
        return os.path.isfile(self.path)


    def delete(self):
        if self.is_open:
            return

        try:
            os.remove(self.path)
        except:
            pass


    def open(self):
        try:
            dbfile = open(self.path, 'rb')
            self.data = cPickle.load(dbfile)

            if not hasattr(self, 'version'):
                raise Exception('Database is corrupt!')

            if self.version != self.CURRENT_VERSION:
                raise Exception('Version Mismatch! File: %s, Plugin: %s' % (self.version, self.CURRENT_VERSION))

        except IOError:
            pass

        if not hasattr(self, 'version'):
            self.initialize()

        self.is_open = True
        self.autosave_timer.start(self.autosave_interval * 1000)



    def close(self):
        self.autosave_timer.stop()
        self.data = {}
        self.is_open = False


    def __getattr__(self, key):
        try:
            return self.data[key]
        except KeyError:
            try:
                default = self.default_for(key)
                setattr(self, key, default)
                return getattr(self, key)
            except KeyError:
                raise AttributeError('Classy database has no attribute %s' % key)


    def __setattr__(self, key, value):
        if key in self.NON_DICT_ATTRIBUTES:
            object.__setattr__(self, key, value)
        else:
            self.data[key] = value


    def save(self):
        self.save_as(self.path)
        os.remove(self.autosave_path)


    def save_as(self, path):
        if not self.is_open:
            return
        cPickle.dump(self.data, open(path, 'wb'))


    def autosave(self):
        self.save_as(self.autosave_path)
        log('Classy database autosaved')


    def initialize(self):
        self.version = self.CURRENT_VERSION


    def clear(self):
        self.data = {}
        self.initialize()


    def set_autosave_interval(self, interval):
        self.autosave_interval = interval
        self.autosave_timer.stop()
        if self.is_open:
            self.autosave_timer.start(self.autosave_interval * 1000)


    def generate_symbols(self):
        contents = []
        contents.append('/*\n * Classy exported symbols')
        contents.append(datetime.now().strftime(' * %x %X'))
        contents.append(' */\n\n')

        if len(self.classes_by_name) > 0:
            contents.append('/*\n * Classes\n */\n\n')
            for c_name in self.classes_by_name:
                contents.append(self.classes_by_name[c_name].generate_symbols())
                contents.append('')

        return '\n'.join(contents)


    @staticmethod
    def default_for(key):
        if key in ClassyDatabase.NONE_DEFAULTS:
            return None
        if key in ClassyDatabase.HASH_DEFAULTS:
            return {}
        if key in ClassyDatabase.LIST_DEFAULTS:
            return []
        return ClassyDatabase.DEFAULTS[key]



db = None


def create_instance():
    global db

    if db is not None:
        raise ValueError('Classy database instance is already created!')

    db = ClassyDatabase()
    return db


def destroy_instance():
    global db

    if db is None:
        raise ValueError('Classy database instance is not created!')

    db = None


def get():
    global db

    if db is None:
        raise ValueError('Classy database instance is not created!')

    return db
