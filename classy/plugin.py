import os
import re
import idaapi

import sark
import sark.qt
from sark.qt import QtWidgets, QtCore

from util import *
from gui import *

import database


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


    def show_gui(self):
        self.gui.show()


    def clear(self):
        if ask_yes_no('Are you really sure that you want to clear the Classy databse?\n', False):
            database.get().clear()
            self.gui.update_fields()
            idc.Refresh()


    def refresh_all(self):
        database_entries.refresh_all()
        idc.Refresh()
