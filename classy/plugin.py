import os
import re
import idaapi

from PyQt5 import QtWidgets, QtCore

from classy.util import *
from classy.gui import *
from classy.menumgr import MenuMgr, MenuState
from classy.typedef_dialog import TypedefDialog

import classy.database as database


class ClassyPlugin(idaapi.plugin_t):
    flags = idaapi.PLUGIN_PROC
    comment = ""

    help = "Uh, maybe later"
    wanted_name = "Classy"
    wanted_hotkey = ""

    version = 'v0.0.2'


    def init(self):
        self.menumgr = MenuMgr(self)
        self.gui = ClassyGui(self)

        db = database.create_instance()
        if db.is_created():
            try:
                db.open()
            except Exception as e:
                idaapi.warning('Loading Classy database failed: %s' % str(e))

        if db.is_open:
            self.menumgr.set_state(MenuState.DATABASE_OPENED)
        else:
            self.menumgr.set_state(MenuState.DATABASE_CLOSED)


        log('Loaded')

        return idaapi.PLUGIN_KEEP


    def run(self, arg):
        show_about()


    def term(self):
        try:
            db = database.get()

            if db.is_open and ask_yes_no('Do you want to save the classy database?', True):
                db.save()
            db.close()

            database.destroy_instance()

        except ValueError:      # Database instance might not be created
            pass

        self.menumgr.cleanup()

        log('Unloaded')


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


    def create_open_database(self):
        db = database.get()

        try:
            db.open()
        except Exception as e:
            idaapi.warning('Creating/opening Classy database failed: %s' % str(e))

        if db.is_open:
            self.menumgr.set_state(MenuState.DATABASE_OPENED)
        else:
            self.menumgr.set_state(MenuState.DATABASE_CLOSED)


    def export_all_symbols(self):
        path = QtWidgets.QFileDialog.getSaveFileName(None,
                                                     'Export all symbols', '',
                                                     'Linker script (*.ld);;All files (*)')
        if not path[0]:
            return

        f = open(path[0], 'w')
        f.write(database.get().generate_symbols())
        f.close()



    def clear_database(self):
        if ask_yes_no('Are you really sure that you want to clear the Classy databse?\n', False):
            database.get().clear()
            self.gui.update_fields()
            idaapi.refresh_idaview_anyway()


    def edit_typedefs(self):
        dlg = TypedefDialog()
        dlg.exec_()


    def edit_pure_virtual_vals(self):
        db = database.get()

        txt = idaapi.ask_str(', '.join([('0x%X' % x) for x in db.pure_virtual_vals]), idaapi.HIST_IDENT,"Enter pure virtual values")
        if txt is None or not txt.strip():
            return

        new_pure_virtual_vals = []

        for s in txt.split(','):
            try:
                new_pure_virtual_vals.append(int(s, 0))
            except ValueError:
                idaapi.warning('Parsing "%s" failed. Pure virtual values were not modified.' % s)
                return

        db.pure_virtual_vals = new_pure_virtual_vals


    def edit_deleted_virtual_vals(self):
        db = database.get()

        txt = idaapi.ask_str(', '.join([('0x%X' % x) for x in db.deleted_virtual_vals]), idaapi.HIST_IDENT,"Enter deleted virtual values")
        if txt is None or not txt.strip():
            return

        new_deleted_virtual_vals = []

        for s in txt.split(','):
            try:
                new_deleted_virtual_vals.append(int(s, 0))
            except ValueError:
                idaapi.warning('Parsing "%s" failed. Deleted virtual values were not modified.' % s)
                return

        db.deleted_virtual_vals = new_deleted_virtual_vals


    def refresh_all(self):
        database_entries.refresh_all()
        idaapi.refresh_idaview_anyway()


    def set_autosave_interval(self):
        db = database.get()

        new_interval, ok_pressed = QtWidgets.QInputDialog.getInt(None, 'Set autosave interval', 'Autosave interval [seconds]:', db.autosave_interval, 10)
        if ok_pressed:
            db.set_autosave_interval(new_interval)
