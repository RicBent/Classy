import idaapi
import idc
from PyQt5 import QtWidgets, QtCore

import classy.database as database
import classy.itanium_mangler as itanium_mangler


# Todo: Move some code to database_entries

class TypedefDialog(QtWidgets.QDialog):
    def __init__(self):
        super(TypedefDialog, self).__init__()

        self.setWindowTitle('Classy Typedefs')

        layout = QtWidgets.QVBoxLayout(self)

        self.list = QtWidgets.QListWidget()
        layout.addWidget(self.list)

        button_layout = QtWidgets.QHBoxLayout(self)
        layout.addLayout(button_layout)

        button_layout.addItem(QtWidgets.QSpacerItem(0, 0, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum))

        add_btn = QtWidgets.QPushButton('Add')
        add_btn.clicked.connect(self.handle_add)
        button_layout.addWidget(add_btn)

        edit_btn = QtWidgets.QPushButton('Edit')
        edit_btn.clicked.connect(self.handle_edit)
        button_layout.addWidget(edit_btn)

        remove_btn = QtWidgets.QPushButton('Remove')
        remove_btn.clicked.connect(self.handle_remove)
        button_layout.addWidget(remove_btn)

        self.update_list()


    def update_list(self):
        db = database.get()

        self.list.clear()
        for t in db.typedefs:
            item = QtWidgets.QListWidgetItem('typedef %s %s;' % (db.typedefs[t], t))
            item.setData(QtCore.Qt.UserRole, t)
            self.list.addItem(item)


    def handle_add(self):
        t = idaapi.ask_str('', idaapi.HIST_IDENT,'Enter typedef name')
        if t is None:
            return

        if t in database.get().typedefs:
            idaapi.warning('That name is already used.')
            return

        if not itanium_mangler.check_identifier(t):
            idaapi.warning('That name is invalid.')
            return

        # Todo: prevent overwriting builtins

        self.try_set_typedef(t)


    def handle_edit(self):
        item = self.list.currentItem()
        if item is None:
            return

        t = item.data(QtCore.Qt.UserRole)
        self.try_set_typedef(t)


    def handle_remove(self):
        item = self.list.currentItem()
        if item is None:
            return

        t = item.data(QtCore.Qt.UserRole)
        del database.get().typedefs[t]

        self.update_list()


    def try_set_typedef(self, t):
        val = idaapi.ask_str('', idaapi.HIST_IDENT,'Enter typedef value')
        if val is None:
            return

        val_segs = val.split()
        itanium_mangler.fix_multi_seg_types(val_segs)
        if len(val_segs) != 1 or (
                val_segs[0] not in itanium_mangler.BUILTIN_TYPES and not itanium_mangler.check_identifier(val_segs[0])):
            idaapi.warning('That value is invalid.')
            return

        database.get().typedefs[t] = val.strip()
        self.update_list()
