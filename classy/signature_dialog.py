import idaapi
import idc
from sark.qt import QtWidgets, QtCore

import database
import itanium_mangler


class SignatureDialog(QtWidgets.QDialog):
    def __init__(self, return_type = 'void', owner_type='', name='', args='', is_const=False, ctor_type=1, dtor_type=1,
                 fixed_return_type=False, fixed_owner_type=False, fixed_name=False, fixed_args=False,
                 fixed_is_const=False, fixed_ctor_type=False, fixed_dtor_type=False):
        super(SignatureDialog, self).__init__()

        self.return_type = return_type
        self.owner_type = owner_type
        self.name = name
        self.args = args
        self.is_const = is_const
        self.ctor_type = ctor_type
        self.dtor_type = dtor_type

        self.setWindowTitle('Set function signature')

        layout = QtWidgets.QGridLayout(self)

        self.signature_w = QtWidgets.QLabel()
        self.signature_w.setMinimumWidth(220)
        layout.addWidget(self.signature_w, 0, 0, 1, 2)

        layout.addWidget(QtWidgets.QLabel('Return type'), 1, 0)
        self.return_type_w = QtWidgets.QLineEdit()
        self.return_type_w.setText(self.return_type)
        self.return_type_w.setDisabled(fixed_return_type)
        self.return_type_w.textChanged.connect(self.update_signature)
        layout.addWidget(self.return_type_w, 1, 1)

        layout.addWidget(QtWidgets.QLabel('Owner type'), 2, 0)
        self.owner_type_w = QtWidgets.QLineEdit()
        self.owner_type_w.setText(self.owner_type)
        self.owner_type_w.setDisabled(fixed_owner_type)
        self.owner_type_w.textChanged.connect(self.update_signature)
        layout.addWidget(self.owner_type_w, 2, 1)

        layout.addWidget(QtWidgets.QLabel('Name'), 3, 0)
        self.name_w = QtWidgets.QLineEdit()
        self.name_w.setText(self.name)
        self.name_w.setDisabled(fixed_name)
        self.name_w.textChanged.connect(self.update_signature)
        layout.addWidget(self.name_w, 3, 1)

        layout.addWidget(QtWidgets.QLabel('Arguments'), 4, 0)
        self.args_w = QtWidgets.QLineEdit()
        self.args_w.setText(self.args)
        self.args_w.setDisabled(fixed_args)
        self.args_w.textChanged.connect(self.update_signature)
        layout.addWidget(self.args_w, 4, 1)

        layout.addWidget(QtWidgets.QLabel('Const'), 5, 0)
        self.is_const_w = QtWidgets.QCheckBox()
        self.is_const_w.setChecked(self.is_const)
        self.is_const_w.setDisabled(fixed_is_const)
        self.is_const_w.stateChanged.connect(self.update_signature)
        layout.addWidget(self.is_const_w, 5, 1)

        layout.addWidget(QtWidgets.QLabel('Ctor'), 6, 0)
        self.ctor_type_w = QtWidgets.QComboBox()
        self.ctor_type_w.addItem("C1: complete")
        self.ctor_type_w.addItem("C2: base")
        self.ctor_type_w.addItem("C3: complete allocating")
        self.ctor_type_w.setCurrentIndex(ctor_type-1)
        self.ctor_type_w.setDisabled(fixed_ctor_type)
        self.ctor_type_w.currentIndexChanged.connect(self.update_signature)
        layout.addWidget(self.ctor_type_w, 6, 1)

        layout.addWidget(QtWidgets.QLabel('Dtor'), 7, 0)
        self.dtor_type_w = QtWidgets.QComboBox()
        self.dtor_type_w.addItem("D0: deleting")
        self.dtor_type_w.addItem("D1: complete")
        self.dtor_type_w.addItem("D2: base")
        self.dtor_type_w.setCurrentIndex(dtor_type)
        self.dtor_type_w.setDisabled(fixed_dtor_type)
        self.dtor_type_w.currentIndexChanged.connect(self.update_signature)
        layout.addWidget(self.dtor_type_w, 7, 1)

        layout.addWidget(QtWidgets.QLabel('Status'), 8, 0)
        self.status_w = QtWidgets.QLabel()
        layout.addWidget(self.status_w, 8, 1)

        layout.addWidget(QtWidgets.QLabel('Mangled'), 9, 0)
        self.mangled_w = QtWidgets.QLabel()
        layout.addWidget(self.mangled_w, 9, 1)

        self.buttonBox = QtWidgets.QDialogButtonBox()
        self.buttonBox.addButton("OK", QtWidgets.QDialogButtonBox.AcceptRole)
        self.buttonBox.addButton("Cancel", QtWidgets.QDialogButtonBox.RejectRole)
        layout.addWidget(self.buttonBox, 10, 0, 1, 2)
        self.buttonBox.accepted.connect(self.handle_ok)
        self.buttonBox.rejected.connect(self.reject)

        self.signature = None
        self.is_signature_valid = False
        self.mangled = None
        self.status = ''
        self.update_signature()

    def update_signature(self):
        self.return_type = self.return_type_w.text().encode('ascii', 'replace').strip() or 'void'
        self.owner_type = self.owner_type_w.text().encode('ascii', 'replace').strip()
        self.name = self.name_w.text().encode('ascii', 'replace').strip()
        self.args = self.args_w.text().encode('ascii', 'replace').strip()
        self.is_const = self.is_const_w.isChecked()
        self.ctor_type = self.ctor_type_w.currentIndex() + 1
        self.dtor_type = self.dtor_type_w.currentIndex()

        # ctors and dtors shouldn't have a return type, dtors shouldn't have args
        if self.owner_type:
            owner_last_type = self.owner_type.split('::')[-1]
            if self.name == owner_last_type:
                self.return_type = ''
            elif self.name == '~' + owner_last_type:
                self.return_type = ''
                self.args = ''

        signature_segs = []
        if self.return_type:
            signature_segs.append(self.return_type)
            signature_segs.append(' ')
        if self.owner_type:
            signature_segs.append(self.owner_type)
            signature_segs.append('::')
        signature_segs.append(self.name)
        signature_segs.append('(')
        signature_segs.append(self.args)
        signature_segs.append(')')
        if self.is_const:
            signature_segs.append(' const')
        self.signature = ''.join(signature_segs)
        self.signature_w.setText(self.signature)

        self.is_signature_valid = False
        self.mangled = None
        try:
            if not self.name or (' ' in self.name):
                raise ValueError('Name is invalid')
            self.mangled = itanium_mangler.mangle_function(self.signature, database.get().typedefs, self.ctor_type, self.dtor_type)
            self.is_signature_valid = True
            self.status = ''
            self.status_w.setText('Valid')
        except (ValueError, NotImplementedError) as e:
            self.status = str(e)
            self.status_w.setText('Invalid: ' + self.status)
        self.mangled_w.setText(str(self.mangled))

    def handle_ok(self):
        if not self.is_signature_valid:
            idaapi.warning("The signature is not valid: " + self.status)
        else:
            self.accept()
