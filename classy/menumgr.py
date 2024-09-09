import re

import ida_kernwin
from classy.uiaction import UiAction
from classy.util import show_about


class MenuState:
    NULL = 0
    DATABASE_CLOSED = 1
    DATABASE_OPENED = 2


class MenuMgr:
    def __init__(self, plugin):
        self.state = MenuState.NULL
        self.actions = []
        
        self.menu = ida_kernwin.create_menu("Classy", "Classy")

        # Global actions
        self.about_action = self.create_menu_item("About", show_about)

        # Database closed actions
        self.action_create_open = self.create_menu_item("Create/open database", plugin.create_open_database)

        # Database opened actions
        self.action_show_gui = self.create_menu_item("Show GUI", plugin.show_gui)
        self.action_save = self.create_menu_item("Save Database", plugin.save)
        self.action_save_as = self.create_menu_item("Save Database As...", plugin.save_as)
        self.action_export_all_symbols = self.create_menu_item("Export all Symbols...", plugin.export_all_symbols)
        self.action_edit_typedefs = self.create_menu_item("Edit Typedefs...", plugin.edit_typedefs)
        self.action_set_pure_virtuals = self.create_menu_item("Set pure virtual values...", plugin.edit_pure_virtual_vals)
        self.action_set_deleted_virtuals = self.create_menu_item("Set deleted virtual values...", plugin.edit_deleted_virtual_vals)
        self.action_set_autosave_interval = self.create_menu_item("Set autosave interval...", plugin.set_autosave_interval)
        self.action_refresh_all = self.create_menu_item("Refresh all", plugin.refresh_all)
        self.action_clear_database = self.create_menu_item("Clear Database", plugin.clear_database)


    def cleanup(self):
        for a in self.actions:
            a.unregister()
        #self.menu.unregister_action(self.menu.menuAction())


    def set_state(self, state):
        if state == self.state:
            return

        self.state = state

        for a in self.actions:
            a.detach()

        if self.state == MenuState.DATABASE_CLOSED:
            self.action_create_open.attach()

        if self.state == MenuState.DATABASE_OPENED:
            self.action_show_gui.attach()
            self.action_save.attach()
            self.action_save_as.attach()
            self.action_export_all_symbols.attach()
            self.action_edit_typedefs.attach()
            self.action_set_pure_virtuals.attach()
            self.action_set_deleted_virtuals.attach()
            self.action_set_autosave_interval.attach()
            self.action_refresh_all.attach()
            self.action_clear_database.attach()

        self.about_action.attach()


    def create_menu_item(self, name, callback, shortcut="", tooltip=""):
        id = 'Classy:' + re.sub('[^A-Za-z0-9]+', '_', name)
        action = UiAction(id, name, tooltip, 'Classy', callback, shortcut)
        action.register()
        self.actions.append(action)
        return action
