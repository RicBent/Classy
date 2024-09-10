import idc
import idaapi
import ida_typeinf
import ida_kernwin
from PyQt5 import QtWidgets, QtCore

import classy.util as util
import classy.itanium_mangler as itanium_mangler


class ChooseStructDialog(QtWidgets.QDialog):
    def __init__(self, inital_new_name='', title='Select a struct', has_none_btn=False):
        super(ChooseStructDialog, self).__init__()

        self.struct_id = idc.BADADDR

        self.setWindowTitle(title)

        layout = QtWidgets.QHBoxLayout(self)

        self.new_name_w = QtWidgets.QLineEdit()
        self.new_name_w.setText(inital_new_name)
        self.new_name_w.setMinimumWidth(200)
        layout.addWidget(self.new_name_w)

        new_btn = QtWidgets.QPushButton('New')
        new_btn.clicked.connect(self.handle_new)
        layout.addWidget(new_btn)

        existing_btn = QtWidgets.QPushButton('Existing')
        existing_btn.clicked.connect(self.handle_existing)
        layout.addWidget(existing_btn)

        if has_none_btn:
            none_btn = QtWidgets.QPushButton('None')
            none_btn.clicked.connect(self.handle_none)
            layout.addWidget(none_btn)

        cancel_btn = QtWidgets.QPushButton('Cancel')
        cancel_btn.clicked.connect(self.reject)
        layout.addWidget(cancel_btn)


    def handle_new(self):
        new_name = self.new_name_w.text().encode('ascii', 'replace').strip().decode()

        if not itanium_mangler.check_identifier(new_name):
            ida_kernwin.warning('The name "%s" is invalid' % new_name)
            return

        struct_id = idc.get_struc_id(new_name)
        if struct_id != idc.BADADDR:
            if util.ask_yes_no('The struct "%s" already exists. Do you want to select it anyways?' % new_name):
                self.struct_id = struct_id
                self.accept()
                return
            return

        self.struct_id = idc.add_struc(idc.BADADDR, new_name, False)
        if self.struct_id == idc.BADADDR:
            ida_kernwin.warning('Creating struct with the name "%s" failed' % new_name)
            return

        self.accept()


    def handle_existing(self):
        struct = ida_typeinf.tinfo_t()
        if not ida_kernwin.choose_struct(struct, 'Select an existing struct'):
            return

        self.struct_id = struct.force_tid()
        self.accept()


    def handle_none(self):
        self.struct_id = idc.BADADDR
        self.accept()
