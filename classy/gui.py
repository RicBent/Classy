from sark.qt import QtWidgets, QtCore
import sip
import idaapi
import idc

import util
import database
import database_entries
from signature_dialog import SignatureDialog


class ClassyGui(idaapi.PluginForm):

    def __init__(self, plugin):
        idaapi.PluginForm.__init__(self)
        self.plugin = plugin
        self.parent = None
        self.items_by_class = {}

    def show(self):
        idaapi.PluginForm.Show(self, 'Classy')

    def OnCreate(self, form):
        self.parent = self.FormToPyQtWidget(form)

        layout = QtWidgets.QVBoxLayout()

        # Setup left side
        left_widget = QtWidgets.QWidget()
        left_layout = QtWidgets.QVBoxLayout(left_widget)

        splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        layout.addWidget(splitter)

        self.class_tree = QtWidgets.QTreeWidget()
        self.class_tree.header().hide()
        self.class_tree.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.class_tree.customContextMenuRequested.connect(self.handle_class_tree_context_menu)
        self.class_tree.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.class_tree.itemSelectionChanged.connect(self.handle_class_tree_selection_change)
        left_layout.addWidget(self.class_tree)

        button_layout = QtWidgets.QHBoxLayout()

        add_button = QtWidgets.QPushButton('Add')
        add_button.clicked.connect(self.add_class)
        button_layout.addWidget(add_button)

        remove_button = QtWidgets.QPushButton('Remove')
        remove_button.clicked.connect(self.remove_class)
        button_layout.addWidget(remove_button)

        left_layout.addLayout(button_layout)

        splitter.addWidget(left_widget)

        # Setup right side
        self.class_edit = ClassWidget(self)
        splitter.addWidget(self.class_edit)

        splitter.setSizes([100, 100000])

        self.parent.setLayout(layout)

        self.update_fields()


    def update_fields(self):
        self.reload_tree()
        self.class_edit.update_fields()


    def reload_tree(self):
        db = database.get()

        self.items_by_class = {}
        self.class_tree.clear()
        for c in db.root_classes:
            self.add_child_class_item(self.class_tree, c)


    def add_child_class_item(self, parent, c):
        if parent is None:
            parent = self.class_tree

        item = QtWidgets.QTreeWidgetItem(parent, [c.name])
        item.setData(0, QtCore.Qt.UserRole, c)
        self.items_by_class[c] = item
        for d in c.derived:
            self.add_child_class_item(item, d)
        return item


    def add_class(self):
        c = database_entries.Class.s_create()
        if c is None:
            return

        if c.base is not None:
            parent_item = self.items_by_class[c.base]
        else:
            parent_item = None

        item = self.add_child_class_item(parent_item, c)

        self.class_tree.clearSelection()
        self.class_tree.scrollToItem(item)
        item.setSelected(True)


    def remove_class(self):
        item = self.class_tree.selectedItems()[0] if len(self.class_tree.selectedItems()) else None
        if item is None:
            return

        c = item.data(0, QtCore.Qt.UserRole)
        if type(c) != database_entries.Class:
            return

        if not util.ask_yes_no('Do you really want to remove the class "%s"? All methods and new virtual methods will be unlinked' % c.name, False):
            return

        try:
            c.unlink()
            del self.items_by_class[c]
            sip.delete(item)
            idc.Refresh()
        except ValueError as e:
            idaapi.warning(str(e))


    def update_class(self, c):
        try:
            item = self.items_by_class[c]
        except KeyError:
            return

        item.setText(0, c.name)


    def generate_class_header(self):
        item = self.class_tree.selectedItems()[0] if len(self.class_tree.selectedItems()) else None
        if item is None:
            return

        c = item.data(0, QtCore.Qt.UserRole)
        if type(c) != database_entries.Class:
            return

        path = QtWidgets.QFileDialog.getSaveFileName(None,
                                                     'Export class definition', c.name + '.h',
                                                     'C++ Header file (*.h);;All Files (*)')
        if not path[0]:
            return

        f = open(path[0], 'w')
        f.write(c.generate_cpp_definition())
        f.close()


    def handle_class_tree_selection_change(self):
        item = self.class_tree.selectedItems()[0] if len(self.class_tree.selectedItems()) else None
        if item is None:
            self.class_edit.set_edit_class(None)
        else:
            c = item.data(0, QtCore.Qt.UserRole)
            if type(c) == database_entries.Class:
                self.class_edit.set_edit_class(c)
            else:
                self.class_edit.set_edit_class(None)


    def handle_class_tree_context_menu(self, point):
        item = self.class_tree.itemAt(point)

        menu = QtWidgets.QMenu()
        menu.addAction('Add', self.add_class)

        if item is not None:
            menu.addAction('Remove', self.remove_class)
            menu.addAction('Generate C++ Header File', self.generate_class_header)

        menu.exec_(self.class_tree.mapToGlobal(point))



