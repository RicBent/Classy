import cPickle
import idaapi
import os


class ClassyDatabase(object):

    CURRENT_VERSION = 1

    NON_DICT_ATTRIBUTES = ['data', 'path', 'is_unsaved', 'is_open']

    NONE_DEFAULTS = []
    HASH_DEFAULTS = ['classes_by_name', 'known_methods']
    LIST_DEFAULTS = ['root_classes']
    DEFAULTS = {}

    def __init__(self):
        self.data = {}
        self.is_open = False

        idb_path = idaapi.get_path(idaapi.PATH_TYPE_IDB)
        self.path = os.path.splitext(idb_path)[0] + '.cdb'

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
        if not self.is_open:
            return
        cPickle.dump(self.data, open(self.path, 'wb'))

    def initialize(self):
        self.version = self.CURRENT_VERSION

    def clear(self):
        self.data = {}
        self.initialize()

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
        raise ValueError('Database is already created!')

    db = ClassyDatabase()


def destroy_instance():
    global db

    if db is None:
        raise ValueError('Database is not created!')

    db = None


def get():
    global db

    if db is None:
        raise ValueError('Classy database not created!')

    return db
