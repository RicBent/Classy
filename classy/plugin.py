import os
import re
import idaapi

import sark
import sark.qt
from sark.qt import QtWidgets, QtCore

from util import *
from gui import *
from typedef_dialog import TypedefDialog

import database


# Todo:
#  Don't create the Classy database automatically
#  Check for all actions if a database is created

class ClassyPlugin(idaapi.plugin_t):
    flags = idaapi.PLUGIN_PROC
    comment = ""

    help = "Uh, maybe later"
    wanted_name = "Classy"
    wanted_hotkey = ""

    version = 'v0.0.2'


    def init(self):
        try:
            self.actions = []
            self.menu = sark.qt.MenuManager()
            self.add_menu_items()

            self.gui = ClassyGui(self)

            database.create_instance()

            log('Loaded')

            return idaapi.PLUGIN_KEEP

        except Exception as e:
            idaapi.warning("Loading Classy failed: " + str(e))
            return idaapi.PLUGIN_SKIP


    def run(self, arg):
        show_about()


    def term(self):
        if ask_yes_no('Do you want to save the classy database?', True):
            database.get().save()

        database.destroy_instance()

        self.remove_menu_items()

        log('Unloaded')

    
    def add_menu_items(self):
        self.menu.add_menu("Classy")
        self.add_menu_item("Show GUI", "Classy/", self.show_gui)
        self.add_menu_item("Save Database", "Classy/", self.save)
        self.add_menu_item("Save Database As...", "Classy/", self.save_as)
        self.add_menu_item("Edit Typedefs...", "Classy/", self.edit_typedefs)
        self.add_menu_item("Set pure virtual values...", "Classy/", self.edit_pure_virtual_vals)
        self.add_menu_item("Refresh all", "Classy/", self.refresh_all)
        self.add_menu_item("Clear Database", "Classy/", self.clear)
        self.add_menu_item("About", "Classy/", show_about)


    def add_menu_item(self, name, menu_path, callback, shortcut = "", tooltip = ""):
        id = 'Classy:' + re.sub('[^A-Za-z0-9]+', '_', name)
        action = UiAction(id, name, tooltip, menu_path, callback, shortcut)
        action.register_action()
        self.actions.append(action)


    def remove_menu_items(self):
        for action in self.actions:
            action.unregister_action()
        self.menu.clear()


    def save(self):
        database.get().save()


    def save_as(self):
        db = database.get()

        path = QtWidgets.QFileDialog.getSaveFileName(None,
                                                     'Export Classy database', '',
                                                     'Classy database (*.cdb)')
        if not path[0]:
            return

        # Check for user idiocy
        if os.path.normpath(path[0]) == os.path.normpath(db.path):
            idaapi.warning('You cannot overwrite the currently active Classy database.')
            return

        db.save_as(path[0])


    def show_gui(self):
        self.gui.show()


    def clear(self):
        if ask_yes_no('Are you really sure that you want to clear the Classy databse?\n', False):
            database.get().clear()
            self.gui.update_fields()
            idc.Refresh()


    def edit_typedefs(self):
        dlg = TypedefDialog()
        dlg.exec_()


    def edit_pure_virtual_vals(self):
        db = database.get()

        txt = idaapi.askqstr(', '.join([('0x%X' % x) for x in db.pure_virtual_vals]), "Enter pure virtual values")
        if txt is None:
            return

        new_pure_virtual_vals = []

        for s in txt.split(','):
            try:
                new_pure_virtual_vals.append(int(s, 0))
            except ValueError:
                idaapi.warning('Parsing "%s" failed. Pure virtual values were not modified.' % s)
                return

        db.pure_virtual_vals = new_pure_virtual_vals



    def refresh_all(self):
        database_entries.refresh_all()
        idc.Refresh()