class ClassWidget(QtWidgets.QWidget):
    def __init__(self, parent_gui):
        QtWidgets.QWidget.__init__(self)

        self.parent_gui = parent_gui

        self.edit_class = None

        layout = QtWidgets.QGridLayout(self)

        self.name = QtWidgets.QLabel()
        layout.addWidget(self.name, 0, 0)

        self.set_name = QtWidgets.QPushButton('Set')
        self.set_name.setMaximumWidth(50)
        self.set_name.clicked.connect(self.handle_set_name)
        layout.addWidget(self.set_name, 0, 1)

        self.base_class = QtWidgets.QLabel()
        layout.addWidget(self.base_class, 1, 0, 1, 2)

        self.derived_classes = QtWidgets.QLabel()
        layout.addWidget(self.derived_classes, 2, 0, 1, 2)

        self.vtable_range = QtWidgets.QLabel()
        layout.addWidget(self.vtable_range, 3, 0)

        self.set_vtable_range = QtWidgets.QPushButton('Set')
        self.set_vtable_range.setMaximumWidth(50)
        self.set_vtable_range.clicked.connect(self.handle_set_vtable_range)
        layout.addWidget(self.set_vtable_range, 3, 1)

        self.vtable = QtWidgets.QTableWidget()
        self.vtable.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        self.vtable.setColumnCount(4)
        self.vtable.setHorizontalHeaderLabels(['ID', 'Address', 'Function', 'Type'])
        self.vtable.verticalHeader().hide()
        self.vtable.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.vtable.cellDoubleClicked.connect(self.handle_vtable_double_clicked)
        layout.addWidget(self.vtable, 4, 0, 1, 2)

        self.methods = QtWidgets.QTableWidget()
        self.methods.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        self.methods.setColumnCount(2)
        self.methods.setHorizontalHeaderLabels(['Address', 'Function'])
        self.methods.verticalHeader().hide()
        self.methods.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.methods.setSortingEnabled(True)
        self.methods.cellDoubleClicked.connect(self.handle_methods_double_clicked)
        layout.addWidget(self.methods, 5, 0, 1, 2)

        method_btn_layout = QtWidgets.QHBoxLayout()

        self.add_method_btn = QtWidgets.QPushButton('Add')
        self.add_method_btn.setMaximumWidth(50)
        self.add_method_btn.clicked.connect(self.handle_add_method)
        method_btn_layout.addWidget(self.add_method_btn)

        self.remove_method_btn = QtWidgets.QPushButton('Remove')
        self.remove_method_btn.setMaximumWidth(50)
        self.remove_method_btn.clicked.connect(self.handle_remove_method)
        method_btn_layout.addWidget(self.remove_method_btn)

        method_btn_layout.addItem(QtWidgets.QSpacerItem(0, 0, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum))

        layout.addLayout(method_btn_layout, 6, 0, 1, 2)

        self.update_fields()

    def set_edit_class(self, edit_class):
        self.edit_class = edit_class
        self.update_fields()


    def update_fields(self):
        if self.edit_class is None:
            self.setDisabled(True)
            self.name.setText('Name: -')
            self.base_class.setText('Base class: -')
            self.derived_classes.setText('Derived classes: -')
            self.vtable_range.setText('VTable: -')
            self.vtable.setRowCount(0)
            self.methods.setRowCount(0)

        else:
            self.setEnabled(True)
            self.name.setText('Name: %s' % self.edit_class.name)
            self.base_class.setText('Base class: %s' % (self.edit_class.base.name if self.edit_class.base is not None else 'None'))

            derived_classes_txts = []
            for dc in self.edit_class.derived:
                derived_classes_txts.append(dc.name)
            derived_classes_txt = ', '.join(derived_classes_txts)
            if not derived_classes_txt:
                derived_classes_txt = 'None'
            self.derived_classes.setText('Derived classes: %s' % derived_classes_txt)

            if self.edit_class.vtable_start is None or self.edit_class.vtable_end is None:
                vtable_range_txt = 'Not set'
            else:
                vtable_range_txt = '0x%X - 0x%X' % (self.edit_class.vtable_start, self.edit_class.vtable_end)
            self.vtable_range.setText('VTable: %s' % vtable_range_txt)

            self.vtable.setRowCount(len(self.edit_class.vmethods))
            for idx, vm in enumerate(self.edit_class.vmethods):
                self.vtable.setItem(idx, 0, QtWidgets.QTableWidgetItem(str(idx)))
                self.vtable.setItem(idx, 1, QtWidgets.QTableWidgetItem("0x%X" % vm.ea))
                self.vtable.setItem(idx, 2, QtWidgets.QTableWidgetItem(vm.get_signature()))
                self.vtable.setItem(idx, 3, QtWidgets.QTableWidgetItem(vm.type_name()))

            self.methods.setRowCount(len(self.edit_class.methods))
            for idx, m in enumerate(self.edit_class.methods):
                address_item = QtWidgets.QTableWidgetItem(m.ea)
                address_item.setData(QtCore.Qt.DisplayRole, "0x%X" % m.ea)
                address_item.setData(QtCore.Qt.UserRole, m)
                self.methods.setItem(idx, 0, address_item)
                self.methods.setItem(idx, 1, QtWidgets.QTableWidgetItem(m.get_signature()))

    def handle_set_name(self):
        if self.edit_class is None:
            return

        new_name = idaapi.askqstr(self.edit_class.name, 'Enter a class name')
        if new_name is None or new_name == self.edit_class.name:
            return

        if new_name in database.get().classes_by_name:
            idaapi.warning('That name is already used.')
            return

        if not database_entries.Class.s_name_is_valid(new_name):
            idaapi.warning('The class name "%s" is invalid.' % new_name)
            return

        self.edit_class.rename(new_name)
        self.parent_gui.update_class(self.edit_class)


    def handle_set_vtable_range(self):
        if self.edit_class is None:
            return

        selection = idaapi.read_selection()

        # Check selection
        if selection[1] == idc.BADADDR or selection[2] == idc.BADADDR:
            return

        if selection[1] > selection[2]:
            return

        if selection[1] != idc.ScreenEA() and selection[2] != idc.ScreenEA():
            return

        # Warning for large ranges
        if (selection[2] - selection[1]) > 0x1000:
            if not util.ask_yes_no('Warning: The VTable range is longer than 0x1000 bytes. Continue?', False):
                return

        try:
            self.edit_class.set_vtable_range(selection[1], selection[2])
            self.update_fields()
        except ValueError as e:
            idaapi.warning(str(e))


    def handle_vtable_double_clicked(self, row, column):
        if self.edit_class is None:
            return

        vm = self.edit_class.vmethods[row]

        if column == 0:         # Go to vtable offset
            idc.jumpto(self.edit_class.vtable_start + row*4)
        elif column == 1:       # Go to address
            idc.Jump(vm.ea)
        elif column == 2:       # Edit signature
            dlg = SignatureDialog(vm.return_type, vm.owner.name, vm.name, vm.args, vm.is_const, vm.ctor_type, vm.dtor_type, fixed_owner_type=True)
            if dlg.exec_() != QtWidgets.QDialog.Accepted:
                return
            vm.set_signature(dlg.name, dlg.args, dlg.return_type, dlg.is_const, dlg.ctor_type, dlg.dtor_type)
            self.vtable.setItem(row, 2, QtWidgets.QTableWidgetItem(vm.get_signature()))
            idc.Refresh()


    def handle_add_method(self):
        db = database.get()

        if self.edit_class is None:
            return

        sel_ea = idc.ScreenEA()

        if sel_ea == idc.BADADDR:
            return

        existing_method = None
        if sel_ea in db.known_methods:
            existing_method = db.known_methods[sel_ea]
            if type(existing_method) != database_entries.Method:
                idaapi.warning("Cannot unlink function that is in a VTable")
                return

        name = idc.get_name(sel_ea, 0)
        if name.startswith('_Z'):       # Ignore already mangled names
            name = ''
        if not name:
            name = 'sub_%X' % sel_ea

        dlg = SignatureDialog(name=name, owner_type=self.edit_class.name, fixed_owner_type=True)
        if dlg.exec_() != QtWidgets.QDialog.Accepted:
            return

        if existing_method is not None:
            existing_method.unlink()

        method = database_entries.Method(sel_ea, self.edit_class, dlg.name)
        method.set_signature(dlg.name, dlg.args, dlg.return_type, dlg.is_const, dlg.ctor_type, dlg.dtor_type)
        self.edit_class.methods.append(method)
        method.refresh()

        self.update_fields()


    def handle_remove_method(self):
        db = database.get()

        if self.edit_class is None:
            return

        row_item = self.methods.item(self.methods.currentRow(), 0)
        if row_item is None:
            return

        m = row_item.data(QtCore.Qt.UserRole)
        if type(m) != database_entries.Method or m not in self.edit_class.methods:
            return

        m.unlink()

        self.update_fields()


    def handle_methods_double_clicked(self, row, column):
        if self.edit_class is None:
            return

        m = self.methods.item(row, 0).data(QtCore.Qt.UserRole)
        if type(m) != database_entries.Method or m not in self.edit_class.methods:
            return

        elif column == 0:       # Go to address
            idc.Jump(m.ea)
        elif column == 1:       # Edit signature
            dlg = SignatureDialog(m.return_type, m.owner.name, m.name, m.args, m.is_const, m.ctor_type, m.dtor_type, fixed_owner_type=True)
            if dlg.exec_() != QtWidgets.QDialog.Accepted:
                return
            m.set_signature(dlg.name, dlg.args, dlg.return_type, dlg.is_const, dlg.ctor_type, dlg.dtor_type)
            self.methods.setItem(row, 1, QtWidgets.QTableWidgetItem(m.get_signature()))
            idc.Refresh()

